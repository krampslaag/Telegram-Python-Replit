#!/usr/bin/env python3
"""
Production deployment script for Bikera Mining Bot
Runs both Flask API and Telegram bot for deployment only
"""
import os
import sys
import logging
import asyncio
import threading
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_flask_app(port):
    """Run the Flask web application"""
    try:
        from production_app import app
        logger.info(f"Starting Flask app on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Flask app error: {e}")
        import traceback
        traceback.print_exc()

async def run_telegram_bot():
    """Run the Telegram bot"""
    try:
        from core.utils import setup_logging, ensure_directories, debug_startup
        from storage.location_logger import LocationLogger
        from bot.telegram_bot import TelegramBot
        from config.settings import TELEGRAM_TOKEN
        
        bot_logger = setup_logging()
        ensure_directories()
        debug_startup()
        
        if not TELEGRAM_TOKEN:
            logger.warning("TELEGRAM_TOKEN not set - Telegram bot will not start")
            return
            
        # Add delay to ensure previous instances have time to shut down
        logger.info("Waiting 5 seconds to ensure clean startup...")
        await asyncio.sleep(5)
            
        logger.info("Initializing Telegram bot components...")
        location_logger = LocationLogger()
        await location_logger.load_blockchain_state()
        
        bot_instance = TelegramBot(TELEGRAM_TOKEN, location_logger)
        logger.info("Starting Telegram bot...")
        
        # Handle potential conflicts gracefully
        max_retries = 3
        retry_delay = 10
        
        for attempt in range(max_retries):
            try:
                # Start the bot components manually without waiting for stop signal
                bot_instance.setup_handlers()
                bot_instance.mining_task = asyncio.create_task(bot_instance.mining_loop())
                
                await bot_instance.app.initialize()
                await bot_instance.app.start()
                await bot_instance.app.updater.start_polling()
                
                logger.info("Telegram bot started successfully and is polling for updates")
                
                # Keep the bot running in the background
                # Don't wait for stop signal here - let it run independently
                break
                
            except Exception as e:
                if "Conflict" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Bot conflict detected, waiting {retry_delay} seconds before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(retry_delay)
                else:
                    raise
        
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
        import traceback
        traceback.print_exc()

def run_telegram_in_thread():
    """Run Telegram bot in a separate thread"""
    while True:  # Keep trying to run the bot
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Keep the bot running
            logger.info("Starting Telegram bot event loop...")
            loop.run_until_complete(run_telegram_bot())
            
            # Keep the thread alive even after bot finishes
            logger.info("Telegram bot keeping thread alive...")
            loop.run_forever()
            
        except KeyboardInterrupt:
            logger.info("Telegram bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Telegram thread error: {e}")
            import traceback
            traceback.print_exc()
            
            # In production, restart after error
            logger.warning("Bot crashed - restarting in 30 seconds...")
            import time
            time.sleep(30)

def main():
    """Main entry point for production deployment"""
    # Get port from environment (Cloud Run sets this automatically)
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"Starting Bikera Mining Bot (PRODUCTION) on port {port}")
    
    # Create thread for Telegram bot
    # daemon=False ensures the thread won't be killed when main thread exits
    telegram_thread = threading.Thread(target=run_telegram_in_thread, daemon=False)
    telegram_thread.start()
    
    # Give Telegram bot time to initialize
    import time
    time.sleep(5)
    
    # Run Flask app in main thread (blocking)
    run_flask_app(port)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)