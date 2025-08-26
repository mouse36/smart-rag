"""
Configuration settings for the Smart RAG Backend
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the application"""
    
    def __init__(self):
        # Flask settings
        self.HOST = os.getenv('HOST', '0.0.0.0')  # Changed default to 0.0.0.0 for deployment
        self.PORT = int(os.getenv('PORT', 5000))
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # API Control
        self.API_CALLS_ENABLED = os.getenv('API_CALLS_ENABLED', 'True').lower() == 'true'
        
        # DeepSeek API settings
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
        self.DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        self.DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'DeepSeek-V3.1')
        
        # Vector search settings
        self.EMBEDDINGS_MODEL = os.getenv('EMBEDDINGS_MODEL', 'all-MiniLM-L6-v2')
        self.VECTOR_DIMENSION = int(os.getenv('VECTOR_DIMENSION', 384))  # for all-MiniLM-L6-v2
        self.CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 500))
        self.CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 50))
        
        # Lightweight vector search settings (for memory-constrained environments)
        self.LIGHTWEIGHT_EMBEDDINGS_MODEL = os.getenv('LIGHTWEIGHT_EMBEDDINGS_MODEL', 'all-MiniLM-L6-v2')
        self.LIGHTWEIGHT_VECTOR_DIMENSION = int(os.getenv('LIGHTWEIGHT_VECTOR_DIMENSION', 384))
        self.USE_LIGHTWEIGHT_SEARCH = os.getenv('USE_LIGHTWEIGHT_SEARCH', 'True').lower() == 'true'
        self.LAZY_LOAD_MODEL = os.getenv('LAZY_LOAD_MODEL', 'True').lower() == 'true'
        

        
        # Knowledge base settings
        self.KNOWLEDGE_BASE_PATH = os.getenv(
            'KNOWLEDGE_BASE_PATH', 
            os.path.join(os.path.dirname(__file__), 'knowledge_base')
        )
        self.EMBEDDINGS_CACHE_PATH = os.getenv(
            'EMBEDDINGS_CACHE_PATH',
            os.path.join(os.path.dirname(__file__), 'cache', 'embeddings.pkl')
        )
        self.INDEX_CACHE_PATH = os.getenv(
            'INDEX_CACHE_PATH',
            os.path.join(os.path.dirname(__file__), 'cache', 'sklearn_index.pkl')
        )
        
        # Response generation settings
        self.MAX_CONTEXT_LENGTH = int(os.getenv('MAX_CONTEXT_LENGTH', 4000))
        self.MAX_RESPONSE_LENGTH = int(os.getenv('MAX_RESPONSE_LENGTH', 1000))
        self.TEMPERATURE = float(os.getenv('TEMPERATURE', 0.7))
        self.TOP_P = float(os.getenv('TOP_P', 0.9))
        
        # Phone authentication settings (legacy)
        self.APPROVED_PHONE_NUMBERS = self._parse_phone_numbers(os.getenv('APPROVED_PHONE_NUMBERS', ''))
        
        # JSONBin API settings
        self.JSONBIN_API_KEY = os.getenv('JSONBIN_API_KEY')
        self.JSONBIN_BASE_URL = os.getenv('JSONBIN_BASE_URL', 'https://api.jsonbin.io/v3/b')
        self.JSONBIN_BIN_ID = os.getenv('JSONBIN_BIN_ID')
        
        # Stripe payment settings
        self.STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
        self.STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
        self.STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
        self.STRIPE_CURRENCY = os.getenv('STRIPE_CURRENCY', 'usd')
        
        # Use environment variables for donation URLs, with fallback to relative paths
        base_url = os.getenv('BASE_URL', '')
        if base_url:
            self.DONATION_SUCCESS_URL = os.getenv('DONATION_SUCCESS_URL', f'{base_url}/static/donation-success.html')
            self.DONATION_CANCEL_URL = os.getenv('DONATION_CANCEL_URL', f'{base_url}/static/donation-cancel.html')
        else:
            # Fallback to relative paths for production
            self.DONATION_SUCCESS_URL = os.getenv('DONATION_SUCCESS_URL', '/static/donation-success.html')
            self.DONATION_CANCEL_URL = os.getenv('DONATION_CANCEL_URL', '/static/donation-cancel.html')
        
        # Create cache directory if it doesn't exist
        self._ensure_cache_directory()
    
    def _ensure_cache_directory(self):
        """Ensure the cache directory exists"""
        cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
        os.makedirs(cache_dir, exist_ok=True)
    
    def _parse_phone_numbers(self, phone_numbers_str: str) -> list:
        """Parse comma-separated phone numbers from environment variable"""
        if not phone_numbers_str:
            return []
        return [phone.strip() for phone in phone_numbers_str.split(',') if phone.strip()]
    
    def validate(self) -> Optional[str]:
        """Validate configuration and return error message if invalid"""
        if self.API_CALLS_ENABLED and not self.DEEPSEEK_API_KEY:
            return "DEEPSEEK_API_KEY environment variable is required when API calls are enabled"
        
        if not self.JSONBIN_API_KEY:
            return "JSONBIN_API_KEY environment variable is required for user authentication"
        
        return None
    
    def is_stripe_configured(self) -> bool:
        """Check if Stripe is properly configured"""
        return bool(self.STRIPE_SECRET_KEY and self.STRIPE_PUBLISHABLE_KEY)
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the AI assistant"""
        return """You are a helpful virtual assistant specializing in selective mutism (SM). 
You have access to comprehensive knowledge about selective mutism, including treatment approaches, 
parent guidance, educational strategies, and clinical insights.

Your role is to:
1. Provide accurate, evidence-based information about selective mutism
2. Offer practical guidance for parents, teachers, and caregivers
3. Explain treatment approaches and interventions
4. Address common concerns and misconceptions
5. Be empathetic and supportive in your responses

Always base your responses on the provided context from the knowledge base. If you don't have 
enough information to answer a question fully, say so and suggest consulting with a qualified 
professional. Never provide medical diagnoses or replace professional clinical assessment.

Be warm, understanding, and professional in your tone. Remember that families dealing with 
selective mutism often feel frustrated and need support."""

    def __str__(self) -> str:
        """String representation of config (without sensitive data)"""
        return f"""Config(
            HOST={self.HOST}
            PORT={self.PORT}
            DEBUG={self.DEBUG}
            DEEPSEEK_MODEL={self.DEEPSEEK_MODEL}
            EMBEDDINGS_MODEL={self.EMBEDDINGS_MODEL}
            VECTOR_DIMENSION={self.VECTOR_DIMENSION}
            CHUNK_SIZE={self.CHUNK_SIZE}

            KNOWLEDGE_BASE_PATH={self.KNOWLEDGE_BASE_PATH}
        )"""
