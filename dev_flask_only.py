#!/usr/bin/env python3
"""
Development Flask-only script for Bikera Mining Bot
Runs only the Flask API without Telegram bot to avoid conflicts
"""
import os
import logging
from dotenv import load_dotenv
from production_app import app

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for development Flask server"""
    # Use port 8000 in development to avoid conflict with frontend
    port = int(os.environ.get('DEV_PORT', 8000))
    
    logger.info(f"Starting Flask API only (DEVELOPMENT) on port {port}")
    logger.info("Telegram bot is NOT running in development mode")
    logger.info("To test Telegram bot, deploy to production")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Flask server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()