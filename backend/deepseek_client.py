"""
DeepSeek API Client for Chat Completions
Handles communication with DeepSeek API for generating responses
"""

import logging
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """Client for interacting with DeepSeek API"""
    
    def __init__(self, config):
        self.config = config
        self.base_url = config.DEEPSEEK_BASE_URL
        self.api_key = config.DEEPSEEK_API_KEY
        self.model = config.DEEPSEEK_MODEL
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self._ready = False
        
        # Test connection on initialization
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to DeepSeek API"""
        try:
            # Make a simple test request
            test_response = self._make_request(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            self._ready = True
            logger.info("DeepSeek API connection successful")
            
        except Exception as e:
            logger.error(f"DeepSeek API connection failed: {str(e)}")
            self._ready = False
    
    def is_ready(self) -> bool:
        """Check if the DeepSeek client is ready"""
        return self._ready and bool(self.api_key)
    
    def generate_response(self, user_message: str, context_passages: List[Dict[str, Any]]) -> str:
        """Generate a response using DeepSeek API with context"""
        if not self.is_ready():
            raise RuntimeError("DeepSeek client not ready")
        
        try:
            # Prepare the context
            context = self._prepare_context(context_passages)
            
            # Create the messages for the API
            messages = [
                {
                    "role": "system",
                    "content": self.config.get_system_prompt()
                },
                {
                    "role": "user", 
                    "content": self._format_user_message(user_message, context)
                }
            ]
            
            # Make the API request
            response_data = self._make_request(messages)
            
            # Extract the response text
            response_text = response_data['choices'][0]['message']['content']
            
            logger.info(f"Generated response for user message: {user_message[:50]}...")
            return response_text.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._get_fallback_response()
    
    def _prepare_context(self, passages: List[Dict[str, Any]]) -> str:
        """Prepare context from relevant passages"""
        if not passages:
            return "No specific context available."
        
        context_parts = []
        total_length = 0
        
        for i, passage in enumerate(passages):
            passage_text = passage['text']
            source = passage['source_file']
            
            # Add source information
            context_part = f"[Source: {source}]\n{passage_text}\n"
            
            # Check if adding this passage would exceed max context length
            if total_length + len(context_part) > self.config.MAX_CONTEXT_LENGTH:
                break
            
            context_parts.append(context_part)
            total_length += len(context_part)
        
        context = "\n---\n".join(context_parts)
        logger.debug(f"Prepared context with {len(context_parts)} passages ({total_length} characters)")
        
        return context
    
    def _format_user_message(self, user_message: str, context: str) -> str:
        """Format the user message with context for the API"""
        formatted_message = f"""Based on the following context from our knowledge base about selective mutism, please answer the user's question:

CONTEXT:
{context}

USER QUESTION:
{user_message}

Please provide a helpful, accurate response based on the context provided. If the context doesn't contain enough information to fully answer the question, acknowledge this and provide what information you can, while suggesting they consult with a qualified professional for more specific guidance."""
        
        return formatted_message
    
    def _make_request(self, messages: List[Dict[str, str]], max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Make a request to the DeepSeek API"""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.MAX_RESPONSE_LENGTH,
            "temperature": self.config.TEMPERATURE,
            "top_p": self.config.TOP_P,
            "stream": False
        }
        
        try:
            response = requests.post(
                url, 
                headers=self.headers, 
                json=payload,
                timeout=30  # 30 second timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            raise
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {str(e)}")
            raise
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when API fails"""
        return """I apologize, but I'm experiencing technical difficulties at the moment. 
Here are some general suggestions for selective mutism:

1. **Be patient and understanding** - Children with selective mutism need time and support
2. **Avoid pressure** - Don't force speech or put the child in uncomfortable situations
3. **Consult professionals** - Work with psychologists or speech therapists experienced with SM
4. **Create comfortable environments** - Reduce anxiety triggers when possible
5. **Use gradual exposure** - Slowly introduce speaking situations in a supportive way

For specific guidance tailored to your situation, please consult with a qualified professional who specializes in selective mutism."""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            'ready': self.is_ready(),
            'model': self.model,
            'base_url': self.base_url,
            'max_response_length': self.config.MAX_RESPONSE_LENGTH,
            'temperature': self.config.TEMPERATURE,
            'top_p': self.config.TOP_P
        }
