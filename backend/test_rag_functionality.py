#!/usr/bin/env python3
"""
Comprehensive RAG Functionality Test
Tests all critical components of the RAG system to ensure nothing is lost.
"""

import os
import sys
import logging
import json
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_vector_search_engine():
    """Test the memory-optimized vector search engine"""
    logger.info("Testing memory-optimized vector search engine...")
    
    try:
        from config import Config
        from vector_search_memory_optimized import MemoryOptimizedVectorSearchEngine
        
        config = Config()
        vector_engine = MemoryOptimizedVectorSearchEngine(config)
        
        # Test initialization
        logger.info("Testing initialization...")
        vector_engine.initialize()
        
        if not vector_engine.is_ready():
            logger.error("❌ Vector search engine not ready after initialization")
            return False
        
        if not vector_engine.chunks:
            logger.error("❌ No chunks loaded - RAG functionality broken")
            return False
        
        logger.info(f"✅ Initialization successful. Loaded {len(vector_engine.chunks)} chunks")
        
        # Test search functionality
        logger.info("Testing search functionality...")
        test_queries = [
            "selective mutism treatment",
            "school strategies for selective mutism",
            "parent guidance selective mutism"
        ]
        
        for query in test_queries:
            results = vector_engine.search(query, top_k=3)
            if not results:
                logger.error(f"❌ No results for query: {query}")
                return False
            
            logger.info(f"✅ Query '{query}' returned {len(results)} results")
            
            # Verify result structure
            for result in results:
                required_fields = ['text', 'source_file', 'chunk_id', 'similarity_score', 'metadata']
                for field in required_fields:
                    if field not in result:
                        logger.error(f"❌ Missing field '{field}' in search result")
                        return False
        
        # Test stats
        stats = vector_engine.get_stats()
        logger.info(f"✅ Search engine stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Vector search test failed: {e}")
        return False

def test_chat_functionality():
    """Test the complete chat/RAG pipeline"""
    logger.info("Testing complete chat/RAG pipeline...")
    
    try:
        from config import Config
        from deepseek_client import DeepSeekClient
        
        config = Config()
        
        if not config.API_CALLS_ENABLED:
            logger.warning("⚠️  API calls disabled - skipping chat test")
            return True
        
        # Test DeepSeek client
        deepseek_client = DeepSeekClient(config)
        if not deepseek_client.is_ready():
            logger.error("❌ DeepSeek client not ready")
            return False
        
        logger.info("✅ DeepSeek client ready")
        
        # Test a simple chat request
        test_message = "What is selective mutism?"
        
        # Create mock context passages
        context_passages = [{
            'text': 'Selective mutism is an anxiety disorder where a person is unable to speak in certain social situations.',
            'source_file': 'test.txt',
            'similarity_score': 0.9
        }]
        
        # Test the generate_response method
        response = deepseek_client.generate_response(test_message, context_passages)
        
        if not response:
            logger.error("❌ No response from DeepSeek client")
            return False
        
        logger.info(f"✅ Chat response received: {response[:100]}...")
        return True
        
    except Exception as e:
        logger.error(f"❌ Chat functionality test failed: {e}")
        return False

def test_memory_optimization():
    """Test memory optimization features"""
    logger.info("Testing memory optimization features...")
    
    try:
        import psutil
        
        # Test memory monitoring
        available_memory = psutil.virtual_memory().available / (1024 * 1024)
        logger.info(f"Available memory: {available_memory:.1f} MB")
        
        # Test environment variables
        env_vars = {
            'USE_SMALLER_MODEL': 'True',
            'MAX_MEMORY_MB': '400',
            'MIN_MEMORY_FOR_MODEL': '150',
            'LAZY_LOAD_MODEL': 'True'
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            logger.info(f"Set {key}={value}")
        
        # Test with memory-optimized settings
        from config import Config
        from vector_search_memory_optimized import MemoryOptimizedVectorSearchEngine
        
        config = Config()
        vector_engine = MemoryOptimizedVectorSearchEngine(config)
        
        # Test initialization with memory constraints
        vector_engine.initialize()
        
        if not vector_engine.is_ready():
            logger.error("❌ Memory-optimized engine not ready")
            return False
        
        # Test search with memory monitoring
        results = vector_engine.search("test query", top_k=2)
        if not results:
            logger.error("❌ No search results with memory optimization")
            return False
        
        logger.info("✅ Memory optimization working correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory optimization test failed: {e}")
        return False

def test_deployment_scenarios():
    """Test deployment-specific scenarios"""
    logger.info("Testing deployment scenarios...")
    
    scenarios = [
        {
            'name': 'Low memory scenario',
            'env_vars': {
                'MAX_MEMORY_MB': '100',
                'MIN_MEMORY_FOR_MODEL': '200'
            }
        },
        {
            'name': 'No cache scenario',
            'env_vars': {
                'EMBEDDINGS_CACHE_PATH': '/tmp/nonexistent_cache.pkl',
                'INDEX_CACHE_PATH': '/tmp/nonexistent_index.bin'
            }
        }
    ]
    
    for scenario in scenarios:
        logger.info(f"Testing scenario: {scenario['name']}")
        
        try:
            # Set scenario environment variables
            for key, value in scenario['env_vars'].items():
                os.environ[key] = value
            
            from config import Config
            from vector_search_memory_optimized import MemoryOptimizedVectorSearchEngine
            
            config = Config()
            vector_engine = MemoryOptimizedVectorSearchEngine(config)
            
            # Test initialization
            vector_engine.initialize()
            
            # Test search (should fall back to keyword search if needed)
            results = vector_engine.search("test", top_k=1)
            
            # Should at least be ready (even if no results)
            if not vector_engine.is_ready():
                logger.error(f"❌ Engine not ready in scenario: {scenario['name']}")
                return False
            
            logger.info(f"✅ Scenario '{scenario['name']}' passed")
            
        except Exception as e:
            logger.error(f"❌ Scenario '{scenario['name']}' failed: {e}")
            return False
    
    return True

def main():
    """Run all tests"""
    logger.info("Starting comprehensive RAG functionality tests...")
    
    tests = [
        ("Vector Search Engine", test_vector_search_engine),
        ("Chat Functionality", test_chat_functionality),
        ("Memory Optimization", test_memory_optimization),
        ("Deployment Scenarios", test_deployment_scenarios)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Test Results: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 All tests passed! RAG functionality is preserved.")
        return True
    else:
        logger.error("❌ Some tests failed. RAG functionality may be compromised.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
