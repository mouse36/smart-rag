#!/usr/bin/env python3
"""
Test script for Railway deployment debugging
"""

import os
import sys
import traceback
from pathlib import Path

def test_environment():
    """Test environment variables and basic setup"""
    print("🔍 Testing environment...")
    
    # Check critical environment variables
    critical_vars = ['PORT', 'HOST', 'DEBUG', 'API_CALLS_ENABLED']
    for var in critical_vars:
        value = os.getenv(var, 'Not set')
        print(f"  {var}: {value}")
    
    # Check Railway-specific variables
    railway_vars = ['RAILWAY_ENVIRONMENT', 'RAILWAY_PROJECT_ID', 'RAILWAY_SERVICE_ID']
    for var in railway_vars:
        value = os.getenv(var, 'Not set')
        print(f"  {var}: {value}")

def test_imports():
    """Test critical imports"""
    print("\n📦 Testing imports...")
    
    try:
        import flask
        print("  ✅ Flask imported successfully")
    except Exception as e:
        print(f"  ❌ Flask import failed: {e}")
        return False
    
    try:
        import requests
        print("  ✅ Requests imported successfully")
    except Exception as e:
        print(f"  ❌ Requests import failed: {e}")
        return False
    
    try:
        import numpy
        print("  ✅ NumPy imported successfully")
    except Exception as e:
        print(f"  ❌ NumPy import failed: {e}")
        return False
    
    try:
        import sklearn
        print("  ✅ Scikit-learn imported successfully")
    except Exception as e:
        print(f"  ❌ Scikit-learn import failed: {e}")
        return False
    
    return True

def test_app_import():
    """Test Flask app import"""
    print("\n🚀 Testing Flask app import...")
    
    try:
        from app import app
        print("  ✅ Flask app imported successfully")
        return app
    except Exception as e:
        print(f"  ❌ Flask app import failed: {e}")
        print("  Full traceback:")
        traceback.print_exc()
        return None

def test_health_endpoint(app):
    """Test health endpoint"""
    if not app:
        return False
    
    print("\n🏥 Testing health endpoint...")
    
    try:
        with app.test_client() as client:
            response = client.get('/health')
            print(f"  ✅ Health endpoint: {response.status_code} - {response.data.decode()}")
            
            # Test detailed health endpoint
            response = client.get('/health/detailed')
            print(f"  ✅ Detailed health endpoint: {response.status_code}")
            
            return True
    except Exception as e:
        print(f"  ❌ Health endpoint test failed: {e}")
        return False

def test_knowledge_base():
    """Test knowledge base access"""
    print("\n📚 Testing knowledge base...")
    
    knowledge_base_path = Path(__file__).parent / 'knowledge_base'
    if not knowledge_base_path.exists():
        print(f"  ❌ Knowledge base directory not found: {knowledge_base_path}")
        return False
    
    txt_files = list(knowledge_base_path.glob('*.txt'))
    if not txt_files:
        print(f"  ❌ No .txt files found in knowledge base")
        return False
    
    print(f"  ✅ Found {len(txt_files)} knowledge base files")
    return True

def main():
    """Main test function"""
    print("🧪 Railway Deployment Test Suite")
    print("=" * 50)
    
    # Test environment
    test_environment()
    
    # Test imports
    if not test_imports():
        print("\n❌ Critical imports failed")
        sys.exit(1)
    
    # Test knowledge base
    if not test_knowledge_base():
        print("\n❌ Knowledge base test failed")
        sys.exit(1)
    
    # Test Flask app
    app = test_app_import()
    if not app:
        print("\n❌ Flask app import failed")
        sys.exit(1)
    
    # Test health endpoint
    if not test_health_endpoint(app):
        print("\n❌ Health endpoint test failed")
        sys.exit(1)
    
    print("\n✅ All tests passed!")
    print("🚀 Application should be ready for deployment")

if __name__ == '__main__':
    main()
