#!/usr/bin/env python3
"""
Setup verification script for Smart RAG Backend
Checks all requirements and provides guidance for setup
"""

import os
import sys
import subprocess
from pathlib import Path

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, will use system environment variables only
    pass

def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version >= (3, 8):
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Need Python 3.8+")
        return False

def check_pip_packages():
    """Check if required packages can be imported"""
    print("\n📦 Checking Python packages...")
    
    packages = {
        'flask': 'Flask web framework',
        'sentence_transformers': 'Sentence transformers for embeddings',
        'scikit-learn': 'scikit-learn for vector search',
        'numpy': 'NumPy for numerical operations',
        'requests': 'HTTP requests library',
    }
    
    optional_packages = {
    }
    
    missing_packages = []
    
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"❌ {package} - {description} - MISSING")
            missing_packages.append(package)
    
    for package, description in optional_packages.items():
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"⚠️  {package} - {description} - OPTIONAL")
    
    if missing_packages:
        print(f"\n📋 To install missing packages, run:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_environment_variables():
    """Check environment variables"""
    print("\n🔐 Checking environment variables...")
    
    required_vars = {
        'DEEPSEEK_API_KEY': 'DeepSeek API key (required for AI responses)'
    }
    
    optional_vars = {

        'DEBUG': 'Debug mode (optional)',
    }
    
    missing_required = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value and value != 'your_deepseek_api_key_here':
            print(f"✅ {var} - {description} - SET")
        else:
            print(f"❌ {var} - {description} - NOT SET")
            missing_required.append(var)
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var} - {description} - SET ({value})")
        else:
            print(f"⚠️  {var} - {description} - NOT SET (will use default)")
    
    if missing_required:
        print(f"\n📋 To set required environment variables:")
        for var in missing_required:
            if var == 'DEEPSEEK_API_KEY':
                print(f"export {var}='your_actual_deepseek_api_key'")
    
    return len(missing_required) == 0

def check_knowledge_base():
    """Check knowledge base files"""
    print("\n📚 Checking knowledge base...")
    
    backend_dir = Path(__file__).parent
    kb_path = backend_dir / 'knowledge_base'
    
    if not kb_path.exists():
        print(f"❌ Knowledge base directory not found: {kb_path}")
        return False
    
    txt_files = list(kb_path.glob('*.txt'))
    if not txt_files:
        print(f"❌ No .txt files found in knowledge base: {kb_path}")
        return False
    
    print(f"✅ Found {len(txt_files)} knowledge base files")
    
    # Check total size
    total_size = sum(f.stat().st_size for f in txt_files)
    print(f"📊 Total knowledge base size: {total_size / 1024 / 1024:.1f} MB")
    
    return True





def check_deepseek_api():
    """Test DeepSeek API connection"""
    print("\n🤖 Testing DeepSeek API connection...")
    
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key or api_key == 'your_deepseek_api_key_here':
        print("⚠️  DeepSeek API key not set - skipping API test")
        return False
    
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'deepseek-chat',
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'max_tokens': 5
        }
        
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ DeepSeek API connection successful")
            return True
        else:
            print(f"❌ DeepSeek API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ DeepSeek API test failed: {e}")
        return False

def main():
    """Main setup check function"""
    print("🚀 Smart RAG Backend Setup Check")
    print("=" * 50)
    
    checks = [
        check_python_version,
        check_pip_packages,
        check_environment_variables,
        check_knowledge_base,


        check_deepseek_api,
    ]
    
    results = []
    for check in checks:
        result = check()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 Setup Check Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 All checks passed! Your system is ready to run.")
        print("\n🚀 To start the backend:")
        print("python run.py")
        
    elif passed >= total - 2:  # Allow some optional checks to fail
        print("⚠️  Most checks passed. System should work with minor limitations.")
        print("\n🚀 You can try starting the backend:")
        print("python run.py")
        
    else:
        print("❌ Several checks failed. Please fix the issues above before running.")
        print("\n📋 Next steps:")
        print("1. Install missing Python packages: pip install -r requirements.txt")
        print("2. Set your DeepSeek API key: export DEEPSEEK_API_KEY='your_key'")
        print("3. Run this check again: python setup_check.py")
    
    print(f"\n📈 Score: {passed}/{total} checks passed")

if __name__ == '__main__':
    main()
