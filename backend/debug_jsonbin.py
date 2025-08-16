#!/usr/bin/env python3
"""
Debug JSONBin Connection
Simple script to test JSONBin API connection without our complex client
"""

import os
import requests
from dotenv import load_dotenv

def main():
    print("=" * 50)
    print("JSONBin Debug Test")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv('JSONBIN_API_KEY')
    bin_id = os.getenv('JSONBIN_BIN_ID')
    base_url = os.getenv('JSONBIN_BASE_URL', 'https://api.jsonbin.io/v3')
    
    print(f"Base URL: {base_url}")
    print(f"Bin ID: {bin_id}")
    print(f"API Key length: {len(api_key) if api_key else 0}")
    print(f"API Key starts with: {api_key[:10] if api_key else 'None'}...")
    print()
    
    if not api_key or not bin_id:
        print("❌ Missing API key or Bin ID")
        return
    
    # Test 1: Simple GET request to the bin
    print("Test 1: Direct GET request to bin...")
    url = f"{base_url}/bins/{bin_id}/latest"
    headers = {
        'X-Master-Key': api_key,
        'X-Bin-Meta': 'false'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Success! Bin is accessible")
            data = response.json()
            print(f"Data: {data}")
        elif response.status_code == 401:
            print("❌ Authentication failed - check API key")
        elif response.status_code == 404:
            print("❌ Bin not found - check bin ID")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
    
    print()
    
    # Test 2: Check if we can list bins (to verify API key works)
    print("Test 2: List bins to verify API key...")
    try:
        list_url = f"{base_url}/bins"
        response = requests.get(list_url, headers={'X-Master-Key': api_key}, timeout=10)
        print(f"List bins status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API key works - can list bins")
        else:
            print(f"❌ Cannot list bins: {response.status_code}")
            
    except Exception as e:
        print(f"❌ List bins failed: {str(e)}")

if __name__ == "__main__":
    main()
