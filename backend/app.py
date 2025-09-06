"""
Smart RAG Backend - Virtual Assistant powered by DeepSeek API
Features:
- Vector similarity search for knowledge base retrieval
- DeepSeek API integration for intelligent responses
- RESTful API endpoints for frontend integration
- JWT-based authentication for secure session management
"""

from flask import Flask, request, jsonify, send_from_directory, send_file, Response
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
from jsonbin_client import JSONBinClient
from config import Config

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Conditionally import AI/ML modules based on API_CALLS_ENABLED
config = Config()
if config.API_CALLS_ENABLED:
    # Use ultra-lightweight vector search for memory-constrained environments
    try:
        from vector_search_ultra_lightweight import UltraLightweightVectorSearchEngine as VectorSearchEngine
        logger.info("Using ultra-lightweight vector search engine")
    except ImportError:
        # Fallback to memory-optimized vector search
        try:
            from vector_search_memory_optimized import MemoryOptimizedVectorSearchEngine as VectorSearchEngine
            logger.info("Using memory-optimized vector search engine")
        except ImportError:
            # Fallback to original vector search
            from vector_search import VectorSearchEngine
            logger.info("Using standard vector search engine")
    from deepseek_client import DeepSeekClient

# Initialize Flask app
app = Flask(__name__)
# Configure CORS for frontend integration
CORS(app, origins=['https://ai.sunnyminded.com', 'http://localhost:3000', 'http://127.0.0.1:8080', 'http://localhost:8080'])

# Request logging middleware
@app.before_request
def log_request_info():
    """Log all incoming requests with detailed information"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.headers.get('User-Agent', 'unknown')
    method = request.method
    path = request.path
    query_string = request.query_string.decode('utf-8') if request.query_string else ''
    
    logger.info(f"🌐 [REQUEST] {method} {path}{'?' + query_string if query_string else ''} from {client_ip}")
    logger.info(f"🔍 [REQUEST] User-Agent: {user_agent}")
    
    # Log request body for POST/PUT requests (excluding sensitive data)
    if method in ['POST', 'PUT', 'PATCH'] and request.is_json:
        try:
            data = request.get_json()
            if data:
                # Redact sensitive fields
                safe_data = {}
                for key, value in data.items():
                    if key.lower() in ['password', 'token', 'secret', 'key']:
                        safe_data[key] = '[REDACTED]'
                    else:
                        safe_data[key] = value
                logger.info(f"📦 [REQUEST] Request body: {safe_data}")
        except Exception as e:
            logger.warning(f"⚠️ [REQUEST] Could not parse request body: {str(e)}")

@app.after_request
def log_response_info(response):
    """Log response information"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    method = request.method
    path = request.path
    status_code = response.status_code
    
    # Determine log level based on status code
    if status_code >= 500:
        logger.error(f"💥 [RESPONSE] {method} {path} -> {status_code} to {client_ip}")
    elif status_code >= 400:
        logger.warning(f"⚠️ [RESPONSE] {method} {path} -> {status_code} to {client_ip}")
    else:
        logger.info(f"✅ [RESPONSE] {method} {path} -> {status_code} to {client_ip}")
    
    return response

# Initialize components
jsonbin_client = JSONBinClient(config)

# Conditionally initialize AI/ML components
if config.API_CALLS_ENABLED:
    vector_engine = VectorSearchEngine(config)
    deepseek_client = DeepSeekClient(config)
    
    # Initialize with lazy loading if enabled
    if config.LAZY_LOAD_MODEL:
        logger.info("Vector search engine initialized with lazy loading")
    else:
        logger.info("Initializing vector search engine...")
        vector_engine.initialize()
