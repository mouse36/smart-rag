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

# Import deployment safeguards
try:
    from deployment_safeguards import setup_deployment_safeguards
    setup_deployment_safeguards()
except ImportError:
    # deployment_safeguards not available, continue without it
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

def check_basic_requirements():
    """Check basic requirements without complex imports"""
    print("🔍 Checking basic requirements...")
    
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
    
    # Check basic Python dependencies
    try:
        import flask
        import requests
        print("✅ Core Python packages are installed")
    except ImportError as e:
        print(f"❌ ERROR: Missing required package: {e}")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🚀 Starting Backend...")
    print("=" * 50)
    
    # Railway-specific logging
    print(f"🚂 Railway Environment:")
    print(f"  PORT: {os.getenv('PORT', 'Not set')}")
    print(f"  RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'Not set')}")
    print(f"  HOST: {os.getenv('HOST', 'Not set')}")
    print(f"  DEBUG: {os.getenv('DEBUG', 'Not set')}")
    print(f"  API_CALLS_ENABLED: {os.getenv('API_CALLS_ENABLED', 'Not set')}")
    
    # Check basic requirements
    if not check_basic_requirements():
        print("\n❌ Startup failed due to missing requirements")
        sys.exit(1)
    
    print("\n✅ Basic requirements satisfied")
    print("🔄 Loading application...")
    
    try:
        # Import and run the Flask app
        print("📦 Importing Flask app...")
        from app import app
        print("✅ Flask app imported successfully")
        
        # Test health endpoint
        print("🔍 Testing health endpoint...")
        with app.test_client() as client:
            response = client.get('/health')
            print(f"✅ Health endpoint test: {response.status_code} - {response.data.decode()}")
        
        # Get configuration
        from config import Config
        config = Config()
        
        print("\n📊 Configuration:")
        print(f"  Host: {config.HOST}")
        print(f"  Port: {config.PORT}")
        print(f"  Debug: {config.DEBUG}")
        print(f"  API Calls Enabled: {config.API_CALLS_ENABLED}")
        
        print("\n🎉 Application ready!")
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
