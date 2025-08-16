"""
Smart RAG Backend - Virtual Assistant powered by DeepSeek API
Features:
- Vector similarity search for knowledge base retrieval
- DeepSeek API integration for intelligent responses
- Redis caching for improved performance
- RESTful API endpoints for frontend integration
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import time
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime
import stripe

# Import custom modules
from vector_search import VectorSearchEngine
from deepseek_client import DeepSeekClient
from cache_manager import CacheManager
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
cache_manager = CacheManager(config)
jsonbin_client = JSONBinClient(config)

# Initialize Stripe
if config.STRIPE_SECRET_KEY:
    stripe.api_key = config.STRIPE_SECRET_KEY

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
                'cache_manager': cache_manager.is_ready(),
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
def chat():
    """Main chat endpoint for processing user messages"""
    try:
        # Parse request data
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Check cache first
        cache_key = _generate_cache_key(user_message)
        cached_response = cache_manager.get(cache_key)
        if cached_response:
            logger.info(f"Cache hit for message: {user_message[:50]}...")
            return jsonify({
                'response': cached_response,
                'cached': True,
                'timestamp': datetime.now().isoformat()
            })
        
        # Retrieve relevant context from knowledge base
        relevant_passages = vector_engine.search(user_message, top_k=7)
        
        # Generate response using DeepSeek API
        response = deepseek_client.generate_response(
            user_message=user_message,
            context_passages=relevant_passages
        )
        
        # Cache the response
        cache_manager.set(cache_key, response, ttl=3600)  # Cache for 1 hour
        
        # Log the interaction
        logger.info(f"Generated response for: {user_message[:50]}... (Context passages: {len(relevant_passages)})")
        
        return jsonify({
            'response': response,
            'cached': False,
            'context_passages_count': len(relevant_passages),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': 'Internal server error occurred',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    try:
        stats = cache_manager.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({'error': 'Failed to retrieve cache stats'}), 500

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the cache (admin endpoint)"""
    try:
        cache_manager.clear()
        logger.info("Cache cleared successfully")
        return jsonify({
            'message': 'Cache cleared successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({'error': 'Failed to clear cache'}), 500

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
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in phone validation endpoint: {str(e)}")
        return jsonify({'error': 'Phone validation failed'}), 500

@app.route('/auth/register', methods=['POST'])
def register_user():
    """Register a new user with username and password"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Register user using JSONBin client
        success, result = jsonbin_client.register_user(username, password)
        
        if success:
            logger.info(f"User registered successfully: {username}")
            return jsonify({
                'success': True,
                'message': result['message'],
                'username': result['username'],
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
            
            logger.warning(f"User registration failed for {username}: {error_message}")
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
    """Authenticate user login with username and password"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Authenticate user using JSONBin client
        success, result = jsonbin_client.login_user(username, password)
        
        if success:
            logger.info(f"User logged in successfully: {username}")
            return jsonify({
                'success': True,
                'message': result['message'],
                'username': result['username'],
                'last_login': result['last_login'],
                'created_at': result.get('created_at'),
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
            
            logger.warning(f"User login failed for {username}: {error_message}")
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

@app.route('/auth/user/<username>', methods=['GET'])
def get_user_info(username):
    """Get user information (admin endpoint)"""
    try:
        # Basic validation
        if not username or not username.strip():
            return jsonify({'error': 'Username is required'}), 400
        
        # Get user info using JSONBin client
        success, result = jsonbin_client.get_user_info(username.strip())
        
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
        
        username = data.get('username', '').strip()
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not username or not old_password or not new_password:
            return jsonify({'error': 'Username, old password, and new password are required'}), 400
        
        # Change password using JSONBin client
        success, result = jsonbin_client.change_password(username, old_password, new_password)
        
        if success:
            logger.info(f"Password changed successfully for user: {username}")
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
            
            logger.warning(f"Password change failed for {username}: {error_message}")
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

def _generate_cache_key(message: str) -> str:
    """Generate a cache key for a message"""
    return hashlib.md5(message.lower().strip().encode()).hexdigest()

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

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
        if not cache_manager.is_ready():
            raise Exception("Cache manager not ready")
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
