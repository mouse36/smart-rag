"""
JSONBin API Client for User Authentication
Handles user registration, login, and account management using JSONBin.io
"""

import requests
import json
import bcrypt
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class JSONBinClient:
    """Client for interacting with JSONBin.io API for user authentication"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.JSONBIN_BASE_URL
        self.api_key = config.JSONBIN_API_KEY
        self.bin_id = config.JSONBIN_BIN_ID
        
        self.headers = {
            'Content-Type': 'application/json',
            'X-Master-Key': self.api_key,
            'X-Bin-Meta': 'false'  # Don't include metadata in response
        }
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def is_ready(self) -> bool:
        """Check if the JSONBin client is properly configured"""
        return bool(self.api_key and self.bin_id)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False
    
    def _make_request(self, method: str, url: str, **kwargs) -> Tuple[bool, Dict[str, Any]]:
        """Make HTTP request with error handling"""
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 401:
                logger.error("JSONBin API authentication failed - check API key")
                return False, {"error": "api_auth_failed", "message": "Invalid API key"}
            elif response.status_code == 404:
                logger.error("JSONBin bin not found - check bin ID")
                return False, {"error": "bin_not_found", "message": "Bin not found"}
            elif response.status_code == 429:
                logger.warning("JSONBin API rate limit exceeded")
                # Extract retry-after header if available
                retry_after = response.headers.get('Retry-After', '60')
                return False, {"error": "rate_limit", "message": f"Rate limit exceeded. Please try again in {retry_after} seconds."}
            else:
                logger.error(f"JSONBin API error: {response.status_code} - {response.text}")
                return False, {"error": "api_error", "message": f"API error: {response.status_code}"}
                
        except requests.exceptions.Timeout:
            logger.error("JSONBin API request timeout")
            return False, {"error": "timeout", "message": "Request timeout"}
        except requests.exceptions.ConnectionError:
            logger.error("JSONBin API connection error")
            return False, {"error": "connection_error", "message": "Unable to connect to JSONBin API"}
        except Exception as e:
            logger.error(f"Unexpected error in JSONBin request: {str(e)}")
            return False, {"error": "unexpected_error", "message": f"Unexpected error: {str(e)}"}
    
    def get_accounts_data(self) -> Tuple[bool, Dict[str, Any]]:
        """Retrieve all accounts data from the bin"""
        url = f"{self.base_url}/{self.bin_id}/latest"
        
        success, result = self._make_request('GET', url)
        
        if not success:
            return False, result
        
        # If the bin is empty or doesn't exist yet, return empty accounts list
        accounts_data = result
        if not accounts_data or 'accounts' not in accounts_data:
            return True, {"accounts": []}
        
        return True, accounts_data
    
    def save_accounts_data(self, accounts_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Save accounts data to the bin"""
        url = f"{self.base_url}/{self.bin_id}"
        
        # Add metadata
        data_to_save = {
            **accounts_data,
            "last_updated": datetime.now().isoformat(),
            "version": accounts_data.get("version", 0) + 1
        }
        
        success, result = self._make_request('PUT', url, json=data_to_save)
        
        if not success:
            return False, result
        
        logger.info(f"Successfully saved accounts data (version {data_to_save['version']})")
        return True, {"message": "Accounts data saved successfully"}
    
    def register_user(self, username: str, password: str, phone_number: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Register a new user with the new account format"""
        try:
            # Validate input
            if not username or not password:
                return False, {"error": "validation_error", "message": "Username and password are required."}
            
            # Get current accounts data
            success, accounts_data = self.get_accounts_data()
            if not success:
                return False, accounts_data
            
            accounts = accounts_data.get("accounts", [])
            
            # Check if username already exists
            for account in accounts:
                if account.get("username", "").lower() == username.lower():
                    return False, {"error": "user_exists", "message": "Username is taken. Please choose a different username."}
            
            # Create new account
            new_account = {
                "username": username,
                "password-hash": self._hash_password(password),
                "phone-number": phone_number or "",
                "status": "pending",  # Default to pending for new signups
                "admin": False,
                "online": True,
                "last-seen": datetime.now().isoformat(),
                "superpower": "",
                "chat-history": []
            }
            
            # Add account to the list
            accounts.append(new_account)
            
            # Save updated data
            updated_data = {"accounts": accounts}
            success, result = self.save_accounts_data(updated_data)
            
            if not success:
                return False, result
            
            logger.info(f"Successfully registered user: {username}")
            return True, {
                "message": "User registered successfully",
                "username": username,
                "created_at": new_account["last-seen"]
            }
            
        except Exception as e:
            logger.error(f"Error registering user {username}: {str(e)}")
            return False, {"error": "registration_error", "message": f"Registration failed: {str(e)}"}
    
    def login_user(self, username: str, password: str) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user login with new account format"""
        try:
            # Validate input
            if not username or not password:
                return False, {"error": "validation_error", "message": "Username and password are required"}
            
            # Get current accounts data
            success, accounts_data = self.get_accounts_data()
            if not success:
                return False, accounts_data
            
            accounts = accounts_data.get("accounts", [])
            
            # Find account
            account_found = None
            account_index = None
            for i, account in enumerate(accounts):
                if account.get("username", "").lower() == username.lower():
                    account_found = account
                    account_index = i
                    break
            
            if not account_found:
                return False, {"error": "user_not_found", "message": "No account found with this username. Please contact support if you believe this is an error."}
            
            # Check if account status allows login
            account_status = account_found.get("status", "approved")
            if account_status == "deactivated":
                return False, {"error": "account_disabled", "message": "This account has been deleted. Please contact support if you believe this is an error."}
            elif account_status == "pending":
                return False, {"error": "account_pending", "message": "Account is pending approval from administrators. Please wait until your account is approved to login."}
            
            # Verify password using bcrypt
            stored_hash = account_found.get("password-hash", "")
            if not self._verify_password(password, stored_hash):
                return False, {"error": "invalid_password", "message": "Incorrect password."}
            
            # Update last seen time and online status
            accounts[account_index]["last-seen"] = datetime.now().isoformat()
            accounts[account_index]["online"] = True
            
            # Save updated data
            updated_data = {"accounts": accounts}
            success, result = self.save_accounts_data(updated_data)
            
            if not success:
                logger.warning(f"Failed to update last login for user {username}")
                # Don't fail the login for this, just log the warning
            
            logger.info(f"Successfully logged in user: {username}")
            return True, {
                "message": "Login successful",
                "username": username,
                "last_login": accounts[account_index]["last-seen"],
                "created_at": account_found.get("last-seen")
            }
            
        except Exception as e:
            logger.error(f"Error logging in user {username}: {str(e)}")
            return False, {"error": "login_error", "message": f"Login failed: {str(e)}"}
    
    def get_user_info(self, username: str) -> Tuple[bool, Dict[str, Any]]:
        """Get account information (without password)"""
        try:
            # Get current accounts data
            success, accounts_data = self.get_accounts_data()
            if not success:
                return False, accounts_data
            
            accounts = accounts_data.get("accounts", [])
            
            # Find account
            for account in accounts:
                if account.get("username", "").lower() == username.lower():
                    # Return account info without password hash
                    account_info = {
                        "username": account.get("username"),
                        "phone-number": account.get("phone-number"),
                        "status": account.get("status"),
                        "admin": account.get("admin"),
                        "online": account.get("online"),
                        "last-seen": account.get("last-seen"),
                        "superpower": account.get("superpower"),
                        "chat-history": account.get("chat-history", [])
                    }
                    return True, account_info
            
            return False, {"error": "user_not_found", "message": "User not found"}
            
        except Exception as e:
            logger.error(f"Error getting user info for {username}: {str(e)}")
            return False, {"error": "user_info_error", "message": f"Failed to get user info: {str(e)}"}
    
    def list_users(self) -> Tuple[bool, Dict[str, Any]]:
        """List all accounts (admin function)"""
        try:
            # Get current accounts data
            success, accounts_data = self.get_accounts_data()
            if not success:
                return False, accounts_data
            
            accounts = accounts_data.get("accounts", [])
            
            # Return accounts without password hashes
            account_list = []
            for account in accounts:
                account_info = {
                    "username": account.get("username"),
                    "phone-number": account.get("phone-number"),
                    "status": account.get("status"),
                    "admin": account.get("admin"),
                    "online": account.get("online"),
                    "last-seen": account.get("last-seen"),
                    "superpower": account.get("superpower")
                }
                account_list.append(account_info)
            
            return True, {
                "users": account_list,  # Keep "users" key for API compatibility
                "total_count": len(account_list),
                "last_updated": accounts_data.get("last_updated"),
                "version": accounts_data.get("version", 0)
            }
            
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return False, {"error": "list_users_error", "message": f"Failed to list users: {str(e)}"}
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, Dict[str, Any]]:
        """Change account password"""
        try:
            # Validate input
            if not username or not old_password or not new_password:
                return False, {"error": "validation_error", "message": "All fields are required"}
            
            # First verify current credentials
            success, login_result = self.login_user(username, old_password)
            if not success:
                return False, {"error": "invalid_credentials", "message": "Current password is incorrect"}
            
            # Get current accounts data
            success, accounts_data = self.get_accounts_data()
            if not success:
                return False, accounts_data
            
            accounts = accounts_data.get("accounts", [])
            
            # Find and update account
            for i, account in enumerate(accounts):
                if account.get("username", "").lower() == username.lower():
                    accounts[i]["password-hash"] = self._hash_password(new_password)
                    accounts[i]["last-seen"] = datetime.now().isoformat()
                    break
            
            # Save updated data
            updated_data = {"accounts": accounts}
            success, result = self.save_accounts_data(updated_data)
            
            if not success:
                return False, result
            
            logger.info(f"Successfully changed password for user: {username}")
            return True, {"message": "Password changed successfully"}
            
        except Exception as e:
            logger.error(f"Error changing password for user {username}: {str(e)}")
            return False, {"error": "password_change_error", "message": f"Password change failed: {str(e)}"}
    
    def logout_user(self, username: str) -> Tuple[bool, Dict[str, Any]]:
        """Update user's last-seen time and set online to false when logging out"""
        try:
            # Validate input
            if not username:
                return False, {"error": "validation_error", "message": "Username is required"}
            
            # Get current accounts data
            success, accounts_data = self.get_accounts_data()
            if not success:
                return False, accounts_data
            
            accounts = accounts_data.get("accounts", [])
            
            # Find and update account
            account_found = False
            for i, account in enumerate(accounts):
                if account.get("username", "").lower() == username.lower():
                    accounts[i]["last-seen"] = datetime.now().isoformat()
                    accounts[i]["online"] = False
                    account_found = True
                    break
            
            if not account_found:
                return False, {"error": "user_not_found", "message": "User not found"}
            
            # Save updated data
            updated_data = {"accounts": accounts}
            success, result = self.save_accounts_data(updated_data)
            
            if not success:
                return False, result
            
            logger.info(f"Successfully logged out user: {username}")
            return True, {"message": "User logged out successfully"}
            
        except Exception as e:
            logger.error(f"Error logging out user {username}: {str(e)}")
            return False, {"error": "logout_error", "message": f"Logout failed: {str(e)}"}
    
    def test_connection(self) -> Tuple[bool, Dict[str, Any]]:
        """Test connection to JSONBin API"""
        try:
            url = f"{self.base_url}/{self.bin_id}/latest"
            success, result = self._make_request('GET', url)
            
            if success:
                return True, {"message": "JSONBin connection successful", "data": result}
            else:
                return False, result
                
        except Exception as e:
            logger.error(f"JSONBin connection test failed: {str(e)}")
            return False, {"error": "connection_test_failed", "message": str(e)}
