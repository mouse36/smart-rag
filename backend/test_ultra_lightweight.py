#!/usr/bin/env python3
"""
Test script for ultra-lightweight vector search engine
"""

import os
import sys
import logging

# Add the backend directory to the path
sys.path.append(os.path.dirname(__file__))

from config import Config
from vector_search_ultra_lightweight import UltraLightweightVectorSearchEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ultra_lightweight_engine():
    """Test the ultra-lightweight vector search engine"""
    try:
        logger.info("Testing ultra-lightweight vector search engine...")
        
        # Initialize config
        config = Config()
        
        # Initialize engine
        engine = UltraLightweightVectorSearchEngine(config)
        
        # Initialize the engine
        engine.initialize()
        
        # Get status
        status = engine.get_status()
        logger.info(f"Engine status: {status}")
        
        # Test search
        test_query = "selective mutism treatment"
        results = engine.search(test_query, top_k=3)
        
        logger.info(f"Search results for '{test_query}':")
        for i, result in enumerate(results):
            logger.info(f"  {i+1}. {result['source_file']} (similarity: {result['similarity']:.3f})")
            logger.info(f"     Text: {result['text'][:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

def main():
    """Main test function"""
    logger.info("Starting ultra-lightweight engine test...")
    
    success = test_ultra_lightweight_engine()
    
    if success:
        logger.info("Ultra-lightweight engine test passed!")
        return 0
    else:
        logger.error("Ultra-lightweight engine test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
