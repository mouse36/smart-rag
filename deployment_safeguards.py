"""
Deployment safeguards for Railway deployment
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def setup_deployment_safeguards() -> None:
    """
    Set up deployment safeguards for Railway environment
    """
    try:
        # Ensure proper environment variables for Railway
        if not os.getenv('PORT'):
            logger.warning("PORT environment variable not set, Railway will set this automatically")
        
        # Set production defaults
        if not os.getenv('DEBUG'):
            os.environ['DEBUG'] = 'False'
        
        if not os.getenv('HOST'):
            os.environ['HOST'] = '0.0.0.0'
        
        # Memory optimization for Railway
        if not os.getenv('LAZY_LOAD_MODEL'):
            os.environ['LAZY_LOAD_MODEL'] = 'True'
        
        if not os.getenv('USE_LIGHTWEIGHT_SEARCH'):
            os.environ['USE_LIGHTWEIGHT_SEARCH'] = 'True'
        
        logger.info("Deployment safeguards configured successfully")
        
    except Exception as e:
        logger.warning(f"Deployment safeguards setup failed: {e}")
        # Don't fail deployment for safeguard issues