else:
    vector_engine = None
    deepseek_client = None

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
            logger.warning("No Authorization header provided")
            return jsonify({'error': 'Authorization header required'}), 401
        
        try:
            # Extract token from "Bearer <token>" format
            token = auth_header.split(' ')[1]
            logger.info(f"Token extracted: {token[:20]}...")
        except IndexError:
            logger.warning("Invalid authorization header format")
            return jsonify({'error': 'Invalid authorization header format'}), 401
        
        # Verify token
        payload = verify_jwt_token(token)
        if not payload:
            logger.warning("Token verification failed")
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        logger.info(f"Token verified for user: {payload.get('email', 'unknown')}")
        
        # Add user info to request context
        request.user = payload
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify backend status"""
    start_time = time.time()
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.headers.get('User-Agent', 'unknown')
    
    logger.info(f"🏥 [HEALTH CHECK] Request from {client_ip} - User-Agent: {user_agent}")
    
    try:
        # Safely check component readiness
        vector_ready = False
        deepseek_ready = False
        jsonbin_ready = False
        
        logger.info("🔍 [HEALTH CHECK] Checking component readiness...")
        
        try:
            if vector_engine:
                vector_ready = vector_engine.is_ready()
                logger.info(f"🧠 [HEALTH CHECK] Vector engine: {'✅ Ready' if vector_ready else '❌ Not ready'}")
            else:
                logger.warning("🧠 [HEALTH CHECK] Vector engine: Not initialized")
        except Exception as e:
            logger.warning(f"🧠 [HEALTH CHECK] Vector engine readiness check failed: {str(e)}")
        
        try:
            if deepseek_client:
                deepseek_ready = deepseek_client.is_ready()
                logger.info(f"🤖 [HEALTH CHECK] DeepSeek client: {'✅ Ready' if deepseek_ready else '❌ Not ready'}")
            else:
                logger.warning("🤖 [HEALTH CHECK] DeepSeek client: Not initialized")
        except Exception as e:
            logger.warning(f"🤖 [HEALTH CHECK] DeepSeek client readiness check failed: {str(e)}")
        
        try:
            jsonbin_ready = jsonbin_client.is_ready()
            logger.info(f"💾 [HEALTH CHECK] JSONBin client: {'✅ Ready' if jsonbin_ready else '❌ Not ready'}")
        except Exception as e:
            logger.warning(f"💾 [HEALTH CHECK] JSONBin client readiness check failed: {str(e)}")
        
        stripe_configured = config.is_stripe_configured()
        logger.info(f"💳 [HEALTH CHECK] Stripe: {'✅ Configured' if stripe_configured else '❌ Not configured'}")
        
        response_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'api_mode': {
                'api_calls_enabled': config.API_CALLS_ENABLED,
                'mode': 'live_api' if config.API_CALLS_ENABLED else 'placeholder'
            },
            'components': {
                'vector_engine': vector_ready,
                'deepseek_client': deepseek_ready,
                'jsonbin_client': jsonbin_ready,
                'stripe_configured': stripe_configured
            }
        }
        
        response_time = (time.time() - start_time) * 1000
        logger.info(f"✅ [HEALTH CHECK] Completed in {response_time:.2f}ms - Status: Healthy")
        
        return jsonify(response_data), 200
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"💥 [HEALTH CHECK] Failed after {response_time:.2f}ms: {str(e)}")
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
        # Debug: Log authentication info
        logger.info(f"Chat endpoint called by user: {request.user.get('email', 'unknown')}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request data: {request.get_data()}")
        # Parse request data
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Check if API calls are enabled
        if not config.API_CALLS_ENABLED:
            return jsonify({
                'response': 'API calls are currently disabled. This is a placeholder response.',
                'context_sources': 0,
                'timestamp': datetime.now().isoformat()
            }), 200
        
        # Check if AI components are available
        if vector_engine is None or deepseek_client is None:
            return jsonify({
                'response': 'AI components are not available. Please check the backend configuration.',
                'context_sources': 0,
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # Check if DeepSeek API key is configured
        if not config.DEEPSEEK_API_KEY:
            return jsonify({
                'response': 'DeepSeek API key is not configured. Please set the DEEPSEEK_API_KEY environment variable.',
                'context_sources': 0,
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # Initialize vector engine if using lazy loading
        if not vector_engine.is_ready():
            logger.info("Initializing vector engine (lazy loading)...")
            try:
                vector_engine.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize vector engine: {str(e)}")
                return jsonify({
                    'response': f'Failed to initialize AI components: {str(e)}',
                    'context_sources': 0,
                    'timestamp': datetime.now().isoformat()
                }), 503
        
        # Retrieve relevant context from knowledge base
        try:
            relevant_passages = vector_engine.search(user_message, top_k=7)
        except Exception as e:
            logger.error(f"Failed to search knowledge base: {str(e)}")
            return jsonify({
                'response': f'Failed to search knowledge base: {str(e)}',
                'context_sources': 0,
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # Generate response using DeepSeek API
        try:
            response = deepseek_client.generate_response(
                user_message=user_message,
                context_passages=relevant_passages
            )
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            return jsonify({
                'response': f'Failed to generate response: {str(e)}',
                'context_sources': len(relevant_passages),
                'timestamp': datetime.now().isoformat()
            }), 503
        
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
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        logger.error(f"Vector engine ready: {vector_engine.is_ready() if vector_engine else 'None'}")
        logger.error(f"DeepSeek client ready: {deepseek_client.is_ready() if deepseek_client else 'None'}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to process message', 'details': str(e)}), 500



@app.route('/test-components', methods=['GET'])
def test_components():
    """Test endpoint to debug component initialization issues"""
    try:
        results = {
            'config': {
                'api_calls_enabled': config.API_CALLS_ENABLED,
                'deepseek_api_key_set': bool(config.DEEPSEEK_API_KEY),
                'embeddings_model': config.EMBEDDINGS_MODEL,
                'lazy_load_model': config.LAZY_LOAD_MODEL
            },
            'components': {
                'vector_engine_exists': vector_engine is not None,
                'deepseek_client_exists': deepseek_client is not None
            }
        }
        
        # Test vector engine if it exists
        if vector_engine:
            try:
                vector_ready = vector_engine.is_ready()
                results['vector_engine'] = {
                    'ready': vector_ready,
                    'model_loaded': vector_engine.model is not None,
                    'index_loaded': vector_engine.index is not None,
                    'chunks_count': len(vector_engine.chunks) if hasattr(vector_engine, 'chunks') else 0
                }
                
                # Try to initialize if not ready
                if not vector_ready:
                    logger.info("Attempting to initialize vector engine...")
                    vector_engine.initialize()
                    results['vector_engine']['initialization_success'] = True
                    results['vector_engine']['ready_after_init'] = vector_engine.is_ready()
                
            except Exception as e:
                results['vector_engine'] = {
                    'error': str(e),
                    'error_type': type(e).__name__
                }
        
        # Test DeepSeek client if it exists
        if deepseek_client:
            try:
                deepseek_ready = deepseek_client.is_ready()
                results['deepseek_client'] = {
                    'ready': deepseek_ready,
                    'api_key_set': bool(deepseek_client.api_key)
                }
            except Exception as e:
                results['deepseek_client'] = {
                    'error': str(e),
                    'error_type': type(e).__name__
                }
        
        return jsonify(results), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/search', methods=['POST'])
def search_knowledge_base():
    """Direct search endpoint for testing knowledge base retrieval"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query'].strip()
        top_k = data.get('top_k', 5)
        
        # Check if API calls are enabled
        if not config.API_CALLS_ENABLED:
            return jsonify({
                'query': query,
                'results': [],
                'count': 0,
                'message': 'API calls are currently disabled. Search functionality is not available.',
                'timestamp': datetime.now().isoformat()
            }), 200
        
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
    start_time = time.time()
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.headers.get('User-Agent', 'unknown')
    
    logger.info(f"📱 [PHONE VALIDATION] Request from {client_ip} - User-Agent: {user_agent}")
    
    try:
        data = request.get_json()
        logger.info(f"📦 [PHONE VALIDATION] Request data: {data}")
        
        if not data or 'phone' not in data:
            logger.warning("❌ [PHONE VALIDATION] Missing phone number in request")
            return jsonify({'error': 'Phone number is required'}), 400
        
        phone = data['phone'].strip()
        if not phone:
            logger.warning("❌ [PHONE VALIDATION] Empty phone number provided")
            return jsonify({'error': 'Phone number cannot be empty'}), 400
        
        logger.info(f"📞 [PHONE VALIDATION] Validating phone: {phone}")
        
        # Normalize the phone number
        normalized_phone = _normalize_phone_number(phone)
        logger.info(f"🔧 [PHONE VALIDATION] Normalized phone: {normalized_phone}")
        
        # Check if the normalized phone number is in the approved list
        approved_phones = [_normalize_phone_number(p) for p in config.APPROVED_PHONE_NUMBERS]
        logger.info(f"📋 [PHONE VALIDATION] Approved phones list: {approved_phones}")
        
        is_approved = normalized_phone in approved_phones
        logger.info(f"✅ [PHONE VALIDATION] Phone {phone} (normalized: {normalized_phone}) - {'APPROVED' if is_approved else 'REJECTED'}")
        
        response_data = {
            'phone': phone,
            'normalized_phone': normalized_phone,
            'is_approved': is_approved,
            'success': is_approved,  # Add success field for frontend compatibility
            'timestamp': datetime.now().isoformat()
        }
        
        response_time = (time.time() - start_time) * 1000
        logger.info(f"⏱️ [PHONE VALIDATION] Completed in {response_time:.2f}ms")
        
        return jsonify(response_data)
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"💥 [PHONE VALIDATION] Failed after {response_time:.2f}ms: {str(e)}")
        return jsonify({'error': 'Phone validation failed'}), 500

