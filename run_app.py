#!/usr/bin/env python3
"""
Unified startup script for Bikera Mining Bot
Runs both the Flask web app and Telegram bot
"""
import os
import sys
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_flask_app():
    """Run the Flask web application"""
    try:
        from production_app import app
        
        # Get port from environment
        # In deployment, use PORT env variable (usually 5000)
        # In development, use 8000 to avoid conflict with frontend
        port = int(os.environ.get('PORT', 8000 if not os.environ.get('PORT') else os.environ.get('PORT')))
        
        logger.info(f"Starting Flask app on port {port}")
        
        # Run Flask app (blocking)
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"Flask app error: {e}")
        import traceback
        traceback.print_exc()

async def run_telegram_bot():
    """Run the Telegram bot"""
    try:
        # Import telegram bot components
        from core.utils import setup_logging, ensure_directories, debug_startup
        from storage.location_logger import LocationLogger
        from bot.telegram_bot import TelegramBot
        from config.settings import TELEGRAM_TOKEN
        
        # Setup
        bot_logger = setup_logging()
        ensure_directories()
        debug_startup()
        
        if not TELEGRAM_TOKEN:
            logger.warning("TELEGRAM_TOKEN not set - Telegram bot will not start")
            return
            
        # Check if we're in production (deployment) mode
        is_production = os.environ.get('DEPLOYMENT_MODE') == 'production' or os.environ.get('PORT')
        
        if not is_production:
            logger.info("Skipping Telegram bot in development mode to avoid conflicts")
            return
            
        # Initialize components
        logger.info("Initializing Telegram bot components...")
        location_logger = LocationLogger()
        await location_logger.load_blockchain_state()
        
        bot_instance = TelegramBot(TELEGRAM_TOKEN, location_logger)
        
        logger.info("Starting Telegram bot...")
        await bot_instance.start()
        
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
        import traceback
        traceback.print_exc()

def run_telegram_in_thread():
    """Run Telegram bot in a separate thread with its own event loop"""
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the bot
        loop.run_until_complete(run_telegram_bot())
        
    except Exception as e:
        logger.error(f"Telegram thread error: {e}")

def main():
    """Main entry point"""
    logger.info("Starting Bikera Mining Bot (Web + Telegram)")
    
    # Create thread for Telegram bot
    telegram_thread = threading.Thread(target=run_telegram_in_thread, daemon=True)
    telegram_thread.start()
    
    # Give Telegram bot time to initialize
    import time
    time.sleep(2)
    
    # Run Flask app in main thread (blocking)
    run_flask_app()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)