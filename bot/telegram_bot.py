"""
Main Telegram bot class with privacy-preserving mining and hybrid user identification
"""
import asyncio
import logging
import time
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from bot.handlers import BotHandlers
from bot.conversations import ConversationHandlers
from core.mining import MiningInterval, WinnerDetermination
from core.node_manager import NodeManager
from storage.location_logger import LocationLogger

logger = logging.getLogger(__name__)

class TelegramBot:
    """Main Telegram bot class with privacy-preserving coordinate handling and hybrid identification"""
    
    def __init__(self, token: str, location_logger: LocationLogger):
        self.token = token
        self.location_logger = location_logger
        self.app = ApplicationBuilder().token(token).build()
        
        # Initialize handlers
        self.handlers = BotHandlers(location_logger)
        self.conversations = ConversationHandlers(location_logger)
        
        # Initialize node manager
        self.node_manager = NodeManager()
        self.node_manager.register_node()
        
        # Mining loop control
        self.mining_task = None
        self.stop_flag = asyncio.Event()
        
        # Heartbeat task for node management
        self.heartbeat_task = None
        
        # Bot handler status
        self.is_bot_active = True  # Start as active, will be adjusted based on era

    async def mining_loop(self):
        """Privacy-preserving mining loop with obfuscated coordinates and hybrid identification"""
        logger.info("🔄 Starting mining loop with hybrid user identification...")
        
        while not self.stop_flag.is_set():
            try:
                # Increment interval counter
                self.location_logger.interval_count += 1
                
                # Check if this node should handle Telegram for current era
                should_handle, designated_handler = self.node_manager.should_handle_telegram(self.location_logger.interval_count)
                
                # Update bot handler status based on era rotation
                if should_handle != self.is_bot_active:
                    if should_handle:
                        await self._enable_telegram_handlers()
                        logger.info(f"✅ Telegram bot handlers ENABLED for era {self.node_manager.get_current_era(self.location_logger.interval_count)}")
                    else:
                        await self._disable_telegram_handlers()
                        logger.info(f"⏸️ Telegram bot handlers DISABLED - Node {designated_handler} is handling this era")
                
                # Start new interval
                target_distance = self.location_logger.current_interval.start(self.location_logger.interval_count)
                
                logger.info(f"⏱️ Interval {self.location_logger.interval_count} started - waiting 600 seconds")
                logger.info(f"🎯 Target distance: {target_distance:.3f}km")
                logger.info(f"🔒 Coordinate obfuscation: ENABLED")
                logger.info(f"🔐 Hybrid identification: Solana addresses for rewards, Telegram IDs for encryption")

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
                    
                    # Get previous interval object for obfuscated coordinate processing
                    prev_interval = None
                    if hasattr(self.location_logger, 'previous_interval_obj'):
                        prev_interval = self.location_logger.previous_interval_obj
                    
                    winner = WinnerDetermination.determine_winner(
                        self.location_logger.previous_interval, 
                        current_coords, 
                        target_distance,
                        prev_interval,
                        self.location_logger.current_interval
                    )
                    
                    if winner:
                        new_block = await self.location_logger.process_winner(winner, target_distance)
                        if new_block:
                            logger.info(f"✅ Block #{new_block.block_height} added successfully")
                            logger.info(f"🏆 Winner: Telegram user {winner['user_id']}")
                            logger.info(f"💰 Rewards to: {winner['solana_address'][:8]}...{winner['solana_address'][-8:]}")
                            
                            # Check if we need to save epoch (every 100 blocks)
                            if new_block.block_height % 100 == 0:
                                logger.info(f"📦 Block {new_block.block_height} reached - saving epoch to .era file")
                                await self.location_logger._save_epoch_blocks()
                                
                            # Check if we need to reset interval counter at 100
                            if self.location_logger.interval_count == 100:
                                logger.info(f"🔄 Interval 100 reached - resetting interval counter to 1")
                                self.location_logger.interval_count = 0  # Will be incremented to 1 at start of next loop
                            
                            # Notify winner via Telegram
                            try:
                                await self.app.bot.send_message(
                                    chat_id=winner['user_id'],
                                    text=(
                                        f"🎉 **Congratulations! You won the mining interval!** 🎉\n\n"
                                        f"🏆 **Interval #{self.location_logger.interval_count}**\n"
                                        f"🎯 **Target Distance:** {target_distance:.3f}km\n"
                                        f"📏 **Your Distance:** {winner['travel_distance']:.3f}km\n"
                                        f"📊 **Difference:** {winner['difference']:.3f}km\n"
                                        f"💰 **Reward:** {new_block.reward} IMERA\n"
                                        f"🔗 **Your Address:** `{winner['solana_address'][:8]}...{winner['solana_address'][-8:]}`\n\n"
                                        f"🔒 Your coordinates were obfuscated for privacy protection."
                                    ),
                                    parse_mode='Markdown'
                                )
                            except Exception as e:
                                logger.error(f"Failed to notify winner {winner['user_id']}: {e}")
                    else:
                        logger.info("❌ No winner found for this interval")
                else:
                    if self.location_logger.interval_count < 3:
                        logger.info(f"📝 Interval {self.location_logger.interval_count}: Data collection only (winners start from interval 3)")
                    else:
                        logger.info("📝 No previous interval data available")

                # Set current as previous for next iteration
                self.location_logger.previous_interval = current_coords.copy() if current_coords else None
                self.location_logger.previous_interval_obj = self.location_logger.current_interval
                
                # Create new interval for next round
                self.location_logger.current_interval = MiningInterval()
                
                # Save state after each interval
                await self.location_logger.save_user_data()
                
                logger.info(f"🔄 Preparing for interval {self.location_logger.interval_count + 1}")
                
            except Exception as e:
                logger.error(f"💥 Mining loop error: {e}")
                import traceback
                traceback.print_exc()
                
                if not self.stop_flag.is_set():
                    logger.info("😴 Waiting 5 seconds before retry...")
                    await asyncio.sleep(5)

    async def _enable_telegram_handlers(self):
        """Enable Telegram command handlers"""
        self.setup_handlers()
        self.is_bot_active = True
        logger.info("✅ Telegram handlers enabled")
    
    async def _disable_telegram_handlers(self):
        """Disable Telegram command handlers"""
        # Remove all handlers
        for group in self.app.handlers:
            for handler in list(self.app.handlers[group]):
                self.app.remove_handler(handler)
        self.is_bot_active = False
        logger.info("⏸️ Telegram handlers disabled")
    
    async def heartbeat_loop(self):
        """Maintain node heartbeat and cleanup inactive nodes"""
        while not self.stop_flag.is_set():
            try:
                # Update heartbeat
                self.node_manager.update_heartbeat()
                
                # Cleanup inactive nodes every 5 minutes
                if int(time.time()) % 300 == 0:
                    removed = self.node_manager.cleanup_inactive_nodes()
                    if removed > 0:
                        logger.info(f"🧹 Cleaned up {removed} inactive nodes")
                
                # Log node status every minute
                if int(time.time()) % 60 == 0:
                    status = self.node_manager.get_node_status()
                    logger.info(f"📊 Node status - Active: {status['active_nodes']}/{status['total_nodes']} nodes")
                
                await asyncio.sleep(10)  # Heartbeat every 10 seconds
                
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(10)

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
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.conversations.handle_document_import))

    async def start(self):
        """Start the bot"""
        try:
            # Check initial era handler status
            should_handle, designated_handler = self.node_manager.should_handle_telegram(self.location_logger.interval_count)
            
            if should_handle:
                # Setup handlers if this node should handle Telegram
                self.setup_handlers()
                logger.info(f"✅ This node ({self.node_manager.node_id}) is handling Telegram for current era")
            else:
                self.is_bot_active = False
                logger.info(f"⏸️ This node is in standby - Node {designated_handler} is handling Telegram")
            
            # Start mining in background
            self.mining_task = asyncio.create_task(self.mining_loop())
            
            # Start heartbeat loop
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())

            # Start bot
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()

            logger.info("🤖 Bot started successfully with node rotation")
            logger.info("💰 Rewards tracked by Solana addresses")
            logger.info("🔐 Private keys managed per Telegram user")
            logger.info(f"🔄 Era: {self.node_manager.get_current_era(self.location_logger.interval_count)}")

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
            
            # Cancel heartbeat task
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            # Stop bot
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("🤖 Bot stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ Error stopping bot: {e}")