@app.route('/auth/register', methods=['POST'])
def register_user():
    """Register a new user with email and password"""
    start_time = time.time()
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.headers.get('User-Agent', 'unknown')
    
    logger.info(f"📧 [USER REGISTRATION] Request from {client_ip} - User-Agent: {user_agent}")
    
    try:
        data = request.get_json()
        logger.info(f"📦 [USER REGISTRATION] Request data: {data}")
        
        if not data:
            logger.warning("❌ [USER REGISTRATION] Missing request body")
            return jsonify({'error': 'Request body is required'}), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        logger.info(f"📧 [USER REGISTRATION] Attempting registration for email: {email}")
        
        if not email or not password:
            logger.warning(f"❌ [USER REGISTRATION] Missing required fields - Email: {'✅' if email else '❌'}, Password: {'✅' if password else '❌'}")
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Register user using JSONBin client
        logger.info(f"💾 [USER REGISTRATION] Calling JSONBin client to register user: {email}")
        success, result = jsonbin_client.register_user(email, password)
        
        if success:
            logger.info(f"✅ [USER REGISTRATION] User registered successfully: {email}")
            response_data = {
                'success': True,
                'message': result['message'],
                'email': result.get('email', result.get('username')),  # Handle both old and new response formats
                'created_at': result['created_at'],
                'timestamp': datetime.now().isoformat()
            }
            
            response_time = (time.time() - start_time) * 1000
            logger.info(f"⏱️ [USER REGISTRATION] Completed in {response_time:.2f}ms")
            
            return jsonify(response_data), 201
        else:
            # Handle different error types
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Registration failed')
            
            logger.warning(f"❌ [USER REGISTRATION] Registration failed for {email}: {error_message} (Error type: {error_type})")
            
            if error_type == 'user_exists':
                status_code = 409  # Conflict
                logger.info(f"👤 [USER REGISTRATION] User already exists: {email}")
            elif error_type == 'validation_error':
                status_code = 400  # Bad Request
                logger.warning(f"⚠️ [USER REGISTRATION] Validation error for {email}: {error_message}")
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503  # Service Unavailable
                error_message = 'Authentication service temporarily unavailable'
                logger.error(f"🚨 [USER REGISTRATION] Service unavailable error for {email}: {error_type}")
            else:
                status_code = 500  # Internal Server Error
                logger.error(f"💥 [USER REGISTRATION] Unknown error for {email}: {error_type}")
            
            response_data = {
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }
            
            response_time = (time.time() - start_time) * 1000
            logger.info(f"⏱️ [USER REGISTRATION] Failed after {response_time:.2f}ms")
            
            return jsonify(response_data), status_code
            
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"💥 [USER REGISTRATION] Exception after {response_time:.2f}ms: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'registration_error',
            'message': 'Registration failed due to server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/auth/login', methods=['POST'])
