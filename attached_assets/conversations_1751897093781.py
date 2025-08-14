"""
Telegram bot conversation handlers
"""
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from config.settings import WAITING_ADDRESS, WAITING_LOCATION

logger = logging.getLogger(__name__)

class ConversationHandlers:
    """Collection of conversation handlers for the Telegram bot"""
    
    def __init__(self, location_logger):
        self.location_logger = location_logger

    # Address Setting Conversation
    async def start_address_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the address setting conversation"""
        await update.message.reply_text(
            "Please enter your Solana address:"
        )
        return WAITING_ADDRESS

    async def handle_address_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle address input"""
        user_id = update.effective_user.id
        address = update.message.text.strip()

        # Basic length check only (between 32-44 characters)
        if len(address) < 32 or len(address) > 44:
            await update.message.reply_text("Address should be between 32 and 44 characters. Please try again with /setaddress")
            return ConversationHandler.END

        self.location_logger.user_addresses[user_id] = address
        
        # Save user data after address update
        self.location_logger.save_user_data()
        
        await update.message.reply_text(
            f"✅ Solana address set successfully!\n"
            f"Address: {address[:6]}...{address[-4:]}\n\n"
            f"You can now participate in GPS mining intervals.\n"
            f"Use /status to check current interval status."
        )
        return ConversationHandler.END

    async def cancel_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel address setting"""
        await update.message.reply_text("Address setting cancelled. You can try again with /setaddress")
        return ConversationHandler.END

    # Location Sharing Conversation
    async def start_location_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the location sharing conversation"""
        user_id = update.effective_user.id
        
        # Check if user has keys
        if user_id not in self.location_logger.user_keys:
            await update.message.reply_text("Please use /start first to generate your keys.")
            return ConversationHandler.END
            
        # Check if user has set address
        if user_id not in self.location_logger.user_addresses:
            await update.message.reply_text("Please set your Solana address using /setaddress first.")
            return ConversationHandler.END
            
        # Check if interval is active
        if not self.location_logger.current_interval.is_active:
            await update.message.reply_text("No active interval. Please wait for the next interval to start.")
            return ConversationHandler.END

        keyboard = [[KeyboardButton(text="Share Location", request_location=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

        await update.message.reply_text(
            "Please share your location using the button below 📍\n\n"
            "You can do this by:\n"
            "1. Click the attachment (📎) or (+) icon\n"
            "2. Select 'Location'\n"
            "3. Share your current location\n\n"
            "Type /cancel to cancel location sharing.",
            reply_markup=reply_markup
        )
        return WAITING_LOCATION

    async def handle_location_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location input"""
        user_id = update.effective_user.id
        location = update.message.location
        
        if not location:
            await update.message.reply_text(
                "Please share a valid location or use /cancel to cancel.",
                reply_markup=ReplyKeyboardRemove()
            )
            return WAITING_LOCATION
            
        coordinates = (location.latitude, location.longitude)
        self.location_logger.current_interval.stage_coordinates(user_id, coordinates)
        
        time_remaining = self.location_logger.current_interval.get_time_remaining()
        participants = len(self.location_logger.current_interval.staged_coordinates)
        
        await update.message.reply_text(
            f"✅ Location successfully staged for this interval!\n"
            f"⏱️ Time remaining: {time_remaining} seconds\n"
            f"📍 Your coordinates will be finalized at interval end.\n"
            f"👥 Current participants: {participants}\n"
            f"🎯 Target distance: {self.location_logger.current_interval.target_distance:.2f}km\n\n"
            f"You can update your location again by using /location before the interval ends.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
        
    async def cancel_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel location sharing"""
        await update.message.reply_text(
            "Location sharing cancelled. You can try again with /location",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    def get_address_conversation_handler(self):
        """Get the address setting conversation handler"""
        return ConversationHandler(
            entry_points=[CommandHandler('setaddress', self.start_address_conversation)],
            states={
                WAITING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_address_input)]
            },
            fallbacks=[CommandHandler('cancel', self.cancel_address)]
        )

    def get_location_conversation_handler(self):
        """Get the location sharing conversation handler"""
        return ConversationHandler(
            entry_points=[CommandHandler('location', self.start_location_conversation)],
            states={
                WAITING_LOCATION: [
                    MessageHandler(filters.LOCATION, self.handle_location_input),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                 lambda u, c: u.message.reply_text("Please use the location share button or /cancel"))
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel_location)]
        )