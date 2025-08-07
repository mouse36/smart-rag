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
        self.HOST = os.getenv('HOST', '127.0.0.1')
        self.PORT = int(os.getenv('PORT', 5000))
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # DeepSeek API settings
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
        self.DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        self.DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        
        # Vector search settings
        self.EMBEDDINGS_MODEL = os.getenv('EMBEDDINGS_MODEL', 'all-MiniLM-L6-v2')
        self.VECTOR_DIMENSION = int(os.getenv('VECTOR_DIMENSION', 384))  # for all-MiniLM-L6-v2
        self.CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 500))
        self.CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 50))
        
        # Cache settings (Redis)
        self.REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        self.REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
        self.REDIS_DB = int(os.getenv('REDIS_DB', 0))
        self.REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
        self.CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))  # 1 hour default
        
        # Knowledge base settings
        self.KNOWLEDGE_BASE_PATH = os.getenv(
            'KNOWLEDGE_BASE_PATH', 
            os.path.join(os.path.dirname(__file__), 'knowledge_base')
        )
        self.EMBEDDINGS_CACHE_PATH = os.getenv(
            'EMBEDDINGS_CACHE_PATH',
            os.path.join(os.path.dirname(__file__), 'data', 'embeddings.pkl')
        )
        self.INDEX_CACHE_PATH = os.getenv(
            'INDEX_CACHE_PATH',
            os.path.join(os.path.dirname(__file__), 'data', 'faiss_index.bin')
        )
        
        # Response generation settings
        self.MAX_CONTEXT_LENGTH = int(os.getenv('MAX_CONTEXT_LENGTH', 4000))
        self.MAX_RESPONSE_LENGTH = int(os.getenv('MAX_RESPONSE_LENGTH', 1000))
        self.TEMPERATURE = float(os.getenv('TEMPERATURE', 0.7))
        self.TOP_P = float(os.getenv('TOP_P', 0.9))
        
        # Create data directory if it doesn't exist
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
    
    def validate(self) -> Optional[str]:
        """Validate configuration and return error message if invalid"""
        if not self.DEEPSEEK_API_KEY:
            return "DEEPSEEK_API_KEY environment variable is required"
        
        if not os.path.exists(self.KNOWLEDGE_BASE_PATH):
            return f"Knowledge base path does not exist: {self.KNOWLEDGE_BASE_PATH}"
        
        return None  # Configuration is valid
    
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
            REDIS_HOST={self.REDIS_HOST}
            REDIS_PORT={self.REDIS_PORT}
            KNOWLEDGE_BASE_PATH={self.KNOWLEDGE_BASE_PATH}
        )"""
