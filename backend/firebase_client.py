"""
Firebase Firestore Client for User Authentication
Handles user registration, login, and account management using Firebase Firestore
"""

import firebase_admin
from firebase_admin import credentials, firestore
import bcrypt
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class FirebaseClient:
    """Client for interacting with Firebase Firestore for user authentication"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize Firebase if not already initialized
        if not firebase_admin._apps:
            # Use service account key if available, otherwise use default credentials
            if hasattr(config, 'FIREBASE_SERVICE_ACCOUNT_KEY') and config.FIREBASE_SERVICE_ACCOUNT_KEY:
                cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_KEY)
                firebase_admin.initialize_app(cred)
            else:
                # Use default credentials (for local development or when using Application Default Credentials)
                firebase_admin.initialize_app()
        
        # Get Firestore client
        self.db = firestore.client()
        self.accounts_collection = self.db.collection('accounts')
        
    def is_ready(self) -> bool:
        """Check if the Firebase client is properly configured"""
        try:
            # Test connection by trying to access the collection
            self.accounts_collection.limit(1).get()
            return True
        except Exception as e:
            logger.error(f"Firebase connection test failed: {str(e)}")
            return False
    
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
    
    def get_accounts_data(self) -> Tuple[bool, Dict[str, Any]]:
        """Retrieve all accounts data from Firestore"""
        try:
            # Get all documents from the accounts collection
            docs = self.accounts_collection.stream()
            accounts = []
            
            for doc in docs:
                account_data = doc.to_dict()
                account_data['id'] = doc.id  # Add document ID
                accounts.append(account_data)
            
            return True, {"accounts": accounts}
            
        except Exception as e:
            logger.error(f"Error getting accounts data: {str(e)}")
            return False, {"error": "firebase_error", "message": f"Failed to get accounts data: {str(e)}"}
    
    def save_accounts_data(self, accounts_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Save accounts data to Firestore (batch update)"""
        try:
            # This method is kept for compatibility but Firestore doesn't need it
            # Individual account operations are handled directly
            return True, {"message": "Accounts data structure maintained"}
            
        except Exception as e:
            logger.error(f"Error saving accounts data: {str(e)}")
            return False, {"error": "firebase_error", "message": f"Failed to save accounts data: {str(e)}"}
    
    def register_user(self, email: str, password: str, phone_number: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Register a new user with the new account format"""
        try:
            # Validate input
            if not email or not password:
                return False, {"error": "validation_error", "message": "Email and password are required."}
            
            # Basic email validation
            import re
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, email):
                return False, {"error": "validation_error", "message": "Please enter a valid email address."}
            
            # Check if email already exists
            existing_docs = self.accounts_collection.where('email', '==', email.lower()).limit(1).stream()
            if list(existing_docs):
                return False, {"error": "user_exists", "message": "Email address is already registered. Please use a different email address."}
            
            # Create new account
            new_account = {
                "email": email.lower(),
                "username": email.split("@")[0],
                "profile-picture": "default.svg",
                "password-hash": self._hash_password(password),
                "phone-number": phone_number or "",
                "status": "pending",  # Default to pending for new signups
                "admin": False,
                "online": True,
                "last-seen": datetime.now().isoformat(),
                "superpower": "",
                "chat-history": [],
                "created_at": datetime.now().isoformat()
            }
            
            # Add account to Firestore
            doc_ref = self.accounts_collection.add(new_account)
            
            logger.info(f"Successfully registered user: {email}")
            return True, {
                "message": "User registered successfully",
                "email": email,
                "created_at": new_account["created_at"],
                "user_id": doc_ref[1].id
            }
            
        except Exception as e:
            logger.error(f"Error registering user {email}: {str(e)}")
            return False, {"error": "registration_error", "message": f"Registration failed: {str(e)}"}
    
    def login_user(self, email: str, password: str) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user login with new account format"""
        try:
            # Validate input
            if not email or not password:
                return False, {"error": "validation_error", "message": "Email and password are required"}
            
            # Find account by email
            docs = self.accounts_collection.where('email', '==', email.lower()).limit(1).stream()
            account_docs = list(docs)
            
            if not account_docs:
                return False, {"error": "user_not_found", "message": "No account found with this email address. Please contact support if you believe this is an error."}
            
            account_doc = account_docs[0]
            account_found = account_doc.to_dict()
            account_found['id'] = account_doc.id
            
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
            self.accounts_collection.document(account_doc.id).update({
                "last-seen": datetime.now().isoformat(),
                "online": True
            })
            
            logger.info(f"Successfully logged in user: {email}")
            return True, {
                "message": "Login successful",
                "email": email,
                "username": account_found.get("username", email.split("@")[0]),
                "profile_picture": account_found.get("profile-picture", "default.svg"),
                "last_login": datetime.now().isoformat(),
                "created_at": account_found.get("created_at"),
                "user_id": account_doc.id
            }
            
        except Exception as e:
            logger.error(f"Error logging in user {email}: {str(e)}")
            return False, {"error": "login_error", "message": f"Login failed: {str(e)}"}
    
    def get_user_info(self, email: str) -> Tuple[bool, Dict[str, Any]]:
        """Get account information (without password)"""
        try:
            # Find account by email
            docs = self.accounts_collection.where('email', '==', email.lower()).limit(1).stream()
            account_docs = list(docs)
            
            if not account_docs:
                return False, {"error": "user_not_found", "message": "User not found"}
            
            account_doc = account_docs[0]
            account = account_doc.to_dict()
            
            # Return account info without password hash
            account_info = {
                "id": account_doc.id,
                "email": account.get("email"),
                "username": account.get("username"),
                "profile-picture": account.get("profile-picture", "default.svg"),
                "phone-number": account.get("phone-number"),
                "status": account.get("status"),
                "admin": account.get("admin"),
                "online": account.get("online"),
                "last-seen": account.get("last-seen"),
                "superpower": account.get("superpower"),
                "chat-history": account.get("chat-history", []),
                "created_at": account.get("created_at")
            }
            return True, account_info
            
        except Exception as e:
            logger.error(f"Error getting user info for {email}: {str(e)}")
            return False, {"error": "user_info_error", "message": f"Failed to get user info: {str(e)}"}
    
    def list_users(self) -> Tuple[bool, Dict[str, Any]]:
        """List all accounts (admin function)"""
        try:
            # Get all documents from the accounts collection
            docs = self.accounts_collection.stream()
            account_list = []
            
            for doc in docs:
                account = doc.to_dict()
                # Return accounts without password hashes
                account_info = {
                    "id": doc.id,
                    "email": account.get("email"),
                    "username": account.get("username"),
                    "phone-number": account.get("phone-number"),
                    "status": account.get("status"),
                    "admin": account.get("admin"),
                    "online": account.get("online"),
                    "last-seen": account.get("last-seen"),
                    "superpower": account.get("superpower"),
                    "created_at": account.get("created_at")
                }
                account_list.append(account_info)
            
            return True, {
                "users": account_list,  # Keep "users" key for API compatibility
                "total_count": len(account_list),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return False, {"error": "list_users_error", "message": f"Failed to list users: {str(e)}"}
    
    def change_password(self, email: str, old_password: str, new_password: str) -> Tuple[bool, Dict[str, Any]]:
        """Change account password"""
        try:
            # Validate input
            if not email or not old_password or not new_password:
                return False, {"error": "validation_error", "message": "All fields are required"}
            
            # First verify current credentials
            success, login_result = self.login_user(email, old_password)
            if not success:
                return False, {"error": "invalid_credentials", "message": "Current password is incorrect"}
            
            # Find account by email
            docs = self.accounts_collection.where('email', '==', email.lower()).limit(1).stream()
            account_docs = list(docs)
            
            if not account_docs:
                return False, {"error": "user_not_found", "message": "User not found"}
            
            account_doc = account_docs[0]
            
            # Update password
            self.accounts_collection.document(account_doc.id).update({
                "password-hash": self._hash_password(new_password),
                "last-seen": datetime.now().isoformat()
            })
            
            logger.info(f"Successfully changed password for user: {email}")
            return True, {"message": "Password changed successfully"}
            
        except Exception as e:
            logger.error(f"Error changing password for user {email}: {str(e)}")
            return False, {"error": "password_change_error", "message": f"Password change failed: {str(e)}"}
    
    def logout_user(self, email: str) -> Tuple[bool, Dict[str, Any]]:
        """Update user's last-seen time and set online to false when logging out"""
        try:
            # Validate input
            if not email:
                return False, {"error": "validation_error", "message": "Email is required"}
            
            # Find account by email
            docs = self.accounts_collection.where('email', '==', email.lower()).limit(1).stream()
            account_docs = list(docs)
            
            if not account_docs:
                return False, {"error": "user_not_found", "message": "User not found"}
            
            account_doc = account_docs[0]
            
            # Update account
            self.accounts_collection.document(account_doc.id).update({
                "last-seen": datetime.now().isoformat(),
                "online": False
            })
            
            logger.info(f"Successfully logged out user: {email}")
            return True, {"message": "User logged out successfully"}
            
        except Exception as e:
            logger.error(f"Error logging out user {email}: {str(e)}")
            return False, {"error": "logout_error", "message": f"Logout failed: {str(e)}"}
    
    def get_user_chat_history(self, email: str) -> Tuple[bool, Dict[str, Any]]:
        """Get chat history for a specific user"""
        try:
            # Get user info which includes chat history
            success, user_info = self.get_user_info(email)
            if not success:
                return False, user_info
            
            chat_history = user_info.get("chat-history", [])
            
            return True, {
                "chat_history": chat_history,
                "total_chats": len(chat_history)
            }
            
        except Exception as e:
            logger.error(f"Error getting chat history for user {email}: {str(e)}")
            return False, {"error": "chat_history_error", "message": f"Failed to get chat history: {str(e)}"}
    
    def save_message_to_chat(self, email: str, chat_id: int, message: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
        """Save a message to a specific chat for a user"""
        try:
            # Find account by email
            docs = self.accounts_collection.where('email', '==', email.lower()).limit(1).stream()
            account_docs = list(docs)
            
            if not account_docs:
                return False, {"error": "user_not_found", "message": "User not found"}
            
            account_doc = account_docs[0]
            account = account_doc.to_dict()
            
            # Get chat history
            chat_history = account.get("chat-history", [])
            
            # Validate chat_id
            if chat_id < 1 or chat_id > len(chat_history):
                return False, {"error": "invalid_chat_id", "message": "Invalid chat ID"}
            
            # Add message to the specified chat (chat_id is 1-indexed)
            chat_index = chat_id - 1
            if "messages" not in chat_history[chat_index]:
                chat_history[chat_index]["messages"] = []
            
            chat_history[chat_index]["messages"].append(message)
            
            # Update the document
            self.accounts_collection.document(account_doc.id).update({
                "chat-history": chat_history
            })
            
            logger.info(f"Successfully saved message to chat {chat_id} for user: {email}")
            return True, {"message": "Message saved successfully"}
            
        except Exception as e:
            logger.error(f"Error saving message for user {email}: {str(e)}")
            return False, {"error": "save_message_error", "message": f"Failed to save message: {str(e)}"}
    
    def create_new_chat(self, email: str, initial_message: Dict[str, str], user_first_message: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
        """Create a new chat for a user with initial messages"""
        try:
            # Find account by email
            docs = self.accounts_collection.where('email', '==', email.lower()).limit(1).stream()
            account_docs = list(docs)
            
            if not account_docs:
                return False, {"error": "user_not_found", "message": "User not found"}
            
            account_doc = account_docs[0]
            account = account_doc.to_dict()
            
            # Get current chat history
            chat_history = account.get("chat-history", [])
            
            # Create new chat object
            new_chat = {
                "title": "Untitled Chat",
                "messages": [initial_message, user_first_message]
            }
            
            # Add new chat to the beginning of the array
            chat_history.insert(0, new_chat)
            
            # Update the document
            self.accounts_collection.document(account_doc.id).update({
                "chat-history": chat_history
            })
            
            logger.info(f"Successfully created new chat for user: {email}")
            return True, {
                "message": "New chat created successfully",
                "chat_id": 1,  # New chat is always at position 1
                "total_chats": len(chat_history)
            }
            
        except Exception as e:
            logger.error(f"Error creating new chat for user {email}: {str(e)}")
            return False, {"error": "create_chat_error", "message": f"Failed to create new chat: {str(e)}"}
    
    def update_chat_title(self, email: str, chat_id: int, new_title: str) -> Tuple[bool, Dict[str, Any]]:
        """Update the title of a specific chat for a user"""
        try:
            # Find account by email
            docs = self.accounts_collection.where('email', '==', email.lower()).limit(1).stream()
            account_docs = list(docs)
            
            if not account_docs:
                return False, {"error": "user_not_found", "message": "User not found"}
            
            account_doc = account_docs[0]
            account = account_doc.to_dict()
            
            # Get chat history
            chat_history = account.get("chat-history", [])
            
            # Validate chat_id
            if chat_id < 1 or chat_id > len(chat_history):
                return False, {"error": "invalid_chat_id", "message": "Invalid chat ID"}
            
            # Update chat title (chat_id is 1-indexed)
            chat_index = chat_id - 1
            chat_history[chat_index]["title"] = new_title
            
            # Update the document
            self.accounts_collection.document(account_doc.id).update({
                "chat-history": chat_history
            })
            
            logger.info(f"Successfully updated chat {chat_id} title for user: {email}")
            return True, {"message": "Chat title updated successfully"}
            
        except Exception as e:
            logger.error(f"Error updating chat title for user {email}: {str(e)}")
            return False, {"error": "update_title_error", "message": f"Failed to update chat title: {str(e)}"}
    
    def test_connection(self) -> Tuple[bool, Dict[str, Any]]:
        """Test connection to Firebase Firestore"""
        try:
            # Test connection by trying to access the collection
            docs = self.accounts_collection.limit(1).stream()
            list(docs)  # Consume the iterator
            
            return True, {"message": "Firebase Firestore connection successful"}
                
        except Exception as e:
            logger.error(f"Firebase connection test failed: {str(e)}")
            return False, {"error": "connection_test_failed", "message": str(e)}
