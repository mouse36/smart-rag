#!/usr/bin/env python3
"""
Test script for memory optimization
"""

import os
import sys
import psutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_memory_usage():
    """Test memory usage of the application"""
    logger.info("Testing memory optimization...")
    
    # Set memory optimization environment variables
    os.environ['USE_SMALLER_MODEL'] = 'True'
    os.environ['MAX_MEMORY_MB'] = '400'
    os.environ['LAZY_LOAD_MODEL'] = 'True'
    os.environ['CHUNK_SIZE'] = '300'
    os.environ['CHUNK_OVERLAP'] = '30'
    
    try:
        # Import and test vector search
        from config import Config
        from vector_search_memory_optimized import MemoryOptimizedVectorSearchEngine
        
        config = Config()
        vector_engine = MemoryOptimizedVectorSearchEngine(config)
        
        # Check initial memory
        initial_memory = psutil.virtual_memory().available / (1024 * 1024)
        logger.info(f"Initial available memory: {initial_memory:.1f} MB")
        
        # Initialize vector search
        vector_engine.initialize()
        
        # Check memory after initialization
        after_init_memory = psutil.virtual_memory().available / (1024 * 1024)
        logger.info(f"Memory after initialization: {after_init_memory:.1f} MB")
        logger.info(f"Memory used: {initial_memory - after_init_memory:.1f} MB")
        
        # Test search
        results = vector_engine.search("selective mutism treatment", top_k=3)
        logger.info(f"Search results: {len(results)} found")
        
        # Check memory after search
        after_search_memory = psutil.virtual_memory().available / (1024 * 1024)
        logger.info(f"Memory after search: {after_search_memory:.1f} MB")
        logger.info(f"Total memory used: {initial_memory - after_search_memory:.1f} MB")
        
        # Get stats
        stats = vector_engine.get_stats()
        logger.info(f"Search engine stats: {stats}")
        
        if stats['search_type'] == 'vector':
            logger.info("✅ Vector search is working!")
        else:
            logger.info("⚠️  Using keyword search fallback")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_memory_usage()
    sys.exit(0 if success else 1)
