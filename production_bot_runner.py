#!/usr/bin/env python3
"""
Production bot runner with proper async handling
Ensures the Telegram bot keeps running in deployment
"""
import os
import sys
import logging
import asyncio
import signal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global bot instance for shutdown handling
bot_instance = None
shutdown_event = asyncio.Event()

async def run_telegram_bot():
    """Run the Telegram bot with proper lifecycle management"""
    global bot_instance
    
    try:
        from core.utils import setup_logging, ensure_directories, debug_startup
        from storage.location_logger import LocationLogger
        from bot.telegram_bot import TelegramBot
        from config.settings import TELEGRAM_TOKEN
        
        bot_logger = setup_logging()
        ensure_directories()
        debug_startup()
        
        if not TELEGRAM_TOKEN:
            logger.error("TELEGRAM_TOKEN not set - cannot start bot")
            return
            
        logger.info("Initializing Telegram bot components...")
        location_logger = LocationLogger()
        await location_logger.load_blockchain_state()
        
        bot_instance = TelegramBot(TELEGRAM_TOKEN, location_logger)
        
        # Start the bot without waiting for stop signal
        logger.info("Starting Telegram bot polling...")
        bot_instance.setup_handlers()
        bot_instance.mining_task = asyncio.create_task(bot_instance.mining_loop())
        
        await bot_instance.app.initialize()
        await bot_instance.app.start()
        await bot_instance.app.updater.start_polling()
        
        logger.info("✅ Telegram bot is running successfully")
        logger.info("💰 Rewards tracked by Solana addresses")
        logger.info("🔐 Private keys managed per Telegram user")
        
        # Keep the bot running until shutdown signal
        await shutdown_event.wait()
        
        # Graceful shutdown
        logger.info("Shutting down Telegram bot...")
        await bot_instance.stop()
        
    except Exception as e:
        logger.error(f"Bot error: {e}")
        import traceback
        traceback.print_exc()
        raise

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()

async def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await run_telegram_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    logger.info("Starting Telegram bot (standalone mode)...")
    asyncio.run(main())