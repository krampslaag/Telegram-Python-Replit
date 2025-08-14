"""
Telegram bot command handlers with hybrid user identification
"""
import logging
import json
import time
from datetime import datetime
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from core.utils import format_solana_address, format_time_remaining, format_distance, validate_solana_address
from storage.location_logger import LocationLogger

logger = logging.getLogger(__name__)

class BotHandlers:
    """Telegram bot command handlers with hybrid user identification"""
    
    def __init__(self, location_logger: LocationLogger):
        self.location_logger = location_logger

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        logger.info(f"📱 User {user_id} ({username}) started the bot")
        
        # Generate encryption keys for this Telegram user
        try:
            public_key = self.location_logger.crypto_manager.generate_user_keys(user_id)
            logger.info(f"🔑 Generated encryption keys for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to generate keys for user {user_id}: {e}")
        
        welcome_message = (
            "🌟 **Welcome to Bikera Mining Bot!** 🌟\n\n"
            "This bot uses GPS-based cryptocurrency mining with privacy protection.\n\n"
            "🔐 **Hybrid User System:**\n"
            "• Your Telegram ID is used for private keys and encryption\n"
            "• Your Solana address is used for rewards and blockchain records\n"
            "• This allows secure cross-session data continuity\n\n"
            "🚀 **Getting Started:**\n"
            "1. Set your Solana address with `/address`\n"
            "2. Submit your location with `/location`\n"
            "3. Wait for mining intervals (10 minutes each)\n"
            "4. Check your rewards with `/rewards`\n\n"
            "📍 **Privacy Protection:**\n"
            "• Your real coordinates are never stored\n"
            "• All GPS data is obfuscated while preserving distances\n"
            "• Private keys remain isolated per Telegram user\n\n"
            "💡 Use `/help` to see all available commands!"
        )
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        help_text = (
            "🤖 **Bikera Mining Bot Commands:**\n\n"
            "**Account Management:**\n"
            "`/start` - Initialize your account\n"
            "`/address` - Set your Solana address for rewards\n"
            "`/export_keys` - Export your private keys\n"
            "`/import_keys` - Import private keys\n\n"
            "**Mining:**\n"
            "`/location` - Submit your GPS coordinates\n"
            "`/status` - Check current mining interval\n"
            "`/rewards` - View your mining statistics\n\n"
            "**Data & Stats:**\n"
            "`/blockchain` - View blockchain statistics\n"
            "`/download_blockchain` - Export blockchain data\n"
            "`/download_coordinates` - Export coordinate data\n\n"
            "**How it works:**\n"
            "1. Every 10 minutes, a target distance is randomly generated\n"
            "2. Users submit GPS coordinates during the interval\n"
            "3. The user who traveled closest to the target distance wins\n"
            "4. Winners receive rewards to their Solana address\n"
            "5. All coordinates are obfuscated for privacy\n\n"
            "🔒 **Privacy:** Your real coordinates are never stored or shared!"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def interval_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current mining interval status"""
        user_id = update.effective_user.id
        
        try:
            current_interval = self.location_logger.current_interval
            
            if not current_interval or not current_interval.is_active:
                block_count = len(self.location_logger.blockchain.chain) - 1
                status_text = (
                    "⏸️ **Mining Status: Inactive**\n\n"
                    "No active mining interval. Please wait for the next interval to start.\n\n"
                    f"📊 **Current Statistics:**\n"
                    f"• Current Interval: {self.location_logger.interval_count}\n"
                    f"• Total Blocks: {block_count}\n"
                    f"• Blocks until reset: {100 - (self.location_logger.interval_count % 100)}\n"
                )
            else:
                time_remaining = current_interval.get_time_remaining()
                participants = len(current_interval.staged_coordinates)
                block_count = len(self.location_logger.blockchain.chain) - 1
                
                status_text = (
                    f"⏰ **Active Mining Session**\n\n"
                    f"📊 **Progress:**\n"
                    f"• Interval: #{self.location_logger.interval_count}\n"
                    f"• Block: #{block_count + 1} (mining in progress)\n"
                    f"• Blocks until reset: {100 - (self.location_logger.interval_count % 100)}\n\n"
                    f"🎯 **Target Distance:** {format_distance(current_interval.target_distance)}\n"
                    f"⏱️ **Time Remaining:** {format_time_remaining(time_remaining)}\n"
                    f"👥 **Participants:** {participants}\n"
                    f"🔒 **Privacy:** All coordinates are obfuscated\n\n"
                    f"📍 Use `/location` to submit your GPS coordinates!"
                )
                
                # Check if user has already participated
                user_solana = self.location_logger.crypto_manager.get_solana_address(user_id)
                if user_solana:
                    # Check if user has participated in current interval
                    user_participated = any(
                        coord.user_id_hash for coord in current_interval.staged_coordinates.values()
                        if current_interval.get_real_user_id(coord.user_id_hash) == user_id
                    )
                    
                    if user_participated:
                        status_text += "\n✅ **You have already participated in this interval!**"
                    else:
                        status_text += "\n📍 **You haven't participated yet - submit your location!**"
                else:
                    status_text += "\n⚠️ **Please set your Solana address first with `/address`**"
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting interval status for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ Error getting interval status. Please try again later.",
                parse_mode='Markdown'
            )

    async def get_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user mining statistics"""
        user_id = update.effective_user.id
        
        try:
            # Get user's Solana address
            solana_address = self.location_logger.crypto_manager.get_solana_address(user_id)
            
            if not solana_address:
                await update.message.reply_text(
                    "⚠️ **No Solana address found!**\n\n"
                    "Please set your Solana address first with `/address` to view your rewards.",
                    parse_mode='Markdown'
                )
                return
            
            # Get blockchain stats for this Solana address
            blockchain_stats = self.location_logger.blockchain.get_stats()
            user_rewards = self.location_logger.blockchain.get_user_rewards(solana_address)
            
            # Calculate additional stats
            total_participants = len(self.location_logger.user_addresses)
            win_rate = (user_rewards['blocks_mined'] / max(1, blockchain_stats['total_blocks'] - 1)) * 100
            
            stats_text = (
                f"📊 **Your Mining Statistics**\n\n"
                f"💰 **Rewards:** {user_rewards['total_rewards']:.2f} IMERA\n"
                f"⛏️ **Blocks Mined:** {user_rewards['blocks_mined']}\n"
                f"🎯 **Win Rate:** {win_rate:.1f}%\n"
                f"📅 **First Block:** {datetime.fromtimestamp(user_rewards['first_block_time']).strftime('%Y-%m-%d %H:%M') if user_rewards['first_block_time'] else 'N/A'}\n"
                f"🕐 **Last Block:** {datetime.fromtimestamp(user_rewards['last_block_time']).strftime('%Y-%m-%d %H:%M') if user_rewards['last_block_time'] else 'N/A'}\n\n"
                f"🔗 **Your Address:** `{format_solana_address(solana_address)}`\n"
                f"📱 **Telegram ID:** `{user_id}`\n\n"
                f"🌐 **Global Stats:**\n"
                f"• Total Blocks: {blockchain_stats['total_blocks'] - 1}\n"
                f"• Total Participants: {total_participants}\n"
                f"• Total Rewards Distributed: {blockchain_stats['total_rewards']:.2f} IMERA\n"
            )
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ Error retrieving statistics. Please try again later.",
                parse_mode='Markdown'
            )

    async def blockchain_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show blockchain statistics"""
        try:
            stats = self.location_logger.blockchain.get_stats()
            crypto_stats = self.location_logger.crypto_manager.get_user_stats()
            
            stats_text = (
                f"⛓️ **Blockchain Statistics**\n\n"
                f"📊 **Chain Info:**\n"
                f"• Total Blocks: {stats['total_blocks']}\n"
                f"• Chain Height: {stats['chain_height']}\n"
                f"• Genesis Time: {datetime.fromtimestamp(stats['genesis_time']).strftime('%Y-%m-%d %H:%M')}\n"
                f"• Last Block: {datetime.fromtimestamp(stats['last_block_time']).strftime('%Y-%m-%d %H:%M') if stats['last_block_time'] else 'N/A'}\n\n"
                f"💰 **Rewards:**\n"
                f"• Total Distributed: {stats['total_rewards']:.2f} IMERA\n"
                f"• Unique Miners: {stats['unique_miners']}\n\n"
                f"👥 **User Statistics:**\n"
                f"• Telegram Users: {crypto_stats['total_telegram_users']}\n"
                f"• Solana Addresses: {crypto_stats['total_solana_addresses']}\n"
                f"• Active Mappings: {crypto_stats['unique_mappings']}\n\n"
                f"🔄 **Current Interval:** {self.location_logger.interval_count}\n"
                f"🔒 **Privacy:** All coordinates are obfuscated for user protection"
            )
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting blockchain stats: {e}")
            await update.message.reply_text(
                "❌ Error retrieving blockchain statistics. Please try again later."
            )

    async def download_blockchain(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export blockchain data"""
        user_id = update.effective_user.id
        
        try:
            # Export blockchain data
            blockchain_data = await self.location_logger.blockchain.export_chain()
            
            # Create XML format for privacy
            xml_data = self._create_blockchain_xml(blockchain_data)
            
            # Send as file
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=xml_data.encode('utf-8'),
                filename=f"blockchain_export_{int(time.time())}.xml",
                caption="📊 **Blockchain Export**\n\nPrivacy-protected blockchain data in XML format."
            )
            
        except Exception as e:
            logger.error(f"Error exporting blockchain for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ Error exporting blockchain data. Please try again later."
            )

    async def download_coordinates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export coordinate data (obfuscated)"""
        user_id = update.effective_user.id
        
        try:
            # Get user's participation data
            user_data = {
                'user_id': user_id,
                'solana_address': self.location_logger.crypto_manager.get_solana_address(user_id),
                'intervals_participated': [],
                'export_time': datetime.now().isoformat(),
                'privacy_note': 'All coordinates are obfuscated for privacy protection'
            }
            
            # Add current interval if user participated
            if (self.location_logger.current_interval and 
                self.location_logger.current_interval.staged_coordinates):
                
                user_hash = None
                for hash_id, coord in self.location_logger.current_interval.staged_coordinates.items():
                    if self.location_logger.current_interval.get_real_user_id(hash_id) == user_id:
                        user_hash = hash_id
                        break
                
                if user_hash:
                    user_data['intervals_participated'].append({
                        'interval_number': self.location_logger.current_interval.interval_number,
                        'obfuscated_coordinates': self.location_logger.current_interval.staged_coordinates[user_hash].to_dict(),
                        'timestamp': self.location_logger.current_interval.staged_coordinates[user_hash].timestamp
                    })
            
            # Convert to JSON
            json_data = json.dumps(user_data, indent=2)
            
            # Send as file
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=json_data.encode('utf-8'),
                filename=f"coordinates_export_{user_id}_{int(time.time())}.json",
                caption="📍 **Coordinate Export**\n\nYour obfuscated coordinate data for privacy protection."
            )
            
        except Exception as e:
            logger.error(f"Error exporting coordinates for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ Error exporting coordinate data. Please try again later."
            )

    async def export_keys_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export user's private keys"""
        user_id = update.effective_user.id
        
        try:
            keys_data = self.location_logger.crypto_manager.export_user_keys(user_id)
            
            # Create export data
            export_data = {
                'telegram_user_id': user_id,
                'solana_address': keys_data['solana_address'],
                'private_key': keys_data['private_key'],
                'public_key': keys_data['public_key'],
                'export_time': datetime.now().isoformat(),
                'warning': 'Keep your private keys secure! Do not share them with anyone.'
            }
            
            json_data = json.dumps(export_data, indent=2)
            
            # Send as file with warning
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=json_data.encode('utf-8'),
                filename=f"keys_export_{user_id}_{int(time.time())}.json",
                caption=(
                    "🔑 **Private Keys Export**\n\n"
                    "⚠️ **SECURITY WARNING:**\n"
                    "• Keep these keys secure and private\n"
                    "• Do not share with anyone\n"
                    "• Store in a safe location\n"
                    "• Delete this file after backing up safely"
                )
            )
            
        except Exception as e:
            logger.error(f"Error exporting keys for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ Error exporting keys. Please try again later."
            )

    async def import_keys_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Import user's private keys"""
        await update.message.reply_text(
            "🔑 **Import Private Keys**\n\n"
            "To import your private keys, please send a JSON file with the following format:\n\n"
            "```json\n"
            "{\n"
            '  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----",\n'
            '  "solana_address": "your_solana_address_here"\n'
            "}\n"
            "```\n\n"
            "Send the file as a document attachment."
        )

    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location message"""
        user_id = update.effective_user.id
        location = update.message.location
        
        try:
            # Check if user has set Solana address
            solana_address = self.location_logger.crypto_manager.get_solana_address(user_id)
            if not solana_address:
                await update.message.reply_text(
                    "⚠️ **Please set your Solana address first!**\n\n"
                    "Use `/address` to set your Solana address before submitting coordinates."
                )
                return
            
            # Check if interval is active
            if not self.location_logger.current_interval or not self.location_logger.current_interval.is_active:
                await update.message.reply_text(
                    "⏸️ **No active mining interval**\n\n"
                    "Please wait for the next mining interval to start."
                )
                return
            
            # Check if user already participated
            user_participated = any(
                coord.user_id_hash for coord in self.location_logger.current_interval.staged_coordinates.values()
                if self.location_logger.current_interval.get_real_user_id(coord.user_id_hash) == user_id
            )
            
            if user_participated:
                await update.message.reply_text(
                    "✅ **Already participated!**\n\n"
                    "You have already submitted coordinates for this interval."
                )
                return
            
            # Stage coordinates
            coordinates = (location.latitude, location.longitude)
            self.location_logger.current_interval.stage_coordinates(
                user_id, coordinates, solana_address
            )
            
            time_remaining = self.location_logger.current_interval.get_time_remaining()
            
            await update.message.reply_text(
                f"📍 **Coordinates Submitted!**\n\n"
                f"🔒 Your GPS coordinates have been obfuscated and staged for mining.\n"
                f"⏱️ **Time Remaining:** {format_time_remaining(time_remaining)}\n"
                f"💰 **Rewards Address:** `{format_solana_address(solana_address)}`\n\n"
                f"Good luck! 🍀"
            )
            
        except Exception as e:
            logger.error(f"Error handling location for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ Error processing your location. Please try again later."
            )

    def _create_blockchain_xml(self, blockchain_data):
        """Create XML representation of blockchain data"""
        xml_lines = ['<?xml version="1.0" encoding="utf-8"?>']
        xml_lines.append('<blockchain>')
        
        # Add metadata
        xml_lines.append('  <metadata>')
        xml_lines.append(f'    <total_blocks>{len(blockchain_data)}</total_blocks>')
        xml_lines.append(f'    <last_update>{datetime.now().isoformat()}</last_update>')
        xml_lines.append('    <privacy_protection>Coordinates are obfuscated for user privacy</privacy_protection>')
        xml_lines.append('  </metadata>')
        
        # Add blocks
        xml_lines.append('  <blocks>')
        for block in blockchain_data:
            xml_lines.append('    <block>')
            xml_lines.append(f'      <timestamp>{datetime.fromtimestamp(block["timestamp"]).isoformat()}</timestamp>')
            xml_lines.append(f'      <hash>{block["hash"]}</hash>')
            xml_lines.append(f'      <previous_hash>{block["previous_hash"]}</previous_hash>')
            
            if block.get('miner_address'):
                xml_lines.append(f'      <miner_address>{format_solana_address(block["miner_address"])}</miner_address>')
            if block.get('reward'):
                xml_lines.append(f'      <reward>{block["reward"]}</reward>')
            if block.get('target_distance'):
                xml_lines.append(f'      <target_distance>{block["target_distance"]:.3f}</target_distance>')
            if block.get('travel_distance'):
                xml_lines.append(f'      <travel_distance>{block["travel_distance"]:.3f}</travel_distance>')
            
            xml_lines.append('    </block>')
        xml_lines.append('  </blocks>')
        
        xml_lines.append('</blockchain>')
        
        return '\n'.join(xml_lines)
