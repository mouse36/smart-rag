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
        
        # Test connection on initialization only if API calls are enabled
        if config.API_CALLS_ENABLED:
            self._test_connection()
        else:
            self._ready = True  # Mark as ready for placeholder mode
            logger.info("DeepSeek client initialized in placeholder mode (API calls disabled)")
    
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
        if not self.config.API_CALLS_ENABLED:
            return self._ready  # Just check if ready flag is set for placeholder mode
        return self._ready and bool(self.api_key)
    
    def generate_response(self, user_message: str, context_passages: List[Dict[str, Any]]) -> str:
        """Generate a response using DeepSeek API with context or return placeholder"""
        if not self.is_ready():
            raise RuntimeError("DeepSeek client not ready")
        
        # If API calls are disabled, return placeholder response
        if not self.config.API_CALLS_ENABLED:
            return self._get_placeholder_response(user_message, context_passages)
        
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
    
    def _get_placeholder_response(self, user_message: str, context_passages: List[Dict[str, Any]]) -> str:
        """Get a placeholder response when API calls are disabled"""
        # Create a response that mentions some context if available
        context_info = ""
        if context_passages:
            sources = [passage.get('source_file', 'Unknown') for passage in context_passages[:3]]
            context_info = f"\n\n*Based on information from: {', '.join(set(sources))}*"
        
        placeholder_responses = [
            f"Thank you for your question: '{user_message}'\n\nThis is a placeholder response for demonstration purposes. In the real system, I would provide detailed, evidence-based guidance about selective mutism based on our comprehensive knowledge base.{context_info}",
            
            f"I understand you're asking about: '{user_message}'\n\nThis is a sample response. When API calls are enabled, I would analyze your question against our extensive selective mutism resources and provide specific, helpful guidance tailored to your situation.{context_info}",
            
            f"Your question: '{user_message}'\n\nPlaceholder response: In normal operation, I would draw from our knowledge base containing expert guidance on selective mutism to provide you with accurate, practical advice. This demo mode shows the system is working correctly.{context_info}"
        ]
        
        # Use a simple hash to consistently return the same response for the same question
        import hashlib
        response_index = int(hashlib.md5(user_message.encode()).hexdigest(), 16) % len(placeholder_responses)
        
        logger.info(f"Returned placeholder response for: {user_message[:50]}...")
        return placeholder_responses[response_index]
    
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
            'api_calls_enabled': self.config.API_CALLS_ENABLED,
            'mode': 'live_api' if self.config.API_CALLS_ENABLED else 'placeholder',
            'model': self.model,
            'base_url': self.base_url,
            'max_response_length': self.config.MAX_RESPONSE_LENGTH,
            'temperature': self.config.TEMPERATURE,
            'top_p': self.config.TOP_P
        }