def login_user():
    """Authenticate user login with email and password and return JWT token"""
    start_time = time.time()
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
    user_agent = request.headers.get('User-Agent', 'unknown')
    
    logger.info(f"🔐 [USER LOGIN] Request from {client_ip} - User-Agent: {user_agent}")
    
    try:
        data = request.get_json()
        logger.info(f"📦 [USER LOGIN] Request data: {data}")
        
        if not data:
            logger.warning("❌ [USER LOGIN] Missing request body")
            return jsonify({'error': 'Request body is required'}), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        logger.info(f"🔐 [USER LOGIN] Attempting login for email: {email}")
        
        if not email or not password:
            logger.warning(f"❌ [USER LOGIN] Missing required fields - Email: {'✅' if email else '❌'}, Password: {'✅' if password else '❌'}")
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Authenticate user using JSONBin client
        logger.info(f"💾 [USER LOGIN] Calling JSONBin client to authenticate user: {email}")
        success, result = jsonbin_client.login_user(email, password)
        
        if success:
            logger.info(f"✅ [USER LOGIN] User authenticated successfully: {email}")
            
            # Generate JWT token
            logger.info(f"🔑 [USER LOGIN] Generating JWT token for user: {email}")
            token = generate_jwt_token(result)
            
            response_data = {
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
            }
            
            response_time = (time.time() - start_time) * 1000
            logger.info(f"⏱️ [USER LOGIN] Login completed in {response_time:.2f}ms for: {email}")
            
            return jsonify(response_data), 200
        else:
            # Handle different error types
            error_type = result.get('error', 'unknown_error')
            error_message = result.get('message', 'Login failed')
            
            logger.warning(f"❌ [USER LOGIN] Authentication failed for {email}: {error_message} (Error type: {error_type})")
            
            if error_type in ['user_not_found', 'invalid_password']:
                status_code = 401  # Unauthorized
                logger.info(f"🔒 [USER LOGIN] Unauthorized access attempt for: {email}")
            elif error_type == 'account_disabled':
                status_code = 403  # Forbidden
                logger.warning(f"🚫 [USER LOGIN] Disabled account login attempt: {email}")
            elif error_type == 'validation_error':
                status_code = 400  # Bad Request
                logger.warning(f"⚠️ [USER LOGIN] Validation error for {email}: {error_message}")
            elif error_type in ['api_auth_failed', 'bin_not_found', 'rate_limit', 'timeout', 'connection_error']:
                status_code = 503  # Service Unavailable
                error_message = 'Authentication service temporarily unavailable'
                logger.error(f"🚨 [USER LOGIN] Service unavailable error for {email}: {error_type}")
            else:
                status_code = 500  # Internal Server Error
                logger.error(f"💥 [USER LOGIN] Unknown error for {email}: {error_type}")
            
            response_data = {
                'success': False,
                'error': error_type,
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            }
            
            response_time = (time.time() - start_time) * 1000
            logger.info(f"⏱️ [USER LOGIN] Failed after {response_time:.2f}ms")
            
            return jsonify(response_data), status_code
            
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"💥 [USER LOGIN] Exception after {response_time:.2f}ms: {str(e)}")
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

