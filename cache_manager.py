"""
Cache Manager for storing and retrieving cached responses
Uses Redis for persistent caching with fallback to in-memory cache
"""

import logging
import json
import time
from typing import Optional, Dict, Any
import hashlib

logger = logging.getLogger(__name__)

# Try to import Redis, fallback to in-memory cache if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, falling back to in-memory cache")

class CacheManager:
    """Manages caching of responses with Redis or in-memory fallback"""
    
    def __init__(self, config):
        self.config = config
        self.redis_client = None
        self.memory_cache = {}  # Fallback in-memory cache
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0
        }
        self._ready = False
        
        self._initialize_cache()
    
    def _initialize_cache(self):
        """Initialize the cache system"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=self.config.REDIS_HOST,
                    port=self.config.REDIS_PORT,
                    db=self.config.REDIS_DB,
                    password=self.config.REDIS_PASSWORD,
                    decode_responses=True,
                    socket_timeout=5
                )
                
                # Test Redis connection
                self.redis_client.ping()
                self._ready = True
                logger.info("Redis cache initialized successfully")
                
            except Exception as e:
                logger.warning(f"Redis initialization failed: {str(e)}. Using in-memory cache.")
                self.redis_client = None
                self._ready = True
        else:
            logger.info("Using in-memory cache (Redis not available)")
            self._ready = True
    
    def is_ready(self) -> bool:
        """Check if cache manager is ready"""
        return self._ready
    
    def get(self, key: str) -> Optional[str]:
        """Get a value from cache"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    self.cache_stats['hits'] += 1
                    logger.debug(f"Cache hit for key: {key[:20]}...")
                    return value
                else:
                    self.cache_stats['misses'] += 1
                    return None
            else:
                # Use in-memory cache
                cache_item = self.memory_cache.get(key)
                if cache_item:
                    # Check if expired
                    if time.time() < cache_item['expires_at']:
                        self.cache_stats['hits'] += 1
                        logger.debug(f"Memory cache hit for key: {key[:20]}...")
                        return cache_item['value']
                    else:
                        # Remove expired item
                        del self.memory_cache[key]
                
                self.cache_stats['misses'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            self.cache_stats['errors'] += 1
            return None
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value in cache"""
        try:
            ttl = ttl or self.config.CACHE_TTL
            
            if self.redis_client:
                result = self.redis_client.setex(key, ttl, value)
                if result:
                    self.cache_stats['sets'] += 1
                    logger.debug(f"Cached value for key: {key[:20]}... (TTL: {ttl}s)")
                return result
            else:
                # Use in-memory cache
                expires_at = time.time() + ttl
                self.memory_cache[key] = {
                    'value': value,
                    'expires_at': expires_at
                }
                self.cache_stats['sets'] += 1
                logger.debug(f"Memory cached value for key: {key[:20]}... (TTL: {ttl}s)")
                
                # Clean up expired items occasionally
                self._cleanup_memory_cache()
                return True
                
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            self.cache_stats['errors'] += 1
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        try:
            if self.redis_client:
                result = self.redis_client.delete(key)
                return result > 0
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error deleting from cache: {str(e)}")
            self.cache_stats['errors'] += 1
            return False
    
    def clear(self) -> bool:
        """Clear all cache"""
        try:
            if self.redis_client:
                self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
            
            logger.info("Cache cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            self.cache_stats['errors'] += 1
            return False
    
    def _cleanup_memory_cache(self):
        """Clean up expired items from memory cache"""
        if len(self.memory_cache) < 100:  # Only cleanup if cache is getting large
            return
        
        current_time = time.time()
        expired_keys = [
            key for key, item in self.memory_cache.items()
            if current_time >= item['expires_at']
        ]
        
        for key in expired_keys:
            del self.memory_cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache items")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.cache_stats.copy()
        
        # Add cache type and status
        stats.update({
            'cache_type': 'redis' if self.redis_client else 'memory',
            'ready': self.is_ready(),
            'memory_cache_size': len(self.memory_cache) if not self.redis_client else None
        })
        
        # Add Redis-specific stats if available
        if self.redis_client:
            try:
                redis_info = self.redis_client.info()
                stats.update({
                    'redis_memory_usage': redis_info.get('used_memory_human'),
                    'redis_connected_clients': redis_info.get('connected_clients'),
                    'redis_total_commands_processed': redis_info.get('total_commands_processed')
                })
            except Exception as e:
                logger.warning(f"Could not get Redis stats: {str(e)}")
        
        return stats
    
    def generate_key(self, *args) -> str:
        """Generate a cache key from arguments"""
        # Create a hash from all arguments
        key_string = '|'.join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the cache system"""
        health = {
            'status': 'healthy',
            'cache_type': 'redis' if self.redis_client else 'memory',
            'ready': self.is_ready()
        }
        
        try:
            # Test cache operations
            test_key = 'health_check_test'
            test_value = 'test_value'
            
            # Test set and get
            set_result = self.set(test_key, test_value, ttl=10)
            get_result = self.get(test_key)
            delete_result = self.delete(test_key)
            
            health.update({
                'operations': {
                    'set': set_result,
                    'get': get_result == test_value,
                    'delete': delete_result
                }
            })
            
            if not all([set_result, get_result == test_value, delete_result]):
                health['status'] = 'degraded'
                
        except Exception as e:
            health.update({
                'status': 'unhealthy',
                'error': str(e)
            })
        
        return health
