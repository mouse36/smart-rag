"""
DeepSeek API Client for Chat Completions
Handles communication with DeepSeek API for generating responses
"""

import logging
import requests
import json
import os
import re
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
            logger.warning("DeepSeek client not ready, returning placeholder response")
            return self._get_placeholder_response(user_message, context_passages)
        
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
            
            # Make the API request with retries
            response_data = self._make_request(messages)
            
            # Extract the response text
            response_text = response_data['choices'][0]['message']['content']
            
            logger.info(f"Generated response for user message: {user_message[:50]}...")
            return response_text.strip()
            
        except requests.exceptions.Timeout as e:
            logger.error(f"API request timed out after retries: {str(e)}")
            logger.info("Falling back to enhanced fallback response due to timeout")
            return self._get_enhanced_fallback_response(user_message, context_passages, "connection timeout")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed after retries: {str(e)}")
            logger.info("Falling back to enhanced fallback response due to request error")
            return self._get_enhanced_fallback_response(user_message, context_passages, "API request failed")
            
        except Exception as e:
            logger.error(f"Unexpected error generating response: {str(e)}")
            return self._get_enhanced_fallback_response(user_message, context_passages, "unexpected error")
    
    def generate_response_stream(self, user_message: str, context_passages: List[Dict[str, Any]]):
        """Generate a streaming response using DeepSeek API with context"""
        if not self.is_ready():
            logger.warning("DeepSeek client not ready, returning placeholder response")
            yield self._get_placeholder_response(user_message, context_passages)
            return
        
        # If API calls are disabled, return placeholder response
        if not self.config.API_CALLS_ENABLED:
            yield self._get_placeholder_response(user_message, context_passages)
            return
        
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
            
            # Make the streaming API request
            for chunk in self._make_streaming_request(messages):
                yield chunk
                
        except Exception as e:
            logger.error(f"Unexpected error generating streaming response: {str(e)}")
            yield self._get_enhanced_fallback_response(user_message, context_passages, "unexpected error")

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
    
    def _detect_is_mainly_chinese(self, text: str) -> bool:
        """Detect if the text is mainly in Chinese"""
        if not text:
            return False
        
        # Count Chinese characters (CJK Unified Ideographs, CJK Extension A, etc.)
        chinese_pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')
        chinese_chars = len(chinese_pattern.findall(text))
        
        # Count English/Latin characters
        english_pattern = re.compile(r'[a-zA-Z]')
        english_chars = len(english_pattern.findall(text))
        
        # Count total meaningful characters (Chinese + English + numbers)
        meaningful_chars = chinese_chars + english_chars + len(re.findall(r'[0-9]', text))
        
        if meaningful_chars == 0:
            return False
        
        # Consider text mainly Chinese if Chinese characters make up more than 50% of meaningful characters
        chinese_ratio = chinese_chars / meaningful_chars
        return chinese_ratio > 0.5
    
    def _load_tone_context(self, user_message: str) -> str:
        """Load appropriate tone context file based on user message language"""
        try:
            is_mainly_chinese = self._detect_is_mainly_chinese(user_message)
            
            # Determine the path to the tone context file
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            if is_mainly_chinese:
                tone_file_path = os.path.join(backend_dir, 'tone-context-zh.txt')
            else:
                tone_file_path = os.path.join(backend_dir, 'tone-context-en.txt')
            
            # Read the tone context file
            if os.path.exists(tone_file_path):
                with open(tone_file_path, 'r', encoding='utf-8') as f:
                    tone_context = f.read().strip()
                logger.debug(f"Loaded tone context from {tone_file_path} for {'Chinese' if is_mainly_chinese else 'English'} message")
                return tone_context
            else:
                logger.warning(f"Tone context file not found: {tone_file_path}")
                return ""
        except Exception as e:
            logger.error(f"Error loading tone context: {str(e)}")
            return ""
    
    def _format_user_message(self, user_message: str, context: str) -> str:
        """Format the user message with context for the API"""
        # Load appropriate tone context
        tone_context = self._load_tone_context(user_message)
        
        # Prepend tone context to the original user message
        if tone_context:
            modified_user_message = f"{tone_context}\n\n{user_message}"
        else:
            modified_user_message = user_message
        
        formatted_message = f"""Based on the following context from our knowledge base about selective mutism, please answer the user's question:

CONTEXT:
{context}

USER QUESTION:
{modified_user_message}

Please provide a helpful, accurate response based on the context provided. If the context doesn't contain enough information to fully answer the question, acknowledge this and provide what information you can, while suggesting they consult with a qualified professional for more specific guidance."""
        
        return formatted_message
    
    def _make_request(self, messages: List[Dict[str, str]], max_tokens: Optional[int] = None, retries: int = 3) -> Dict[str, Any]:
        """Make a request to the DeepSeek API with retry logic"""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.MAX_RESPONSE_LENGTH,
            "temperature": self.config.TEMPERATURE,
            "top_p": self.config.TOP_P,
            "stream": False
        }
        
        last_exception = None
        
        for attempt in range(retries):
            try:
                # Increase timeout progressively with each retry
                timeout = 30 + (attempt * 15)  # 30s, 45s, 60s
                
                logger.info(f"Making API request (attempt {attempt + 1}/{retries}) with {timeout}s timeout")
                
                response = requests.post(
                    url, 
                    headers=self.headers, 
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()
                
                return response.json()
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"Request timeout on attempt {attempt + 1}/{retries}: {str(e)}")
                if attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    continue
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.error(f"HTTP request failed on attempt {attempt + 1}/{retries}: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response text: {e.response.text}")
                    # Don't retry on client errors (4xx)
                    if 400 <= e.response.status_code < 500:
                        raise
                if attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
            except json.JSONDecodeError as e:
                last_exception = e
                logger.error(f"Failed to decode JSON response on attempt {attempt + 1}/{retries}: {str(e)}")
                if attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue
        
        # If we get here, all retries failed
        logger.error(f"All {retries} attempts failed. Last error: {str(last_exception)}")
        raise last_exception

    def _make_streaming_request(self, messages: List[Dict[str, str]], max_tokens: Optional[int] = None, retries: int = 3):
        """Make a streaming request to the DeepSeek API with retry logic"""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.MAX_RESPONSE_LENGTH,
            "temperature": self.config.TEMPERATURE,
            "top_p": self.config.TOP_P,
            "stream": True
        }
        
        last_exception = None
        
        for attempt in range(retries):
            try:
                # Increase timeout progressively with each retry
                timeout = 30 + (attempt * 15)  # 30s, 45s, 60s
                
                logger.info(f"Making streaming API request (attempt {attempt + 1}/{retries}) with {timeout}s timeout")
                
                response = requests.post(
                    url, 
                    headers=self.headers, 
                    json=payload,
                    timeout=timeout,
                    stream=True
                )
                response.raise_for_status()
                
                # Process streaming response
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            if data == '[DONE]':
                                return
                            try:
                                chunk = json.loads(data)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield delta['content']
                            except json.JSONDecodeError:
                                continue
                
                return
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"Streaming request timeout on attempt {attempt + 1}/{retries}: {str(e)}")
                if attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    continue
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.error(f"Streaming HTTP request failed on attempt {attempt + 1}/{retries}: {str(e)}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response text: {e.response.text}")
                    # Don't retry on client errors (4xx)
                    if 400 <= e.response.status_code < 500:
                        raise
                if attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
        
        # If we get here, all retries failed
        logger.error(f"All {retries} streaming attempts failed. Last error: {str(last_exception)}")
        raise last_exception
    
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
    
    def _get_enhanced_fallback_response(self, user_message: str, context_passages: List[Dict[str, Any]], error_type: str) -> str:
        """Get an enhanced fallback response when API fails, including context if available"""
        # Start with an apology and explanation
        response = f"I apologize, but I'm experiencing technical difficulties ({error_type}) at the moment.\n\n"
        
        # If we have context, try to provide some relevant information
        if context_passages:
            response += "However, I found some relevant information in our knowledge base:\n\n"
            
            # Include snippets from the most relevant passages
            for i, passage in enumerate(context_passages[:2]):  # Limit to first 2 passages
                source = passage.get('source_file', 'Unknown source')
                text = passage.get('text', '')
                
                # Extract a relevant snippet (first 200 characters)
                snippet = text[:200].strip()
                if len(text) > 200:
                    snippet += "..."
                
                response += f"**From {source}:**\n{snippet}\n\n"
            
            response += "This information may be helpful, but for the most accurate and personalized guidance, please try again in a few moments or consult with a qualified professional.\n\n"
        else:
            response += "While I couldn't retrieve specific information for your question, here are some general guidelines for selective mutism:\n\n"
        
        # Add general suggestions
        response += """**General Selective Mutism Guidelines:**

1. **Be patient and understanding** - Children with selective mutism need time and support
2. **Avoid pressure** - Don't force speech or put the child in uncomfortable situations  
3. **Consult professionals** - Work with psychologists or speech therapists experienced with SM
4. **Create comfortable environments** - Reduce anxiety triggers when possible
5. **Use gradual exposure** - Slowly introduce speaking situations in a supportive way

Please try your question again in a few moments, or consult with a qualified professional who specializes in selective mutism for personalized guidance."""
        
        return response
    
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
