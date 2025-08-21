#!/usr/bin/env python3
"""
Railway Deployment Startup Script for SunnyMentor Backend
Optimized for Railway's 1GB RAM environment
"""

import os
import sys
import logging
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set Railway-specific environment variables
railway_env_vars = {
    'HOST': '0.0.0.0',
    'PORT': os.environ.get('PORT', '5000'),
    'DEBUG': 'False',  # Disable debug mode for production
    'API_CALLS_ENABLED': 'True',
    'LAZY_LOAD_MODEL': 'True',
    'MAX_MEMORY_MB': '400',
    'USE_SMALLER_MODEL': 'True',
    'EMBEDDINGS_MODEL': 'all-MiniLM-L6-v2',
    'VECTOR_DIMENSION': '384',
    'CHUNK_SIZE': '300',
    'CHUNK_OVERLAP': '30',
    'MAX_CONTEXT_LENGTH': '4000',
    'MAX_RESPONSE_LENGTH': '1000',
    'TEMPERATURE': '0.7',
    'TOP_P': '0.9',
}

# Set environment variables if not already set
for key, default_value in railway_env_vars.items():
    if key not in os.environ:
        os.environ[key] = default_value

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_railway_requirements():
    """Check Railway-specific requirements"""
    
    # Check if required environment variables are set
    required_vars = ['DEEPSEEK_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these in Railway dashboard under Variables tab")
        return False
    
    # Check knowledge base
    knowledge_base_path = os.path.join(backend_dir, 'knowledge_base')
    if not os.path.exists(knowledge_base_path):
        logger.error(f"❌ Knowledge base directory not found: {knowledge_base_path}")
        return False
    
    txt_files = list(Path(knowledge_base_path).glob('*.txt'))
    if not txt_files:
        logger.error(f"❌ No .txt files found in knowledge base: {knowledge_base_path}")
        return False
    
    logger.info(f"✅ Found {len(txt_files)} knowledge base files")
    
    # Check Python dependencies
    try:
        import flask
        import requests
        logger.info("✅ Core Python packages are installed")
        
        # Check AI/ML dependencies
        import sentence_transformers
        import torch
        import numpy
        logger.info("✅ AI/ML packages are installed")
        
    except ImportError as e:
        logger.error(f"❌ Missing required package: {e}")
        return False
    
    return True

def main():
    """Main Railway startup function"""
    logger.info("🚀 Starting SunnyMentor Backend on Railway...")
    logger.info("=" * 60)
    
    # Check Railway requirements
    if not check_railway_requirements():
        logger.error("❌ Railway startup failed due to missing requirements")
        sys.exit(1)
    
    logger.info("✅ All Railway requirements satisfied")
    logger.info("🔄 Loading application...")
    
    try:
        # Import and run the Flask app
        from app import app, config
        
        # Conditionally import AI/ML components
        if config.API_CALLS_ENABLED:
            from app import vector_engine, deepseek_client
        
        # Validate configuration
        config_error = config.validate()
        if config_error:
            logger.error(f"❌ Configuration error: {config_error}")
            sys.exit(1)
        
        logger.info("\n📊 Railway Configuration:")
        logger.info(f"  Host: {config.HOST}")
        logger.info(f"  Port: {config.PORT}")
        logger.info(f"  Debug: {config.DEBUG}")
        logger.info(f"  Model: {config.DEEPSEEK_MODEL}")
        logger.info(f"  Embeddings: {config.EMBEDDINGS_MODEL}")
        logger.info(f"  Memory Limit: {os.environ.get('MAX_MEMORY_MB', '400')}MB")
        
        # Initialize components with Railway optimizations
        logger.info("\n🔄 Initializing components with Railway optimizations...")
        
        if config.API_CALLS_ENABLED:
            if config.LAZY_LOAD_MODEL:
                logger.info("  📚 Vector search engine initialized with lazy loading")
                logger.info("  🔍 Testing DeepSeek API connection...")
            else:
                logger.info("  📚 Loading knowledge base and generating embeddings...")
                vector_engine.initialize()
                logger.info("  🔍 Testing DeepSeek API connection...")
            
            if not deepseek_client.is_ready():
                logger.error("❌ DeepSeek API connection failed")
                sys.exit(1)
        else:
            logger.info("⚠️  Skipping AI/ML component initialization - API calls disabled")
        
        logger.info("\n🎉 All components ready for Railway!")
        logger.info(f"🌐 Server starting at http://{config.HOST}:{config.PORT}")
        logger.info("📝 Available endpoints:")
        logger.info("  POST /chat - Main chat endpoint")
        logger.info("  GET  /health - Health check")
        logger.info("  POST /search - Direct knowledge base search")
        logger.info("  GET  / - Frontend files")

        logger.info("\n" + "=" * 60)
        
        # Start the Flask server
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
        
    except KeyboardInterrupt:
        logger.info("\n\n👋 Server stopped by user")
    except Exception as e:
        logger.error(f"\n❌ Server failed to start: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
