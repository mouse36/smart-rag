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

# Import custom modules
from vector_search import VectorSearchEngine
from deepseek_client import DeepSeekClient
from cache_manager import CacheManager
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
                'cache_manager': cache_manager.is_ready()
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
        
        logger.info("All components ready. Starting Flask server...")
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        exit(1)
