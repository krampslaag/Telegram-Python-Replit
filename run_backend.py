#!/usr/bin/env python3
"""
Production-ready backend runner for Bikera Mining Bot
"""
import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the backend application"""
    try:
        # Import and run the app
        from app import app
        
        # Determine port based on environment
        if os.environ.get('PRODUCTION'):
            port = int(os.environ.get('PORT', 5000))
            logger.info(f"Running in PRODUCTION mode on port {port}")
        else:
            port = int(os.environ.get('BACKEND_PORT', 8000))
            logger.info(f"Running in DEVELOPMENT mode on port {port}")
        
        # Start the Flask application
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()