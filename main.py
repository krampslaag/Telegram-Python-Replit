"""
Main entry point for the Bikera Mining Bot
"""
import asyncio
import logging
import os
import signal
import sys
from dotenv import load_dotenv
from core.utils import setup_logging, ensure_directories, debug_startup
from storage.location_logger import LocationLogger
from bot.telegram_bot import TelegramBot
from config.settings import TELEGRAM_TOKEN

# Load environment variables
load_dotenv()

# Global variables for graceful shutdown
bot_instance = None
location_logger = None

async def main():
    """Main application entry point"""
    global bot_instance, location_logger
    
    # Setup logging and directories
    logger = setup_logging()
    ensure_directories()
    
    # Debug startup information
    debug_startup()
    
    # Check for required environment variables
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN environment variable is required")
        sys.exit(1)
    
    try:
        # Initialize components with hybrid user identification
        logger.info("🔧 Initializing LocationLogger with hybrid user identification...")
        location_logger = LocationLogger()
        
        # Load existing blockchain state
        logger.info("📂 Loading existing blockchain state...")
        await location_logger.load_blockchain_state()
        
        # Initialize Telegram bot
        logger.info("🤖 Initializing Telegram bot...")
        bot_instance = TelegramBot(TELEGRAM_TOKEN, location_logger)
        
        # Start the bot
        logger.info("🚀 Starting Bikera Mining Bot...")
        await bot_instance.start()
        
    except KeyboardInterrupt:
        logger.info("⚠️ Received keyboard interrupt")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        if bot_instance:
            await bot_instance.stop()
        if location_logger:
            await location_logger.cleanup()
        logger.info("🏁 Application shutdown complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger = logging.getLogger(__name__)
    logger.info(f"📡 Received signal {signum}")
    
    # Create new event loop for cleanup if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Schedule cleanup
    if bot_instance:
        loop.create_task(bot_instance.stop())
    if location_logger:
        loop.create_task(location_logger.cleanup())
    
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the main application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)
