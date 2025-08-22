#!/usr/bin/env python3
"""
Test script for Firebase client
"""

import os
import sys
from config import Config
from firebase_client import FirebaseClient

def test_firebase_client():
    """Test the Firebase client functionality"""
    print("Testing Firebase client...")
    
    # Initialize config
    config = Config()
    
    # Check if Firebase is configured
    if not config.FIREBASE_PROJECT_ID:
        print("❌ FIREBASE_PROJECT_ID not set")
        return False
    
    print(f"✅ Firebase Project ID: {config.FIREBASE_PROJECT_ID}")
    
    try:
        # Initialize Firebase client
        firebase_client = FirebaseClient(config)
        
        # Test connection
        print("Testing connection...")
        success, result = firebase_client.test_connection()
        
        if success:
            print("✅ Firebase connection successful")
        else:
            print(f"❌ Firebase connection failed: {result}")
            return False
        
        # Test readiness
        if firebase_client.is_ready():
            print("✅ Firebase client is ready")
        else:
            print("❌ Firebase client is not ready")
            return False
        
        print("✅ All Firebase tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Firebase test failed with exception: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_firebase_client()
    sys.exit(0 if success else 1)
