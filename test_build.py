#!/usr/bin/env python3
"""
Simple build test script for Railway debugging
"""

import os
import sys

def test_build():
    """Test basic build requirements"""
    print("🔧 Railway Build Test")
    print("=" * 30)
    
    # Test Python version
    print(f"Python version: {sys.version}")
    
    # Test basic imports
    try:
        import flask
        print("✅ Flask imported successfully")
    except ImportError as e:
        print(f"❌ Flask import failed: {e}")
        return False
    
    try:
        import requests
        print("✅ Requests imported successfully")
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
        return False
    
    # Test file existence
    files_to_check = ['app.py', 'run.py', 'config.py']
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            return False
    
    # Test knowledge base
    kb_path = 'knowledge_base'
    if os.path.exists(kb_path):
        txt_files = [f for f in os.listdir(kb_path) if f.endswith('.txt')]
        print(f"✅ Knowledge base found with {len(txt_files)} .txt files")
    else:
        print("❌ Knowledge base directory missing")
        return False
    
    # Test basic app import
    try:
        from app import app
        print("✅ Flask app imported successfully")
    except Exception as e:
        print(f"❌ Flask app import failed: {e}")
        return False
    
    print("✅ All build tests passed!")
    return True

if __name__ == '__main__':
    success = test_build()
    sys.exit(0 if success else 1)
