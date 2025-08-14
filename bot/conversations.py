"""
Conversation handlers for Telegram bot with hybrid user identification
"""
import logging
import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from core.utils import validate_solana_address, format_solana_address
from config.settings import WAITING_ADDRESS, WAITING_LOCATION

logger = logging.getLogger(__name__)

class ConversationHandlers:
    """Manages conversation flows for user setup"""
    
    def __init__(self, location_logger):
        self.location_logger = location_logger

    def get_address_conversation_handler(self):
        """Create conversation handler for Solana address setup"""
        return ConversationHandler(
            entry_points=[CommandHandler('address', self.start_address_conversation)],
            states={
                WAITING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_address_input)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)]
        )

    def get_location_conversation_handler(self):
        """Create conversation handler for location submission"""
        return ConversationHandler(
            entry_points=[CommandHandler('location', self.start_location_conversation)],
            states={
                WAITING_LOCATION: [MessageHandler(filters.LOCATION, self.handle_location_input)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)]
        )

    async def start_address_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start Solana address setup conversation"""
        user_id = update.effective_user.id
        
        # Check if user already has an address
        current_address = self.location_logger.crypto_manager.get_solana_address(user_id)
        
        if current_address:
            message = (
                f"💰 **Current Solana Address**\n\n"
                f"Your current address: `{format_solana_address(current_address)}`\n\n"
                f"**Do you want to change it?**\n"
                f"Send your new Solana address, or /cancel to keep the current one."
            )
        else:
            message = (
                "💰 **Set Your Solana Address**\n\n"
                "Please send your Solana address to receive mining rewards.\n\n"
                "**Format:** Base58 encoded address (32-44 characters)\n"
                "**Example:** `FsHRFn2xr1X2QFMdrdqAd63uqAY7aAEnF198XRaptjen`\n\n"
                "Send your address or /cancel to abort."
            )
        
        await update.message.reply_text(message, parse_mode='Markdown')
        return WAITING_ADDRESS

    async def handle_address_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Solana address input"""
        user_id = update.effective_user.id
        address = update.message.text.strip()
        
        # Validate address format
        if not validate_solana_address(address):
            await update.message.reply_text(
                "❌ **Invalid Solana Address**\n\n"
                "Please enter a valid Solana address (32-44 characters, Base58 encoded).\n\n"
                "Try again or /cancel to abort."
            )
            return WAITING_ADDRESS
        
        try:
            # Check if address is already in use by another Telegram user
            existing_users = []
            for tel_id, sol_addr in self.location_logger.crypto_manager.solana_mappings.items():
                if sol_addr == address and tel_id != user_id:
                    existing_users.append(tel_id)
            
            # Store the address
            self.location_logger.crypto_manager.set_solana_address(user_id, address)
            
            # Save to persistent storage
            await self.location_logger.save_user_data()
            
            # Generate keys if user doesn't have them
            if user_id not in self.location_logger.crypto_manager.telegram_user_keys:
                self.location_logger.crypto_manager.generate_user_keys(user_id)
            
            success_message = (
                f"✅ **Solana Address Set Successfully!**\n\n"
                f"💰 **Address:** `{format_solana_address(address)}`\n"
                f"🔑 **Telegram ID:** `{user_id}`\n\n"
            )
            
            if existing_users:
                success_message += (
                    f"ℹ️ **Note:** This address is also used by {len(existing_users)} other Telegram user(s).\n"
                    f"Rewards will be shared to the same address, but private keys remain separate.\n\n"
                )
            
            success_message += (
                "🎯 **You can now participate in mining!**\n"
                "Use `/location` to submit your GPS coordinates during mining intervals."
            )
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error setting address for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ **Error Setting Address**\n\n"
                "There was an error saving your address. Please try again later."
            )
            return ConversationHandler.END

    async def start_location_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start location submission conversation"""
        user_id = update.effective_user.id
        
        # Check if user has set Solana address
        solana_address = self.location_logger.crypto_manager.get_solana_address(user_id)
        if not solana_address:
            await update.message.reply_text(
                "⚠️ **Please set your Solana address first!**\n\n"
                "Use `/address` to set your Solana address before submitting coordinates."
            )
            return ConversationHandler.END
        
        # Check if interval is active
        if not self.location_logger.current_interval or not self.location_logger.current_interval.is_active:
            await update.message.reply_text(
                "⏸️ **No active mining interval**\n\n"
                "Please wait for the next mining interval to start.\n"
                "Use `/status` to check the current interval status."
            )
            return ConversationHandler.END
        
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
            return ConversationHandler.END
        
        # Create location request keyboard
        keyboard = [["📍 Share Location"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        time_remaining = self.location_logger.current_interval.get_time_remaining()
        target_distance = self.location_logger.current_interval.target_distance
        
        message = (
            f"📍 **Submit Your Location**\n\n"
            f"⏱️ **Time Remaining:** {time_remaining // 60}m {time_remaining % 60}s\n"
            f"🎯 **Target Distance:** {target_distance:.3f}km\n"
            f"💰 **Rewards to:** `{format_solana_address(solana_address)}`\n\n"
            f"🔒 **Privacy Protection:**\n"
            f"• Your real coordinates are never stored\n"
            f"• All GPS data is obfuscated for privacy\n"
            f"• Distance relationships are preserved for mining\n\n"
            f"Tap '📍 Share Location' below or send your location manually.\n"
            f"Use /cancel to abort."
        )
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        return WAITING_LOCATION

    async def handle_location_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location input"""
        user_id = update.effective_user.id
        location = update.message.location
        
        try:
            # Remove keyboard
            await update.message.reply_text(
                "📍 Processing your location...",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Get user's Solana address
            solana_address = self.location_logger.crypto_manager.get_solana_address(user_id)
            
            # Stage coordinates
            coordinates = (location.latitude, location.longitude)
            self.location_logger.current_interval.stage_coordinates(
                user_id, coordinates, solana_address
            )
            
            time_remaining = self.location_logger.current_interval.get_time_remaining()
            participants = len(self.location_logger.current_interval.staged_coordinates)
            
            success_message = (
                f"✅ **Location Submitted Successfully!**\n\n"
                f"🔒 **Privacy:** Your coordinates have been obfuscated for privacy protection\n"
                f"⏱️ **Time Remaining:** {time_remaining // 60}m {time_remaining % 60}s\n"
                f"👥 **Current Participants:** {participants}\n"
                f"💰 **Rewards Address:** `{format_solana_address(solana_address)}`\n\n"
                f"🏆 **Good luck in the mining competition!**\n"
                f"Use `/status` to check the interval progress."
            )
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error handling location for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ **Error Processing Location**\n\n"
                "There was an error processing your location. Please try again later."
            )
            return ConversationHandler.END

    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current conversation"""
        await update.message.reply_text(
            "❌ **Operation Cancelled**\n\n"
            "The current operation has been cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def handle_document_import(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document import for private keys"""
        user_id = update.effective_user.id
        
        try:
            # Get the document
            document = update.message.document
            
            # Check file type
            if not document.file_name.endswith('.json'):
                await update.message.reply_text(
                    "❌ **Invalid File Type**\n\n"
                    "Please send a JSON file containing your private keys."
                )
                return
            
            # Download and process file
            file = await context.bot.get_file(document.file_id)
            file_content = await file.download_as_bytearray()
            
            try:
                import_data = json.loads(file_content.decode('utf-8'))
            except json.JSONDecodeError:
                await update.message.reply_text(
                    "❌ **Invalid JSON Format**\n\n"
                    "The file contains invalid JSON data."
                )
                return
            
            # Validate required fields
            if 'private_key' not in import_data:
                await update.message.reply_text(
                    "❌ **Missing Private Key**\n\n"
                    "The file must contain a 'private_key' field."
                )
                return
            
            # Import keys
            private_key = import_data['private_key']
            solana_address = import_data.get('solana_address')
            
            self.location_logger.crypto_manager.import_user_keys(
                user_id, private_key, solana_address
            )
            
            # Save data
            await self.location_logger.save_user_data()
            
            success_message = (
                f"✅ **Keys Imported Successfully!**\n\n"
                f"🔑 **Telegram ID:** `{user_id}`\n"
            )
            
            if solana_address:
                success_message += f"💰 **Solana Address:** `{format_solana_address(solana_address)}`\n"
            
            success_message += (
                "\n🎯 **You can now participate in mining!**\n"
                "Use `/location` to submit your GPS coordinates during mining intervals."
            )
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error importing keys for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ **Error Importing Keys**\n\n"
                "There was an error importing your keys. Please check the file format and try again."
            )
