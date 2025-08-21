#!/usr/bin/env python3
"""
Memory-Optimized Deployment Script for Render
This script sets up the environment for deployment with limited memory resources.
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def set_memory_optimized_env():
    """Set environment variables for memory-optimized deployment"""
    env_vars = {
        'USE_SMALLER_MODEL': 'True',
        'MAX_MEMORY_MB': '400',  # Conservative memory limit
        'LAZY_LOAD_MODEL': 'True',
        'CHUNK_SIZE': '300',  # Smaller chunks to reduce memory usage
        'CHUNK_OVERLAP': '30',
        'EMBEDDINGS_MODEL': 'all-MiniLM-L6-v2',  # Smaller model
        'VECTOR_DIMENSION': '384'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"Set {key}={value}")

def install_requirements():
    """Install requirements with memory optimization"""
    try:
        logger.info("Installing core requirements...")
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements-core.txt'
        ], check=True)
        
        logger.info("Installing AI/ML requirements...")
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install requirements: {e}")
        return False

def main():
    """Main deployment function"""
    logger.info("Starting memory-optimized deployment...")
    
    # Set memory-optimized environment variables
    set_memory_optimized_env()
    
    # Install requirements
    if not install_requirements():
        logger.error("Failed to install requirements")
        sys.exit(1)
    
    # Import and run the application
    try:
        from run import main as run_main
        run_main()
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
