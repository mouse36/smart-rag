#!/usr/bin/env python3
"""
Startup script for the Backend
"""

import os
import sys
import logging
from pathlib import Path

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, will use system environment variables only
    pass

# Set up environment variables with defaults
env_vars = {
    'DEEPSEEK_API_KEY': 'your_deepseek_api_key_here',  # MUST be set by user
    'DEEPSEEK_BASE_URL': 'https://api.deepseek.com',
    'DEEPSEEK_MODEL': 'deepseek-chat',
    'HOST': '0.0.0.0',
    'PORT': os.getenv('PORT', '5000'),  # Use Railway's PORT environment variable
    'DEBUG': 'False',  # Set to False for production
    'EMBEDDINGS_MODEL': 'all-MiniLM-L6-v2',
    'VECTOR_DIMENSION': '384',
    'CHUNK_SIZE': '500',
    'CHUNK_OVERLAP': '50',

    'MAX_CONTEXT_LENGTH': '4000',
    'MAX_RESPONSE_LENGTH': '1000',
    'TEMPERATURE': '0.7',
    'TOP_P': '0.9',

    'API_CALLS_ENABLED': 'False'  # Set to 'False' for deployment safety
}

# Set environment variables if not already set
for key, default_value in env_vars.items():
    if key not in os.environ:
        os.environ[key] = default_value

def check_requirements():
    """Check if required environment variables and dependencies are set"""
    
    # Check API calls configuration
    api_enabled = os.environ.get('API_CALLS_ENABLED', 'False').lower() == 'true'
    
    if api_enabled:
        # Check critical environment variables only if API calls are enabled
        if os.environ.get('DEEPSEEK_API_KEY') == 'your_deepseek_api_key_here':
            print("❌ ERROR: DEEPSEEK_API_KEY is not set!")
            print("Please set your DeepSeek API key:")
            print("export DEEPSEEK_API_KEY='your_actual_api_key'")
            return False
        print("✅ API calls are ENABLED - will use DeepSeek API")
    else:
        print("⚠️  API calls are DISABLED - will use placeholder responses")
    
    # Check if knowledge base exists
    knowledge_base_path = Path(__file__).parent / 'knowledge_base'
    if not knowledge_base_path.exists():
        print(f"❌ ERROR: Knowledge base directory not found: {knowledge_base_path}")
        return False
    
    # Check if there are any .txt files in knowledge base
    txt_files = list(knowledge_base_path.glob('*.txt'))
    if not txt_files:
        print(f"❌ ERROR: No .txt files found in knowledge base: {knowledge_base_path}")
        return False
    
    print(f"✅ Found {len(txt_files)} knowledge base files")
    
    # Check Python dependencies
    try:
        import flask
        import requests
        print("✅ Core Python packages are installed")
        
        # Check AI/ML dependencies only if needed
        from config import Config
        config = Config()
        if config.API_CALLS_ENABLED:
            from sentence_transformers import SentenceTransformer
            import numpy
            print("✅ AI/ML packages are installed")
        else:
            print("⚠️  Skipping AI/ML package check - API calls disabled")
            
    except ImportError as e:
        print(f"❌ ERROR: Missing required package: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🚀 Starting Backend...")
    print("=" * 50)
    
    # Debug: Check if JSONBIN_API_KEY is available
    jsonbin_key = os.getenv('JSONBIN_API_KEY')
    if jsonbin_key:
        print(f"✅ JSONBIN_API_KEY found: {jsonbin_key[:8]}...{jsonbin_key[-4:] if len(jsonbin_key) > 12 else '***'}")
    else:
        print("❌ JSONBIN_API_KEY not found in environment")
        print("🔍 Available environment variables:")
        for key in sorted(os.environ.keys()):
            if 'JSONBIN' in key or 'API' in key or 'KEY' in key:
                print(f"  {key}: {'*' * len(os.environ[key])}")
    
    # Set up deployment safeguards
    try:
        from deployment_safeguards import setup_deployment_safeguards
        setup_deployment_safeguards()
        print("✅ Deployment safeguards set up")
    except ImportError:
        print("⚠️  Deployment safeguards not available")
    except Exception as e:
        print(f"⚠️  Deployment safeguards failed: {e}")
    
    # Check requirements
    print("🔍 Checking requirements...")
    if not check_requirements():
        print("\n❌ Startup failed due to missing requirements")
        sys.exit(1)
    
    print("\n✅ All requirements satisfied")
    print("🔄 Loading application...")
    
    try:
        # Import and run the Flask app
        print("📦 Importing Flask app...")
        from app import app, config
        print("✅ Flask app imported successfully")
        
        # Conditionally import AI/ML components
        if config.API_CALLS_ENABLED:
            print("🤖 Importing AI/ML components...")
            from app import vector_engine, deepseek_client
            print("✅ AI/ML components imported")
        
        # Validate configuration
        print("⚙️  Validating configuration...")
        config_error = config.validate()
        if config_error:
            print(f"❌ Configuration error: {config_error}")
            sys.exit(1)
        print("✅ Configuration validated")
        
        print("\n📊 Configuration:")
        print(f"  Host: {config.HOST}")
        print(f"  Port: {config.PORT}")
        print(f"  Debug: {config.DEBUG}")
        print(f"  Model: {config.DEEPSEEK_MODEL}")
        print(f"  Embeddings: {config.EMBEDDINGS_MODEL}")
        
        # Initialize components
        print("\n🔄 Initializing components...")
        
        if config.API_CALLS_ENABLED:
            if config.LAZY_LOAD_MODEL:
                print("  📚 Vector search engine initialized with lazy loading")
                print("  🔍 Testing DeepSeek API connection...")
            else:
                print("  📚 Loading knowledge base and generating embeddings...")
                vector_engine.initialize()
                print("  🔍 Testing DeepSeek API connection...")
            
            if not deepseek_client.is_ready():
                print("❌ DeepSeek API connection failed")
                sys.exit(1)
        else:
            print("⚠️  Skipping AI/ML component initialization - API calls disabled")
        
        print("\n🎉 All components ready!")
        print(f"🌐 Server starting at http://{config.HOST}:{config.PORT}")
        print("📝 Available endpoints:")
        print("  POST /chat - Main chat endpoint")
        print("  GET  /health - Health check")
        print("  POST /search - Direct knowledge base search")

        print("\n" + "=" * 50)
        print("🚀 Starting Flask server...")
        
        # Start the Flask server
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed to start: {str(e)}")
        print("Full error details:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
