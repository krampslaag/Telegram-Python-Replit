"""
Telegram bot command handlers
"""
import os
import time
import datetime
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class BotHandlers:
    """Collection of Telegram bot command handlers"""
    
    def __init__(self, location_logger):
        self.location_logger = location_logger

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        if user_id not in self.location_logger.user_keys:
            public_key = self.location_logger.generate_user_keys(user_id)
            await update.message.reply_text(
                "🔒 Welcome to the GPS Bikera MERA distribution Bot!\n\n"
                "✅ Your encryption keys have been generated.\n"
                "🛡️ Your location data will be obfuscated for privacy.\n"
                "Please set your Solana address using /setaddress.\n\n"
                "Use /help to see all available commands."
            )
        else:
            await update.message.reply_text(
                "🔒 Welcome back!\n"
                "Your encryption keys are already set up.\n"
                "🛡️ Your location data is protected with obfuscation.\n"
                "Use /help to see all available commands."
            )

    async def interval_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced status command with detailed debugging info"""
        user_id = update.effective_user.id
        
        # Current interval status
        if self.location_logger.current_interval.is_active:
            time_remaining = self.location_logger.current_interval.get_time_remaining()
            participants = len(self.location_logger.current_interval.staged_coordinates)
            target = self.location_logger.current_interval.target_distance
            
            # Check if user is participating (check by looking for their hash)
            user_participating = "❌ No"
            if hasattr(self.location_logger.current_interval, '_user_id_mapping'):
                for user_hash, real_id in self.location_logger.current_interval._user_id_mapping.items():
                    if real_id == user_id:
                        user_participating = "✅ Yes"
                        break
            
            status_text = (
                f"🔄 **Active Interval {self.location_logger.interval_count}**\n\n"
                f"⏱️ Time remaining: {time_remaining} seconds\n"
                f"🎯 Target distance: {target:.3f}km\n"
                f"👥 Current participants: {participants}\n"
                f"📍 You participating: {user_participating}\n\n"
            )
            
            if self.location_logger.interval_count < 3:
                status_text += "📝 **Data Collection Phase**\nWinners will be determined from interval 3 onward.\n\n"
            else:
                status_text += "🏆 **Competition Phase**\nWinners determined based on travel distance!\n\n"
                
            # Previous interval info
            if self.location_logger.previous_interval:
                prev_participants = len(self.location_logger.previous_interval)
                status_text += f"📊 Previous interval had {prev_participants} participants\n"
            
        else:
            status_text = (
                f"⏸️ **No Active Interval**\n\n"
                f"📊 Last completed: Interval {self.location_logger.interval_count}\n"
                f"🔄 Next interval starting soon...\n\n"
            )
        
        # User setup status
        has_keys = "✅" if user_id in self.location_logger.user_keys else "❌"
        has_address = "✅" if user_id in self.location_logger.user_addresses else "❌"
        
        status_text += (
            f"**Your Setup:**\n"
            f"{has_keys} Encryption keys\n"
            f"{has_address} Solana address\n\n"
            f"Use /help for more commands"
        )
        
        await update.message.reply_text(status_text, parse_mode='Markdown')

    async def blockchain_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for getting blockchain statistics"""
        stats = self.location_logger.get_blockchain_stats()
        
        last_block_time = "Never"
        if stats['last_block_time']:
            last_block_time = datetime.datetime.fromtimestamp(stats['last_block_time']).strftime("%Y-%m-%d %H:%M:%S")
        
        # Count privacy-protected blocks
        privacy_protected_blocks = 0
        for block in self.location_logger.blockchain.chain[1:]:  # Skip genesis
            try:
                import json
                block_data = json.loads(block.data)
                if block_data.get('privacy_protected', False):
                    privacy_protected_blocks += 1
            except:
                pass
        
        await update.message.reply_text(
            f"📊 Blockchain Statistics:\n\n"
            f"🧱 Total Blocks: {stats['total_blocks']}\n"
            f"💰 Total Rewards Distributed: {stats['total_rewards']} MERA\n"
            f"👥 Unique Miners: {stats['unique_miners']}\n"
            f"⏰ Last Block: {last_block_time}\n\n"
            f"Use /download_blockchain to export complete data"
        )

    async def download_blockchain(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for downloading blockchain data"""
        try:
            filepath = self.location_logger.export_blockchain_xml()
            with open(filepath, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename="blockchain_export.xml",
                    caption="Here's the current blockchain data in XML format."
                )
        except Exception as e:
            logger.error(f"Error exporting blockchain: {e}")
            await update.message.reply_text("Sorry, there was an error generating the blockchain export.")

    async def download_coordinates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for downloading user's coordinates"""
        user_id = update.effective_user.id

        if user_id not in self.location_logger.user_keys:
            await update.message.reply_text("Please use /start first to generate your keys.")
            return

        filepath = f"data/user_logs/user_{user_id}_coordinates.json"
        if not os.path.exists(filepath):
            await update.message.reply_text("No coordinate data found for your account yet.")
            return

        try:
            with open(filepath, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"coordinates_{user_id}.json",
                    caption="📋 Your coordinate data (encrypted)\n🔒 Only you can decrypt this data with your private key."
                )
        except Exception as e:
            logger.error(f"Error sending coordinates file: {e}")
            await update.message.reply_text("Sorry, there was an error retrieving your coordinates.")

    async def get_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for getting user statistics"""
        user_id = update.effective_user.id

        if user_id not in self.location_logger.user_keys:
            await update.message.reply_text("Please use /start first to generate your keys.")
            return

        stats = self.location_logger.get_user_stats(user_id)
        await update.message.reply_text(
            f"📊 Your Statistics:\n\n"
            f"🏆 Total Wins: {stats['total_wins']}\n"
            f"💰 Total Rewards: {stats['total_rewards']} MERA\n"
            f"🎯 Participated Intervals: {stats['participated_intervals']}\n\n"
            f"Use /download_coordinates to get your logged coordinates\n"
            f"Use /download_blockchain to get the complete blockchain data"
        )

    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location sharing"""
        user_id = update.effective_user.id
        location = update.message.location

        if user_id not in self.location_logger.user_keys:
            await update.message.reply_text("Please use /start first to generate your keys.")
            return

        if user_id not in self.location_logger.user_addresses:
            await update.message.reply_text("Please set your Solana address using /setaddress first.")
            return

        if not self.location_logger.current_interval.is_active:
            await update.message.reply_text("No active interval. Please wait for the next interval to start.")
            return

        coordinates = (location.latitude, location.longitude)
        
        # Log the original coordinates locally (encrypted)
        self.location_logger.log_user_coordinates(user_id, coordinates, time.time())
        
        # Stage obfuscated coordinates for the network
        self.location_logger.current_interval.stage_coordinates(user_id, coordinates)

        time_remaining = self.location_logger.current_interval.get_time_remaining()

        await update.message.reply_text(
            f"Location staged for this interval!\n"
            f"Time remaining: {time_remaining} seconds\n"
            f"Your coordinates will be finalized at interval end.\n"
            f"Target distance: {self.location_logger.current_interval.target_distance:.2f}km\n"
            f"You can update your location until the interval ends."
        )

    async def export_keys_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export user's encryption keys"""
        user_id = update.effective_user.id
        try:
            keys = self.location_logger.export_user_keys(user_id)
            await update.message.reply_text(
                f"🔑 Here are your encryption keys:\n\n"
                f"**Private Key:**\n`{keys['private_key']}`\n\n"
                f"**Public Key:**\n`{keys['public_key']}`\n\n"
                f"🔒 **Important:** Keep your private key secure!\n"
                f"It's needed to decrypt your coordinate data.",
                parse_mode='Markdown'
            )
        except ValueError as e:
            await update.message.reply_text(str(e))

    async def import_keys_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Import user's encryption keys"""
        user_id = update.effective_user.id
        if not context.args:
            await update.message.reply_text("Please provide your private key as an argument.")
            return

        private_key_pem = " ".join(context.args)
        try:
            self.location_logger.import_user_keys(user_id, private_key_pem)
            await update.message.reply_text("✅ Keys successfully imported!")
        except Exception as e:
            await update.message.reply_text(f"Failed to import keys: {str(e)}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        help_text = """
🌍 **GPS Bikera MERA Distribution Bot**
🔒 **Privacy-Preserving Location Mining**

/start - Initialize your encryption keys
/setaddress - Set your Solana address
/location - Start location sharing process
/status - Check current interval status
/rewards - View your mining statistics and rewards
/blockchain - View blockchain statistics
/help - Show this help message
/cancel - cancel inputs

Blockchain data:
/download_blockchain - Download complete blockchain data
/download_coordinates - Download your logged coordinates

Key Management:
/export_keys - Export your encryption keys
/import_keys - Import existing encryption keys

📱 Share your location to participate!
You can update your location multiple times during an active interval

⛏️ Mining Process:
• First two intervals collect initial data
• Winners determined from third interval onward
• Each interval lasts 10 minutes
• Target distance generated randomly (0.1-10km)
• Closest to target distance wins the interval
• Winners receive rewards to Solana address

🔒 Security:
• All location data is encrypted
• RSA encryption for coordinates
• Blockchain-based logging
• Automatic blockchain persistence

💾 Data Recovery:
• Blockchain automatically saved after each block
• User data persisted across restarts
• Your private keys decrypt your coordinate history
• Backup files created for safety
"""
        await update.message.reply_text(help_text)
