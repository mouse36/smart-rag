"""
Smart RAG Backend - Virtual Assistant powered by DeepSeek API
Features:
- Vector similarity search for knowledge base retrieval
- DeepSeek API integration for intelligent responses
- RESTful API endpoints for frontend integration
- JWT-based authentication for secure session management
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import json
import time
import jwt
from datetime import datetime, timedelta
from functools import wraps

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime
import stripe

# Import custom modules
from vector_search import VectorSearchEngine
from deepseek_client import DeepSeekClient

from jsonbin_client import JSONBinClient
from config import Config

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize components
config = Config()
vector_engine = VectorSearchEngine(config)
deepseek_client = DeepSeekClient(config)

jsonbin_client = JSONBinClient(config)

# Initialize Stripe
if config.STRIPE_SECRET_KEY:
    stripe.api_key = config.STRIPE_SECRET_KEY

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24  # Tokens expire after 24 hours

# Blacklisted tokens (for logout functionality)
blacklisted_tokens = set()

def generate_jwt_token(user_data: Dict[str, Any]) -> str:
    """Generate a JWT token for authenticated user"""
    payload = {
        'user_id': user_data.get('email'),
        'username': user_data.get('username'),
        'email': user_data.get('email'),
        'profile_picture': user_data.get('profile_picture'),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token"""
    try:
        # Check if token is blacklisted
        if token in blacklisted_tokens:
            return None
        
        # Decode and verify token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token")
        return None
    except Exception as e:
        logger.error(f"Error verifying JWT token: {str(e)}")
        return None

