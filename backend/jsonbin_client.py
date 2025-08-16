"""
JSONBin API Client for User Authentication
Handles user registration, login, and account management using JSONBin.io
"""

import requests
import json
import hashlib
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
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
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
    
    def get_users_data(self) -> Tuple[bool, Dict[str, Any]]:
        """Retrieve all users data from the bin"""
        url = f"{self.base_url}/bins/{self.bin_id}/latest"
        
        success, result = self._make_request('GET', url)
        
        if not success:
            return False, result
        
        # If the bin is empty or doesn't exist yet, return empty users list
        users_data = result.get('record', {})
        if not users_data or 'users' not in users_data:
            return True, {"users": []}
        
        return True, users_data
    
    def save_users_data(self, users_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Save users data to the bin"""
        url = f"{self.base_url}/bins/{self.bin_id}"
        
        # Add metadata
        data_to_save = {
            **users_data,
            "last_updated": datetime.now().isoformat(),
            "version": users_data.get("version", 0) + 1
        }
        
        success, result = self._make_request('PUT', url, json=data_to_save)
        
        if not success:
            return False, result
        
        logger.info(f"Successfully saved users data (version {data_to_save['version']})")
        return True, {"message": "Users data saved successfully"}
    
    def register_user(self, username: str, password: str) -> Tuple[bool, Dict[str, Any]]:
        """Register a new user"""
        try:
            # Validate input
            if not username or not password:
                return False, {"error": "validation_error", "message": "Username and password are required"}
            
            if len(username) < 3:
                return False, {"error": "validation_error", "message": "Username must be at least 3 characters long"}
            
            if len(password) < 6:
                return False, {"error": "validation_error", "message": "Password must be at least 6 characters long"}
            
            # Get current users data
            success, users_data = self.get_users_data()
            if not success:
                return False, users_data
            
            users = users_data.get("users", [])
            
            # Check if username already exists
            for user in users:
                if user.get("username", "").lower() == username.lower():
                    return False, {"error": "user_exists", "message": "Username already exists"}
            
            # Create new user
            new_user = {
                "username": username,
                "password_hash": self._hash_password(password),
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "is_active": True
            }
            
            # Add user to the list
            users.append(new_user)
            
            # Save updated data
            updated_data = {"users": users}
            success, result = self.save_users_data(updated_data)
            
            if not success:
                return False, result
            
            logger.info(f"Successfully registered user: {username}")
            return True, {
                "message": "User registered successfully",
                "username": username,
                "created_at": new_user["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Error registering user {username}: {str(e)}")
            return False, {"error": "registration_error", "message": f"Registration failed: {str(e)}"}
    
    def login_user(self, username: str, password: str) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user login"""
        try:
            # Validate input
            if not username or not password:
                return False, {"error": "validation_error", "message": "Username and password are required"}
            
            # Get current users data
            success, users_data = self.get_users_data()
            if not success:
                return False, users_data
            
            users = users_data.get("users", [])
            
            # Find user
            user_found = None
            user_index = None
            for i, user in enumerate(users):
                if user.get("username", "").lower() == username.lower():
                    user_found = user
                    user_index = i
                    break
            
            if not user_found:
                return False, {"error": "user_not_found", "message": "No account found with this username"}
            
            # Check if account is active
            if not user_found.get("is_active", True):
                return False, {"error": "account_disabled", "message": "Account is disabled"}
            
            # Verify password
            password_hash = self._hash_password(password)
            if user_found.get("password_hash") != password_hash:
                return False, {"error": "invalid_password", "message": "Incorrect password"}
            
            # Update last login time
            users[user_index]["last_login"] = datetime.now().isoformat()
            
            # Save updated data
            updated_data = {"users": users}
            success, result = self.save_users_data(updated_data)
            
            if not success:
                logger.warning(f"Failed to update last login for user {username}")
                # Don't fail the login for this, just log the warning
            
            logger.info(f"Successfully logged in user: {username}")
            return True, {
                "message": "Login successful",
                "username": username,
                "last_login": users[user_index]["last_login"],
                "created_at": user_found.get("created_at")
            }
            
        except Exception as e:
            logger.error(f"Error logging in user {username}: {str(e)}")
            return False, {"error": "login_error", "message": f"Login failed: {str(e)}"}
    
    def get_user_info(self, username: str) -> Tuple[bool, Dict[str, Any]]:
        """Get user information (without password)"""
        try:
            # Get current users data
            success, users_data = self.get_users_data()
            if not success:
                return False, users_data
            
            users = users_data.get("users", [])
            
            # Find user
            for user in users:
                if user.get("username", "").lower() == username.lower():
                    # Return user info without password hash
                    user_info = {
                        "username": user.get("username"),
                        "created_at": user.get("created_at"),
                        "last_login": user.get("last_login"),
                        "is_active": user.get("is_active", True)
                    }
                    return True, user_info
            
            return False, {"error": "user_not_found", "message": "User not found"}
            
        except Exception as e:
            logger.error(f"Error getting user info for {username}: {str(e)}")
            return False, {"error": "user_info_error", "message": f"Failed to get user info: {str(e)}"}
    
    def list_users(self) -> Tuple[bool, Dict[str, Any]]:
        """List all users (admin function)"""
        try:
            # Get current users data
            success, users_data = self.get_users_data()
            if not success:
                return False, users_data
            
            users = users_data.get("users", [])
            
            # Return users without password hashes
            user_list = []
            for user in users:
                user_info = {
                    "username": user.get("username"),
                    "created_at": user.get("created_at"),
                    "last_login": user.get("last_login"),
                    "is_active": user.get("is_active", True)
                }
                user_list.append(user_info)
            
            return True, {
                "users": user_list,
                "total_count": len(user_list),
                "last_updated": users_data.get("last_updated"),
                "version": users_data.get("version", 0)
            }
            
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return False, {"error": "list_users_error", "message": f"Failed to list users: {str(e)}"}
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, Dict[str, Any]]:
        """Change user password"""
        try:
            # Validate input
            if not username or not old_password or not new_password:
                return False, {"error": "validation_error", "message": "All fields are required"}
            
            if len(new_password) < 6:
                return False, {"error": "validation_error", "message": "New password must be at least 6 characters long"}
            
            # First verify current credentials
            success, login_result = self.login_user(username, old_password)
            if not success:
                return False, {"error": "invalid_credentials", "message": "Current password is incorrect"}
            
            # Get current users data
            success, users_data = self.get_users_data()
            if not success:
                return False, users_data
            
            users = users_data.get("users", [])
            
            # Find and update user
            for i, user in enumerate(users):
                if user.get("username", "").lower() == username.lower():
                    users[i]["password_hash"] = self._hash_password(new_password)
                    users[i]["password_changed_at"] = datetime.now().isoformat()
                    break
            
            # Save updated data
            updated_data = {"users": users}
            success, result = self.save_users_data(updated_data)
            
            if not success:
                return False, result
            
            logger.info(f"Successfully changed password for user: {username}")
            return True, {"message": "Password changed successfully"}
            
        except Exception as e:
            logger.error(f"Error changing password for user {username}: {str(e)}")
            return False, {"error": "password_change_error", "message": f"Password change failed: {str(e)}"}
    
    def test_connection(self) -> Tuple[bool, Dict[str, Any]]:
        """Test connection to JSONBin API"""
        try:
            url = f"{self.base_url}/bins/{self.bin_id}/latest"
            success, result = self._make_request('GET', url)
            
            if success:
                return True, {"message": "JSONBin connection successful", "data": result}
            else:
                return False, result
                
        except Exception as e:
            logger.error(f"JSONBin connection test failed: {str(e)}")
            return False, {"error": "connection_test_failed", "message": str(e)}