@app.route('/chat/stream', methods=['POST'])
@require_auth
def chat_stream():
    """Streaming chat endpoint for real-time responses - requires authentication"""
    try:
        # Debug: Log authentication info
        logger.info(f"Streaming chat endpoint called by user: {request.user.get('email', 'unknown')}")
        
        # Parse request data
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Check if API calls are enabled
        if not config.API_CALLS_ENABLED:
            def generate_placeholder():
                yield f"data: {json.dumps({'content': 'API calls are currently disabled. This is a placeholder response.', 'done': True})}\n\n"
            return Response(generate_placeholder(), mimetype='text/event-stream')
        
        # Check if AI components are available
        if vector_engine is None or deepseek_client is None:
            def generate_error():
                yield f"data: {json.dumps({'content': 'AI components are not available. Please check the backend configuration.', 'done': True})}\n\n"
            return Response(generate_error(), mimetype='text/event-stream')
        
        # Check if DeepSeek API key is configured
        if not config.DEEPSEEK_API_KEY:
            def generate_error():
                yield f"data: {json.dumps({'content': 'DeepSeek API key is not configured. Please set the DEEPSEEK_API_KEY environment variable.', 'done': True})}\n\n"
            return Response(generate_error(), mimetype='text/event-stream')
        
        # Initialize vector engine if using lazy loading
        if not vector_engine.is_ready():
            logger.info("Initializing vector engine (lazy loading)...")
            try:
                vector_engine.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize vector engine: {str(e)}")
                def generate_error():
                    yield f"data: {json.dumps({'content': f'Failed to initialize AI components: {str(e)}', 'done': True})}\n\n"
                return Response(generate_error(), mimetype='text/event-stream')
        
        # Retrieve relevant context from knowledge base
        try:
            relevant_passages = vector_engine.search(user_message, top_k=7)
        except Exception as e:
            logger.error(f"Failed to search knowledge base: {str(e)}")
            def generate_error():
                yield f"data: {json.dumps({'content': f'Failed to search knowledge base: {str(e)}', 'done': True})}\n\n"
            return Response(generate_error(), mimetype='text/event-stream')
        
        def generate_stream():
            try:
                # Generate streaming response using DeepSeek API
                full_response = ""
                for chunk in deepseek_client.generate_response_stream(
                    user_message=user_message,
                    context_passages=relevant_passages
                ):
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                
                # Add context information if available
                if relevant_passages:
                    context_info = f"\n\n<div style=\"font-size: 0.8em; color: rgba(100,100,100,0.7); margin-top: 8px; font-style: italic;\">📚 Based on {len(relevant_passages)} relevant sources from our knowledge base</div>"
                    yield f"data: {json.dumps({'content': context_info, 'done': False})}\n\n"
                
                # Send completion signal
                yield f"data: {json.dumps({'content': '', 'done': True, 'context_sources': len(relevant_passages)})}\n\n"
                
                # Log the interaction with user info
                user_email = request.user.get('email', 'unknown')
                logger.info(f"Generated streaming response for user {user_email}: {user_message[:50]}... (Context passages: {len(relevant_passages)})")
                
            except Exception as e:
                logger.error(f"Error in streaming response: {str(e)}")
                yield f"data: {json.dumps({'content': f'Error generating response: {str(e)}', 'done': True})}\n\n"
        
        return Response(generate_stream(), mimetype='text/event-stream')
        
    except Exception as e:
        logger.error(f"Error in streaming chat endpoint: {str(e)}")
        def generate_error():
            yield f"data: {json.dumps({'content': f'Failed to process message: {str(e)}', 'done': True})}\n\n"
        return Response(generate_error(), mimetype='text/event-stream')

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
        # Test connections
        logger.info("Testing component connections...")
        
        if config.API_CALLS_ENABLED:
            # Initialize the vector engine (load embeddings)
            logger.info("Initializing vector search engine...")
            vector_engine.initialize()
            
            if not vector_engine.is_ready():
                raise Exception("Vector engine not ready")
            if not deepseek_client.is_ready():
                raise Exception("DeepSeek client not ready")
        else:
            logger.info("Skipping AI/ML component initialization - API calls disabled")

        if not jsonbin_client.is_ready():
            raise Exception("JSONBin client not ready - check JSONBin configuration")
        
        logger.info("All components ready. Starting Flask server...")
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        exit(1)
