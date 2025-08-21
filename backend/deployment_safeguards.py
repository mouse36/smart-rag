"""
Deployment Safeguards for Render and Other Platforms
Handles common deployment issues and provides fallback mechanisms
"""

import os
import sys
import logging
import time
import signal
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class DeploymentSafeguards:
    """Handles deployment-specific issues and provides safeguards"""
    
    def __init__(self):
        self.startup_time = time.time()
        self.max_startup_time = int(os.getenv('MAX_STARTUP_TIME', 300))  # 5 minutes
        self.memory_limit_mb = int(os.getenv('MEMORY_LIMIT_MB', 512))
        self.port = int(os.getenv('PORT', 5000))
        
    def check_environment(self) -> bool:
        """Check deployment environment and set up safeguards"""
        logger.info("Checking deployment environment...")
        
        # Check if we're in a deployment environment
        is_deployment = any([
            os.getenv('RENDER'),
            os.getenv('HEROKU'),
            os.getenv('RAILWAY'),
            os.getenv('FLY_IO'),
            os.getenv('DOCKER')
        ])
        
        if is_deployment:
            logger.info("Detected deployment environment - enabling safeguards")
            self._setup_deployment_safeguards()
        else:
            logger.info("Local development environment detected")
        
        return True
    
    def _setup_deployment_safeguards(self):
        """Set up deployment-specific safeguards"""
        # Set conservative memory limits
        os.environ.setdefault('MAX_MEMORY_MB', '400')
        os.environ.setdefault('MIN_MEMORY_FOR_MODEL', '150')
        os.environ.setdefault('USE_SMALLER_MODEL', 'True')
        os.environ.setdefault('LAZY_LOAD_MODEL', 'True')
        os.environ.setdefault('CHUNK_SIZE', '300')
        os.environ.setdefault('CHUNK_OVERLAP', '30')
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._graceful_shutdown)
        signal.signal(signal.SIGINT, self._graceful_shutdown)
        
        logger.info("Deployment safeguards configured")
    
    def _graceful_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    def check_memory_usage(self) -> bool:
        """Check current memory usage and warn if approaching limits"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 * 1024)
            used_percent = memory.percent
            
            logger.info(f"Memory usage: {used_percent:.1f}% used, {available_mb:.1f} MB available")
            
            if available_mb < 100:
                logger.warning(f"Low memory warning: {available_mb:.1f} MB available")
                return False
            
            if used_percent > 90:
                logger.warning(f"High memory usage: {used_percent:.1f}%")
                return False
            
            return True
            
        except ImportError:
            logger.warning("psutil not available - cannot monitor memory")
            return True
    
    def check_startup_time(self) -> bool:
        """Check if startup is taking too long"""
        elapsed = time.time() - self.startup_time
        if elapsed > self.max_startup_time:
            logger.error(f"Startup taking too long: {elapsed:.1f}s > {self.max_startup_time}s")
            return False
        return True
    
    def check_port_availability(self) -> bool:
        """Check if the required port is available"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', self.port))
            sock.close()
            
            if result == 0:
                logger.warning(f"Port {self.port} is already in use")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Could not check port availability: {e}")
            return True
    
    def validate_environment_variables(self) -> Dict[str, Any]:
        """Validate required environment variables"""
        required_vars = {
            'DEEPSEEK_API_KEY': 'DeepSeek API key for chat functionality',
            'JSONBIN_API_KEY': 'JSONBin API key for user authentication',
            'JSONBIN_BIN_ID': 'JSONBin bin ID for user data'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
            return {'valid': False, 'missing': missing_vars}
        
        logger.info("All required environment variables are set")
        return {'valid': True, 'missing': []}
    
    def check_file_permissions(self) -> bool:
        """Check file permissions for cache and knowledge base"""
        try:
            # Check cache directory
            cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
            
            # Check if we can write to cache
            test_file = os.path.join(cache_dir, 'test_write.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            # Check knowledge base access
            kb_path = os.path.join(os.path.dirname(__file__), 'knowledge_base')
            if not os.path.exists(kb_path):
                logger.error(f"Knowledge base path not found: {kb_path}")
                return False
            
            # Check if we can read knowledge base files
            kb_files = [f for f in os.listdir(kb_path) if f.endswith('.txt')]
            if not kb_files:
                logger.error("No .txt files found in knowledge base")
                return False
            
            logger.info(f"File permissions OK. Found {len(kb_files)} knowledge base files")
            return True
            
        except Exception as e:
            logger.error(f"File permission check failed: {e}")
            return False
    
    def run_preflight_checks(self) -> bool:
        """Run all preflight checks before starting the application"""
        logger.info("Running preflight checks...")
        
        checks = [
            ("Environment Variables", self.validate_environment_variables),
            ("File Permissions", self.check_file_permissions),
            ("Port Availability", self.check_port_availability),
            ("Memory Usage", self.check_memory_usage),
            ("Startup Time", self.check_startup_time)
        ]
        
        failed_checks = []
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                if isinstance(result, dict):
                    if not result.get('valid', True):
                        failed_checks.append(f"{check_name}: {result.get('missing', [])}")
                elif not result:
                    failed_checks.append(check_name)
                else:
                    logger.info(f"✅ {check_name} passed")
            except Exception as e:
                logger.error(f"❌ {check_name} failed: {e}")
                failed_checks.append(f"{check_name}: {e}")
        
        if failed_checks:
            logger.warning(f"Preflight checks failed: {failed_checks}")
            return False
        
        logger.info("✅ All preflight checks passed")
        return True

def setup_deployment_safeguards():
    """Set up deployment safeguards and run preflight checks"""
    safeguards = DeploymentSafeguards()
    
    # Check environment and set up safeguards
    safeguards.check_environment()
    
    # Run preflight checks
    if not safeguards.run_preflight_checks():
        logger.error("Preflight checks failed - deployment may not work correctly")
        # Don't exit - let the application try to start anyway
        return False
    
    return True
