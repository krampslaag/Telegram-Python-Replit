"""
Main Telegram bot class with privacy-preserving mining
"""
import asyncio
import logging
import time
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from bot.handlers import BotHandlers
from bot.conversations import ConversationHandlers
from core.mining import MiningInterval

logger = logging.getLogger(__name__)

class TelegramBot:
    """Main Telegram bot class with privacy-preserving coordinate handling"""
    
    def __init__(self, token, location_logger):
        self.token = token
        self.location_logger = location_logger
        self.app = ApplicationBuilder().token(token).build()
        
        # Initialize handlers
        self.handlers = BotHandlers(location_logger)
        self.conversations = ConversationHandlers(location_logger)
        
        # Mining loop control
        self.mining_task = None
        self.stop_flag = asyncio.Event()

    async def mining_loop(self):
        """Privacy-preserving mining loop with obfuscated coordinates"""
        logger.info("🔄 Starting mining loop...")
        
        while not self.stop_flag.is_set():
            try:
                # Increment interval counter
                self.location_logger.interval_count += 1
                
                # Start new interval
                target_distance = self.location_logger.current_interval.start(self.location_logger.interval_count)
                
                logger.info(f"⏱️ Interval {self.location_logger.interval_count} started - waiting 600 seconds")
                logger.info(f"🎯 Target distance: {target_distance:.3f}km")
                logger.info(f"🔒 Coordinate obfuscation: ENABLED")

                # Wait for interval duration (10 minutes = 600 seconds)
                try:
                    await asyncio.wait_for(self.stop_flag.wait(), timeout=600)
                    if self.stop_flag.is_set():
                        logger.info("🛑 Mining loop stopped by signal")
                        break
                except asyncio.TimeoutError:
                    # Normal timeout - interval completed
                    pass

                # Finalize current interval
                current_coords = self.location_logger.current_interval.finalize_interval()
                
                logger.info(f"📊 Interval {self.location_logger.interval_count} completed")
                logger.info(f"👥 Participants: {len(current_coords)}")

                # Process winner (from interval 3 onward)
                if self.location_logger.previous_interval and self.location_logger.interval_count >= 3:
                    logger.info(f"🔍 Checking for winner in interval {self.location_logger.interval_count}")
                    
                    winner = self.location_logger.determine_winner(
                        self.location_logger.previous_interval, 
                        current_coords, 
                        target_distance
                    )
                    
                    if winner:
                        new_block = self.location_logger.process_winner(winner, target_distance)
                        if new_block:
                            logger.info(f"✅ Block #{len(self.location_logger.blockchain.chain)-1} added successfully")
                    else:
                        logger.info("❌ No winner found for this interval")
                else:
                    if self.location_logger.interval_count < 3:
                        logger.info(f"📝 Interval {self.location_logger.interval_count}: Data collection only (winners start from interval 3)")
                    else:
                        logger.info("📝 No previous interval data available")

                # Set current as previous for next iteration
                self.location_logger.previous_interval = current_coords.copy() if current_coords else None
                
                # Create new interval for next round
                self.location_logger.current_interval = MiningInterval()
                
                logger.info(f"🔄 Preparing for interval {self.location_logger.interval_count + 1}")
                
            except Exception as e:
                logger.error(f"💥 Mining loop error: {e}")
                import traceback
                traceback.print_exc()
                
                if not self.stop_flag.is_set():
                    logger.info("😴 Waiting 5 seconds before retry...")
                    await asyncio.sleep(5)

    def setup_handlers(self):
        """Setup all bot handlers"""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.handlers.start))
        self.app.add_handler(CommandHandler("help", self.handlers.help_command))
        self.app.add_handler(CommandHandler("status", self.handlers.interval_status))
        self.app.add_handler(CommandHandler("rewards", self.handlers.get_stats))
        self.app.add_handler(CommandHandler("blockchain", self.handlers.blockchain_stats_command))
        self.app.add_handler(CommandHandler("download_blockchain", self.handlers.download_blockchain))
        self.app.add_handler(CommandHandler("download_coordinates", self.handlers.download_coordinates))
        self.app.add_handler(CommandHandler("export_keys", self.handlers.export_keys_handler))
        self.app.add_handler(CommandHandler("import_keys", self.handlers.import_keys_handler))
        
        # Conversation handlers
        self.app.add_handler(self.conversations.get_address_conversation_handler())
        self.app.add_handler(self.conversations.get_location_conversation_handler())
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.LOCATION, self.handlers.handle_location))

    async def start(self):
        """Start the bot"""
        try:
            # Setup handlers
            self.setup_handlers()
            
            # Start mining in background
            self.mining_task = asyncio.create_task(self.mining_loop())

            # Start bot
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()

            logger.info("🤖 Bot started successfully")

            # Wait for stop signal
            await self.stop_flag.wait()
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
            raise

    async def stop(self):
        """Stop the bot"""
        try:
            # Set stop flag
            self.stop_flag.set()

            # Cancel mining task
            if self.mining_task:
                self.mining_task.cancel()
                try:
                    await self.mining_task
                except asyncio.CancelledError:
                    pass

            # Stop bot
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("🤖 Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ Error stopping bot: {e}")