def require_auth(f):
    """Decorator to require authentication for protected endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401
        
        try:
            # Extract token from "Bearer <token>" format
            token = auth_header.split(' ')[1]
        except IndexError:
            return jsonify({'error': 'Invalid authorization header format'}), 401
        
        # Verify token
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user info to request context
        request.user = payload
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify backend status"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'api_mode': {
                'api_calls_enabled': config.API_CALLS_ENABLED,
                'mode': 'live_api' if config.API_CALLS_ENABLED else 'placeholder'
            },
            'components': {
                'vector_engine': vector_engine.is_ready(),
                'deepseek_client': deepseek_client.is_ready(),
                'jsonbin_client': jsonbin_client.is_ready(),
                'stripe_configured': config.is_stripe_configured()
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/chat', methods=['POST'])
@require_auth
def chat():
    """Main chat endpoint for processing user messages - requires authentication"""
    try:
        # Parse request data
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Retrieve relevant context from knowledge base
        relevant_passages = vector_engine.search(user_message, top_k=7)
        
        # Generate response using DeepSeek API
        response = deepseek_client.generate_response(
            user_message=user_message,
            context_passages=relevant_passages
        )
        
        # Log the interaction with user info
        user_email = request.user.get('email', 'unknown')
        logger.info(f"Generated response for user {user_email}: {user_message[:50]}... (Context passages: {len(relevant_passages)})")
        
        return jsonify({
            'response': response,
            'context_sources': len(relevant_passages),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Failed to process message'}), 500



@app.route('/search', methods=['POST'])
def search_knowledge_base():
    """Direct search endpoint for testing knowledge base retrieval"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query'].strip()
        top_k = data.get('top_k', 5)
        
        results = vector_engine.search(query, top_k=top_k)
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/auth/validate-phone', methods=['POST'])
def validate_phone():
    """Validate if a phone number is approved for authentication"""
    try:
        data = request.get_json()
        if not data or 'phone' not in data:
            return jsonify({'error': 'Phone number is required'}), 400
        
        phone = data['phone'].strip()
        if not phone:
            return jsonify({'error': 'Phone number cannot be empty'}), 400
        
        # Normalize the phone number
        normalized_phone = _normalize_phone_number(phone)
        
        # Check if the normalized phone number is in the approved list
        approved_phones = [_normalize_phone_number(p) for p in config.APPROVED_PHONE_NUMBERS]
        is_approved = normalized_phone in approved_phones
        
        logger.info(f"Phone validation request for: {phone} (normalized: {normalized_phone}) - {'Approved' if is_approved else 'Rejected'}")
        
        return jsonify({
            'phone': phone,
            'normalized_phone': normalized_phone,
            'is_approved': is_approved,
            'success': is_approved,  # Add success field for frontend compatibility
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in phone validation endpoint: {str(e)}")
        return jsonify({'error': 'Phone validation failed'}), 500

@app.route('/auth/register', methods=['POST'])
def register_user():
    """Register a new user with email and password"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Register user using JSONBin client
        success, result = jsonbin_client.register_user(email, password)
        
        if success:
            logger.info(f"User registered successfully: {email}")
            return jsonify({
                'success': True,
                'message': result['message'],
                'email': result.get('email', result.get('username')),  # Handle both old and new response formats
                'created_at': result['created_at'],
                'timestamp': datetime.now().isoformat()
            }), 201
        else:
            # Handle different error types
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Registration failed')
            
            if error_type == 'user_exists':
                status_code = 409  # Conflict
            elif error_type == 'validation_error':
                status_code = 400  # Bad Request
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503  # Service Unavailable
                error_message = 'Authentication service temporarily unavailable'
            else:
                status_code = 500  # Internal Server Error
            
            logger.warning(f"User registration failed for {email}: {error_message}")
            return jsonify({
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in user registration endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'registration_error',
            'message': 'Registration failed due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/auth/login', methods=['POST'])
def login_user():
    """Authenticate user login with email and password and return JWT token"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Authenticate user using JSONBin client
        success, result = jsonbin_client.login_user(email, password)
        
        if success:
            logger.info(f"User logged in successfully: {email}")
            
            # Generate JWT token
            token = generate_jwt_token(result)
            
            return jsonify({
                'success': True,
                'message': result['message'],
                'email': result.get('email'),
                'username': result.get('username'),
                'profile_picture': result.get('profile_picture'),
                'last_login': result['last_login'],
                'created_at': result.get('created_at'),
                'token': token,
                'token_expires_in': JWT_EXPIRATION_HOURS * 3600,  # seconds
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            # Handle different error types
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Login failed')
            
            if error_type in ['user_not_found', 'invalid_password']:
                status_code = 401  # Unauthorized
            elif error_type == 'account_disabled':
                status_code = 403  # Forbidden
            elif error_type == 'validation_error':
                status_code = 400  # Bad Request
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503  # Service Unavailable
                error_message = 'Authentication service temporarily unavailable'
            else:
                status_code = 500  # Internal Server Error
            
            logger.warning(f"User login failed for {email}: {error_message}")
            return jsonify({
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in user login endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'login_error',
            'message': 'Login failed due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/auth/logout', methods=['POST'])
@require_auth
def logout_user():
    """Handle user logout, blacklist token, and update account status"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1]
        
        # Blacklist the token
        blacklisted_tokens.add(token)
        logger.info(f"Token blacklisted for user: {request.user.get('email')}")
        
        # Update user logout status using JSONBin client
        email = request.user.get('email')
        success, result = jsonbin_client.logout_user(email)
        
        if success:
            logger.info(f"User logged out successfully: {email}")
            return jsonify({
                'success': True,
                'message': 'Successfully logged out',
                'email': email,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            # Even if JSONBin update fails, we've already blacklisted the token
            logger.warning(f"JSONBin logout update failed for {email}, but token was blacklisted")
            return jsonify({
                'success': True,
                'message': 'Successfully logged out',
                'email': email,
                'timestamp': datetime.now().isoformat()
            }), 200
            
    except Exception as e:
        logger.error(f"Error in user logout endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'logout_error',
            'message': 'Logout failed due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/auth/user/<email>', methods=['GET'])
def get_user_info(email):
    """Get user information (admin endpoint)"""
    try:
        # Basic validation
        if not email or not email.strip():
            return jsonify({'error': 'Email is required'}), 400
        
        # Get user info using JSONBin client
        success, result = jsonbin_client.get_user_info(email.strip())
        
        if success:
            return jsonify({
                'success': True,
                'user': result,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Failed to get user info')
            
            if error_type == 'user_not_found':
                status_code = 404  # Not Found
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503  # Service Unavailable
                error_message = 'Authentication service temporarily unavailable'
            else:
                status_code = 500  # Internal Server Error
            
            return jsonify({
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in get user info endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'user_info_error',
            'message': 'Failed to get user info due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/auth/users', methods=['GET'])
def list_users():
    """List all users (admin endpoint)"""
    try:
        # List users using JSONBin client
        success, result = jsonbin_client.list_users()
        
        if success:
            return jsonify({
                'success': True,
                'users': result['users'],
                'total_count': result['total_count'],
                'last_updated': result.get('last_updated'),
                'version': result.get('version'),
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Failed to list users')
            
            if error_type in ['api_auth_failed', 'bin_not_found']:
                status_code = 503  # Service Unavailable
                error_message = 'Authentication service temporarily unavailable'
            else:
                status_code = 500  # Internal Server Error
            
            return jsonify({
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in list users endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'list_users_error',
            'message': 'Failed to list users due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/auth/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        email = data.get('email', '').strip()
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not email or not old_password or not new_password:
            return jsonify({'error': 'Email, old password, and new password are required'}), 400
        
        # Change password using JSONBin client
        success, result = jsonbin_client.change_password(email, old_password, new_password)
        
        if success:
            logger.info(f"Password changed successfully for user: {email}")
            return jsonify({
                'success': True,
                'message': result['message'],
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Password change failed')
            
            if error_type == 'invalid_credentials':
                status_code = 401  # Unauthorized
            elif error_type == 'validation_error':
                status_code = 400  # Bad Request
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503  # Service Unavailable
                error_message = 'Authentication service temporarily unavailable'
            else:
                status_code = 500  # Internal Server Error
            
            logger.warning(f"Password change failed for {email}: {error_message}")
            return jsonify({
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in change password endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'password_change_error',
            'message': 'Password change failed due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/auth/validate-token', methods=['POST'])
def validate_token():
    """Validate JWT token and return user information"""
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({'error': 'Token is required'}), 400
        
        token = data['token'].strip()
        if not token:
            return jsonify({'error': 'Token cannot be empty'}), 400
        
        # Verify token
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'error': 'invalid_token',
                'message': 'Invalid or expired token'
            }), 401
        
        # Token is valid, return user info
        return jsonify({
            'success': True,
            'user': {
                'email': payload.get('email'),
                'username': payload.get('username'),
                'profile_picture': payload.get('profile_picture')
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in token validation endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'validation_error',
            'message': 'Token validation failed due to server error'
        }), 500

@app.route('/auth/test', methods=['GET'])
def test_auth_connection():
    """Test authentication service connection (admin endpoint)"""
    try:
        success, result = jsonbin_client.test_connection()
        
        if success:
            return jsonify({
                'success': True,
                'message': result['message'],
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'connection_test_failed'),
                'message': result.get('message', 'Connection test failed'),
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        logger.error(f"Error in test auth connection endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'connection_test_error',
            'message': 'Connection test failed due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/chat/history', methods=['GET'])
@require_auth
def get_chat_history():
    """Get chat history for the authenticated user"""
    try:
        # Get authenticated user's email from JWT token
        email = request.user.get('email', '').strip()
        if not email:
            return jsonify({'error': 'User email not found in token'}), 401
        
        # Get chat history using JSONBin client
        success, result = jsonbin_client.get_user_chat_history(email)
        
        if success:
            return jsonify({
                'success': True,
                'chat_history': result['chat_history'],
                'total_chats': result['total_chats'],
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Failed to get chat history')
            
            if error_type == 'user_not_found':
                status_code = 404
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503
                error_message = 'Chat history service temporarily unavailable'
            else:
                status_code = 500
            
            return jsonify({
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in get chat history endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'chat_history_error',
            'message': 'Failed to get chat history due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/chat/save-message', methods=['POST'])
@require_auth
def save_message():
    """Save a message to a user's chat history - requires authentication"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Get authenticated user's email from JWT token
        email = request.user.get('email', '').strip()
        if not email:
            return jsonify({'error': 'User email not found in token'}), 401
        
        chat_id = data.get('chat_id')
        message = data.get('message')
        
        if chat_id is None or not message:
            return jsonify({'error': 'chat_id and message are required'}), 400
        
        if not isinstance(message, dict) or 'from' not in message or 'content' not in message:
            return jsonify({'error': 'Message must be an object with "from" and "content" fields'}), 400
        
        if message['from'] not in ['user', 'chatbot']:
            return jsonify({'error': 'Message "from" field must be "user" or "chatbot"'}), 400
        
        # Save message using JSONBin client
        success, result = jsonbin_client.save_message_to_chat(email, chat_id, message)
        
        if success:
            return jsonify({
                'success': True,
                'message': result['message'],
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Failed to save message')
            
            if error_type == 'user_not_found':
                status_code = 404
            elif error_type == 'invalid_chat_id':
                status_code = 400
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503
                error_message = 'Chat service temporarily unavailable'
            else:
                status_code = 500
            
            return jsonify({
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in save message endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'save_message_error',
            'message': 'Failed to save message due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/chat/create-new-chat', methods=['POST'])
@require_auth
def create_new_chat():
    """Create a new chat for a user - requires authentication"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Get authenticated user's email from JWT token
        email = request.user.get('email', '').strip()
        if not email:
            return jsonify({'error': 'User email not found in token'}), 401
        
        initial_message = data.get('initial_message')
        user_first_message = data.get('user_first_message')
        
        if not initial_message or not user_first_message:
            return jsonify({'error': 'initial_message and user_first_message are required'}), 400
        
        # Validate message format
        for msg, name in [(initial_message, 'initial_message'), (user_first_message, 'user_first_message')]:
            if not isinstance(msg, dict) or 'from' not in msg or 'content' not in msg:
                return jsonify({'error': f'{name} must be an object with "from" and "content" fields'}), 400
        
        # Create new chat using JSONBin client
        success, result = jsonbin_client.create_new_chat(email, initial_message, user_first_message)
        
        if success:
            return jsonify({
                'success': True,
                'message': result['message'],
                'chat_id': result['chat_id'],
                'total_chats': result['total_chats'],
                'timestamp': datetime.now().isoformat()
            }), 201
        else:
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Failed to create new chat')
            
            if error_type == 'user_not_found':
                status_code = 404
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503
                error_message = 'Chat service temporarily unavailable'
            else:
                status_code = 500
            
            return jsonify({
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in create new chat endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'create_chat_error',
            'message': 'Failed to create new chat due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/chat/update-title', methods=['PUT'])
@require_auth
def update_chat_title():
    """Update the title of a specific chat - requires authentication"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Get authenticated user's email from JWT token
        email = request.user.get('email', '').strip()
        if not email:
            return jsonify({'error': 'User email not found in token'}), 401
        
        chat_id = data.get('chat_id')
        new_title = data.get('new_title', '').strip()
        
        if chat_id is None or not new_title:
            return jsonify({'error': 'chat_id and new_title are required'}), 400
        
        # Update chat title using JSONBin client
        success, result = jsonbin_client.update_chat_title(email, chat_id, new_title)
        
        if success:
            return jsonify({
                'success': True,
                'message': result['message'],
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Failed to update chat title')
            
            if error_type == 'user_not_found':
                status_code = 404
            elif error_type == 'invalid_chat_id':
                status_code = 400
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503
                error_message = 'Chat service temporarily unavailable'
            else:
                status_code = 500
            
            return jsonify({
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in update chat title endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'update_title_error',
            'message': 'Failed to update chat title due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/donate/config', methods=['GET'])
def get_donation_config():
    """Get Stripe configuration for frontend"""
    try:
        if not config.is_stripe_configured():
            return jsonify({
                'success': False,
                'error': 'stripe_not_configured',
                'message': 'Stripe payment processing is not configured on this server'
            }), 503
        
        return jsonify({
            'success': True,
            'stripe_publishable_key': config.STRIPE_PUBLISHABLE_KEY,
            'currency': config.STRIPE_CURRENCY
        })
        
    except Exception as e:
        logger.error(f"Error in get donation config endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'config_error',
            'message': 'Failed to get donation configuration'
        }), 500

@app.route('/donate/create-payment-intent', methods=['POST'])
def create_payment_intent():
    """Create a Stripe PaymentIntent for donation"""
    try:
        if not config.is_stripe_configured():
            return jsonify({
                'success': False,
                'error': 'stripe_not_configured',
                'message': 'Stripe payment processing is not configured'
            }), 503
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'invalid_request',
                'message': 'Request body is required'
            }), 400
        
        amount = data.get('amount')
        currency = data.get('currency', config.STRIPE_CURRENCY)
        
        # Validate amount
        if not amount or not isinstance(amount, (int, float)) or amount < 50:  # Minimum $0.50
            return jsonify({
                'success': False,
                'error': 'invalid_amount',
                'message': 'Amount must be at least $0.50 (50 cents)'
            }), 400
        
        # Ensure amount is an integer (cents)
        amount_cents = int(amount)
        
        # Create PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            metadata={
                'type': 'donation',
                'timestamp': datetime.now().isoformat()
            }
        )
        
        logger.info(f"Created payment intent for ${amount_cents/100:.2f} {currency.upper()}")
        
        return jsonify({
            'success': True,
            'client_secret': intent.client_secret,
            'amount': amount_cents,
            'currency': currency
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error in create payment intent: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'stripe_error',
            'message': 'Payment processing error occurred'
        }), 500
        
    except Exception as e:
        logger.error(f"Error in create payment intent endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'payment_error',
            'message': 'Failed to create payment intent'
        }), 500

@app.route('/donate/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        if not config.STRIPE_WEBHOOK_SECRET:
            logger.warning("Stripe webhook secret not configured, skipping verification")
            return jsonify({'status': 'no_verification'}), 200
        
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        if not sig_header:
            logger.error("No Stripe signature header found")
            return jsonify({'error': 'No signature header'}), 400
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, config.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid payload in webhook")
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in webhook")
            return jsonify({'error': 'Invalid signature'}), 400
        
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            logger.info(f"Payment succeeded: {payment_intent['id']} for ${payment_intent['amount']/100:.2f}")
            
            # Here you could save the donation to a database, send confirmation emails, etc.
            
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            logger.warning(f"Payment failed: {payment_intent['id']}")
            
        else:
            logger.info(f"Unhandled event type: {event['type']}")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error in webhook endpoint: {str(e)}")
        return jsonify({'error': 'Webhook error'}), 500

@app.route('/donate/history', methods=['GET'])
def get_donation_history():
    """Get donation history (admin endpoint)"""
    try:
        if not config.is_stripe_configured():
            return jsonify({
                'success': False,
                'error': 'stripe_not_configured',
                'message': 'Stripe is not configured'
            }), 503
        
        # Get recent payment intents
        intents = stripe.PaymentIntent.list(
            limit=50,
            expand=['data.charges']
        )
        
        donations = []
        for intent in intents.data:
            if intent.metadata.get('type') == 'donation' and intent.status == 'succeeded':
                donations.append({
                    'id': intent.id,
                    'amount': intent.amount / 100,  # Convert from cents
                    'currency': intent.currency.upper(),
                    'created': datetime.fromtimestamp(intent.created).isoformat(),
                    'status': intent.status
                })
        
        return jsonify({
            'success': True,
            'donations': donations,
            'total_count': len(donations)
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error in donation history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'stripe_error',
            'message': 'Failed to retrieve donation history'
        }), 500
        
    except Exception as e:
        logger.error(f"Error in donation history endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'history_error',
            'message': 'Failed to get donation history'
        }), 500

def _normalize_phone_number(phone: str) -> str:
    """Normalize phone number for comparison"""
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    
    # If it's a 10-digit number, assume US and add +1
    if len(digits) == 10:
        return '+1' + digits
    
    # If it's 11 digits and starts with 1, add +
    if len(digits) == 11 and digits.startswith('1'):
        return '+' + digits
    
    # For other cases, add + if not present
    if not phone.startswith('+'):
        return '+' + digits
    
    return phone



@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


# Static file serving routes
@app.route('/')
def serve_index():
    """Serve the main HTML page"""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    return send_file(os.path.join(frontend_dir, 'index.html'))

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from frontend directory"""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    return send_from_directory(frontend_dir, filename)


if __name__ == '__main__':
    try:
        # Initialize the vector engine (load embeddings)
        logger.info("Initializing vector search engine...")
        vector_engine.initialize()
        
        # Test connections
        logger.info("Testing component connections...")
        if not vector_engine.is_ready():
            raise Exception("Vector engine not ready")
        if not deepseek_client.is_ready():
            raise Exception("DeepSeek client not ready")

        if not jsonbin_client.is_ready():
            raise Exception("JSONBin client not ready - check JSONBIN_API_KEY and JSONBIN_BIN_ID")
        
        logger.info("All components ready. Starting Flask server...")
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        exit(1)
