#!/usr/bin/env python3
"""
Bikera Mining Bot - Main Entry Point
GPS-based cryptocurrency mining with blockchain logging
"""
import asyncio
import signal
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.utils import setup_logging, ensure_directories, debug_startup
from storage.location_logger import LocationLogger
from bot.telegram_bot import TelegramBot
from config.settings import TELEGRAM_TOKEN

async def main():
    """Main application entry point"""
    try:
        # Debug startup
        debug_startup()
        
        # Setup logging and directories
        logger = setup_logging()
        ensure_directories()
        
        logger.info("🚀 Starting Bikera Mining Bot...")
        
        # Validate configuration
        if not TELEGRAM_TOKEN:
            logger.error("❌ TELEGRAM_TOKEN not found in environment variables")
            logger.error("Please create a .env file with your Telegram bot token")
            return 1
        
        # Initialize core components
        logger.info("📦 Initializing components...")
        location_logger = LocationLogger()
        
        # Create bot instance
        logger.info("🤖 Creating Telegram bot...")
        bot = TelegramBot(TELEGRAM_TOKEN, location_logger)
        
        # Setup graceful shutdown
        def signal_handler():
            logger.info("⏹️ Received shutdown signal...")
            asyncio.create_task(bot.stop())
        
        # Register signal handlers (Unix-like systems)
        if sys.platform != 'win32':
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, signal_handler)
        
        # Start the bot
        logger.info("▶️ Starting bot...")
        await bot.start()
        
        logger.info("✅ Bot started successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⏹️ Received keyboard interrupt")
        return 0
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

def run():
    """Run the application with proper event loop handling"""
    try:
        # Set up event loop policy for Windows compatibility
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Run the main function
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run()