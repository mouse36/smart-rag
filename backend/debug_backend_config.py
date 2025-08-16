#!/usr/bin/env python3
"""
Debug Backend Configuration
Check how the backend is actually reading API key and bin ID from config
"""

import os
import sys
from dotenv import load_dotenv
from config import Config
from jsonbin_client import JSONBinClient

def main():
    print("=" * 60)
    print("Backend Configuration Debug")
    print("=" * 60)
    
    # 1. Check raw environment variables
    print("1. RAW ENVIRONMENT VARIABLES:")
    print("-" * 30)
    load_dotenv()
    raw_api_key = os.getenv('JSONBIN_API_KEY')
    raw_bin_id = os.getenv('JSONBIN_BIN_ID')
    raw_base_url = os.getenv('JSONBIN_BASE_URL')
    
    print(f"Raw JSONBIN_API_KEY: {repr(raw_api_key)}")
    print(f"Raw JSONBIN_BIN_ID: {repr(raw_bin_id)}")
    print(f"Raw JSONBIN_BASE_URL: {repr(raw_base_url)}")
    print()
    
    # 2. Check Config class
    print("2. CONFIG CLASS VALUES:")
    print("-" * 30)
    try:
        config = Config()
        print(f"Config JSONBIN_API_KEY: {repr(config.JSONBIN_API_KEY)}")
        print(f"Config JSONBIN_BIN_ID: {repr(config.JSONBIN_BIN_ID)}")
        print(f"Config JSONBIN_BASE_URL: {repr(config.JSONBIN_BASE_URL)}")
        print(f"Config validation result: {config.validate()}")
        print()
        
        # 3. Check JSONBin client initialization
        print("3. JSONBIN CLIENT VALUES:")
        print("-" * 30)
        client = JSONBinClient(config)
        print(f"Client API key: {repr(client.api_key)}")
        print(f"Client bin ID: {repr(client.bin_id)}")
        print(f"Client base URL: {repr(client.base_url)}")
        print(f"Client is_ready(): {client.is_ready()}")
        print()
        
        # 4. Check headers that would be sent
        print("4. REQUEST HEADERS:")
        print("-" * 30)
        print(f"Headers: {client.headers}")
        print()
        
        # 5. Compare values
        print("5. VALUE COMPARISON:")
        print("-" * 30)
        print(f"Raw vs Config API key match: {raw_api_key == config.JSONBIN_API_KEY}")
        print(f"Raw vs Config bin ID match: {raw_bin_id == config.JSONBIN_BIN_ID}")
        print(f"Config vs Client API key match: {config.JSONBIN_API_KEY == client.api_key}")
        print(f"Config vs Client bin ID match: {config.JSONBIN_BIN_ID == client.bin_id}")
        print()
        
        # 6. Check for any whitespace or encoding issues
        print("6. DETAILED ANALYSIS:")
        print("-" * 30)
        if raw_api_key:
            print(f"API key length: {len(raw_api_key)}")
            print(f"API key starts with: '{raw_api_key[:15]}...'")
            print(f"API key ends with: '...{raw_api_key[-15:]}'")
            print(f"API key has whitespace: {raw_api_key != raw_api_key.strip()}")
            
        if raw_bin_id:
            print(f"Bin ID length: {len(raw_bin_id)}")
            print(f"Bin ID: '{raw_bin_id}'")
            print(f"Bin ID has whitespace: {raw_bin_id != raw_bin_id.strip()}")
        print()
        
        # 7. Test actual request construction
        print("7. REQUEST URL CONSTRUCTION:")
        print("-" * 30)
        test_url = f"{client.base_url}/b/{client.bin_id}/latest"
        print(f"Constructed URL: {test_url}")
        print(f"URL length: {len(test_url)}")
        
    except Exception as e:
        print(f"❌ Error during config/client initialization: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
