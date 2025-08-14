import logging
import asyncio
from telegram import Update
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext import ApplicationBuilder
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import json
import time
import hashlib
import csv
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import datetime
import random
from math import radians, sin, cos, sqrt, atan2
import asyncio
import os
from dotenv import load_dotenv
import signal

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WAITING_ADDRESS = 1
WAITING_LOCATION = 1

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def calculate_distance(coord1, coord2):
    """Calculate the distance between two coordinates using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1 = map(radians, coord1)
    lat2, lon2 = map(radians, coord2)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance

def calculate_travel_distance(start_coords, end_coords):
    """Calculate the distance traveled between two coordinate pairs"""
    return calculate_distance(start_coords, end_coords)

class Block:
    def __init__(self, timestamp, data, previous_hash, target_distance=None, 
                 winner_id=None, travel_distance=None, miner_address=None):
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.target_distance = target_distance
        self.winner_id = winner_id
        self.travel_distance = travel_distance
        self.miner_address = miner_address
        self.hash = self.calculate_hash()
        self.reward = 1.0

    def calculate_hash(self):
        hash_string = f"{self.timestamp}{self.data}{self.previous_hash}{self.target_distance}"
        return hashlib.sha256(hash_string.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        
    def create_genesis_block(self):
        return Block(time.time(), "Genesis Block", "0")
        
    def add_block(self, data, target_distance, winner_id, travel_distance, miner_address):
        previous_block = self.chain[-1]
        new_block = Block(
            time.time(),
            data,
            previous_block.hash,
            target_distance,
            winner_id,
            travel_distance,
            miner_address
        )
        self.chain.append(new_block)
        return new_block

    def verify_chain(self):
        """Verify the integrity of the blockchain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            if current.previous_hash != previous.hash:
                return False
            if current.hash != current.calculate_hash():
                return False
        return True

class MiningInterval:
    def __init__(self):
        self.start_time = None
        self.is_active = False
        self.staged_coordinates = {}  # Dict of user_id: {latest_coords, timestamp}
        self.finalized_coordinates = {}  # Dict of user_id: {start_coords, end_coords}
        self.target_distance = None

    def start(self):
        self.start_time = time.time()
        self.is_active = True
        self.target_distance = random.uniform(0.1, 10.0)  # Random target distance in km
        return self.target_distance

    def stage_coordinates(self, user_id, coordinates):
        self.staged_coordinates[user_id] = {
            'coords': coordinates,
            'timestamp': time.time()
        }

    def finalize_interval(self):
        """Finalize coordinates for all users at interval end"""
        self.is_active = False
        
        for user_id in self.staged_coordinates:
            coords_history = self.staged_coordinates[user_id]
            self.finalized_coordinates[user_id] = {
                'start_coords': coords_history['coords'],
                'end_coords': coords_history['coords']
            }
        
        self.staged_coordinates = {}  # Clear staged coordinates
        return self.finalized_coordinates

    def get_time_remaining(self):
        """Get remaining time in current interval"""
        if not self.is_active:
            return 0
        elapsed = time.time() - self.start_time
        remaining = max(0, 600 - elapsed)  # 600 seconds = 10 minutes
        return int(remaining)

class LocationLogger:
    def __init__(self):
        self.blockchain = Blockchain()
        self.user_keys = {}
        self.user_addresses = {}
        self.current_interval = MiningInterval()
        self.previous_interval = None
        self.interval_count = 0
        self.coordinate_log = {}
        self.ensure_data_directory()

    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        if not os.path.exists('data'):
            os.makedirs('data')
        if not os.path.exists('data/user_logs'):
            os.makedirs('data/user_logs')

    def generate_user_keys(self, user_id):
        """Generate RSA key pair for a user"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        self.user_keys[user_id] = {
            'private': private_key,
            'public': public_key
        }
        
        return public_key

    def encrypt_coordinates(self, public_key, coordinates):
        """Encrypt coordinates using RSA"""
        coords_bytes = json.dumps(coordinates).encode()
        encrypted = public_key.encrypt(
            coords_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return encrypted

    def log_user_coordinates(self, user_id, coordinates, timestamp):
        """Log encrypted coordinates for a user"""
        if user_id not in self.coordinate_log:
            self.coordinate_log[user_id] = []
        
        encrypted_coords = self.encrypt_coordinates(
            self.user_keys[user_id]['public'],
            coordinates
        )
        
        log_entry = {
            'timestamp': timestamp,
            'encrypted_coordinates': encrypted_coords.hex(),
        }
        
        self.coordinate_log[user_id].append(log_entry)
        self.save_user_log(user_id)

    def save_user_log(self, user_id):
        """Save user's coordinate log to a file"""
        filename = f"data/user_logs/user_{user_id}_coordinates.json"
        with open(filename, 'w') as f:
            json.dump(self.coordinate_log[user_id], f, indent=2)

    async def start_mining_intervals(self):
        try:
            while True:
                self.interval_count += 1
                target_distance = self.current_interval.start()
                logging.info(f"Starting interval {self.interval_count}")

                try:
                    await asyncio.sleep(600)  # 10 minutes
                except asyncio.CancelledError:
                    logging.info("Mining intervals cancelled")
                    break

                current_coords = self.current_interval.finalize_interval()

                if self.previous_interval and self.interval_count > 2:
                    winner = self.determine_winner(self.previous_interval, current_coords, target_distance)
                    if winner:
                        self.process_winner(winner, target_distance)

                self.previous_interval = current_coords
                self.current_interval = MiningInterval()
        except Exception as e:
            logging.error(f"Error in mining intervals: {e}")

    def determine_winner(self, previous_coords, current_coords, target_distance):
        winner = None
        closest_difference = float('inf')
        
        for user_id in previous_coords:
            if user_id in current_coords:
                travel_distance = calculate_travel_distance(
                    previous_coords[user_id]['end_coords'],
                    current_coords[user_id]['end_coords']
                )
                
                difference = abs(travel_distance - target_distance)
                if difference < closest_difference:
                    closest_difference = difference
                    winner = {
                        'user_id': user_id,
                        'travel_distance': travel_distance,
                        'start_coords': previous_coords[user_id]['end_coords'],
                        'end_coords': current_coords[user_id]['end_coords']
                    }
        
        return winner

    def process_winner(self, winner, target_distance):
        if winner['user_id'] not in self.user_addresses:
            logging.warning(f"Winner {winner['user_id']} has no registered Solana address")
            return

        encrypted_start = self.encrypt_coordinates(
            self.user_keys[winner['user_id']]['public'],
            winner['start_coords']
        )
        encrypted_end = self.encrypt_coordinates(
            self.user_keys[winner['user_id']]['public'],
            winner['end_coords']
        )

        block_data = json.dumps({
            'user_id': winner['user_id'],
            'encrypted_start': encrypted_start.hex(),
            'encrypted_end': encrypted_end.hex(),
            'timestamp': time.time()
        })

        self.blockchain.add_block(
            block_data,
            target_distance,
            winner['user_id'],
            winner['travel_distance'],
            self.user_addresses[winner['user_id']]
        )

        self.save_to_csv()
        self.save_to_xml()
        self.save_mining_rewards()

    def save_to_csv(self, filename="data/coordinates.csv"):
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Block Number', 'Timestamp', 'Target Distance', 
                           'Winner ID', 'Travel Distance', 'Miner Address', 'Block Hash'])
            for i, block in enumerate(self.blockchain.chain[1:], 1):
                writer.writerow([
                    i,
                    datetime.datetime.fromtimestamp(block.timestamp),
                    block.target_distance,
                    block.winner_id,
                    block.travel_distance,
                    block.miner_address,
                    block.hash
                ])

    def save_mining_rewards(self, filename="data/mining_rewards.csv"):
        with open(filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Miner Address', 'Total Rewards'])
            
            rewards = {}
            for block in self.blockchain.chain[1:]:
                if block.miner_address:
                    rewards[block.miner_address] = rewards.get(block.miner_address, 0) + block.reward
            
            for address, reward in rewards.items():
                writer.writerow([address, reward])

    def export_blockchain_xml(self):
        """Export blockchain data to XML file"""
        root = ET.Element("blockchain")
        
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "total_blocks").text = str(len(self.blockchain.chain))
        ET.SubElement(metadata, "last_update").text = datetime.datetime.now().isoformat()
        
        blocks = ET.SubElement(root, "blocks")
        for block in self.blockchain.chain:
            block_elem = ET.SubElement(blocks, "block")
            ET.SubElement(block_elem, "timestamp").text = datetime.datetime.fromtimestamp(block.timestamp).isoformat()
            ET.SubElement(block_elem, "hash").text = block.hash
            ET.SubElement(block_elem, "previous_hash").text = block.previous_hash
            if block.target_distance:
                ET.SubElement(block_elem, "target_distance").text = str(block.target_distance)
            if block.travel_distance:
                ET.SubElement(block_elem, "travel_distance").text = str(block.travel_distance)
            if block.winner_id:
                ET.SubElement(block_elem, "winner_id").text = str(block.winner_id)
            if block.miner_address:
                ET.SubElement(block_elem, "miner_address").text = str(block.miner_address)
            
            if block.data and block.data != "Genesis Block":
                try:
                    data_dict = json.loads(block.data)
                    data_elem = ET.SubElement(block_elem, "data")
                    for key, value in data_dict.items():
                        ET.SubElement(data_elem, key).text = str(value)
                except json.JSONDecodeError:
                    ET.SubElement(block_elem, "data").text = block.data

        filepath = "data/blockchain_export.xml"
        tree = ET.ElementTree(root)
        tree.write(filepath, encoding='utf-8', xml_declaration=True)
        return filepath

    def get_user_stats(self, user_id):
        """Get statistics for a specific user"""
        wins = sum(1 for block in self.blockchain.chain if block.winner_id == user_id)
        total_rewards = sum(block.reward for block in self.blockchain.chain if block.winner_id == user_id)
        participated_intervals = self.interval_count
        
        return {
            'total_wins': wins,
            'total_rewards': total_rewards,
            'participated_intervals': participated_intervals
        }

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in logger.user_keys:
        public_key = logger.generate_user_keys(user_id)
        await update.message.reply_text(
            "Welcome to the GPS Bikera MERA distribution Bot!\n\n"
            "Your encryption keys have been generated.\n"
            "Please set your Solana address using /setaddress.\n\n"
            "Use /help to see all available commands."
        )
    else:
        await update.message.reply_text(
            "Welcome back!\n"
            "Your encryption keys are already set up.\n"
            "Use /help to see all available commands."
        )

async def interval_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if logger.current_interval.is_active:
        time_remaining = int(600 - (time.time() - logger.current_interval.start_time))
        participants = len(logger.current_interval.staged_coordinates)
        target = logger.current_interval.target_distance
        await update.message.reply_text(
            f"Active interval {logger.interval_count} in progress!\n"
            f"Time remaining: {time_remaining} seconds\n"
            f"Current participants: {participants}\n"
            f"First two intervals collect data only.\n"
            f"Winners determined from third interval onward."
        )
    else:
        await update.message.reply_text("No active interval. Next interval starting soon!")

async def start_address_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please enter your Solana address:"
    )
    return WAITING_ADDRESS

async def handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    address = update.message.text.strip()

    # Basic length check only (between 32-44 characters)
    if len(address) < 32 or len(address) > 44:
        await update.message.reply_text("Address should be between 32 and 44 characters. Please try again with /setaddress")
        return ConversationHandler.END

    logger.user_addresses[user_id] = address
    await update.message.reply_text(
        f"✅ Solana address set successfully!\n"
        f"Address: {address[:6]}...{address[-4:]}\n\n"
        f"You can now participate in GPS mining intervals.\n"
        f"Use /status to check current interval status."
    )
    return ConversationHandler.END

async def cancel_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Address setting cancelled. You can try again with /setaddress")
    return ConversationHandler.END

async def start_location_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if user has keys
    if user_id not in logger.user_keys:
        await update.message.reply_text("Please use /start first to generate your keys.")
        return ConversationHandler.END
        
    # Check if user has set address
    if user_id not in logger.user_addresses:
        await update.message.reply_text("Please set your Solana address using /setaddress first.")
        return ConversationHandler.END
        
    # Check if interval is active
    if not logger.current_interval.is_active:
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

async def handle_location_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    location = update.message.location
    if not location:
        await update.message.reply_text(
            "Please share a valid location or use /cancel to cancel.",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_LOCATION
    coordinates = (location.latitude, location.longitude)
    logger.current_interval.stage_coordinates(user_id, coordinates)
    time_remaining = int(600 - (time.time() - logger.current_interval.start_time))
    participants = len(logger.current_interval.staged_coordinates)  # Add this line
    await update.message.reply_text(
        f"✅ Location successfully staged for this interval!\n"
        f"⏱️ Time remaining: {time_remaining} seconds\n"
        f"📍 Your coordinates will be finalized at interval end.\n"
        f"👥 Current participants: {participants}\n"
        f"🎯 Target distance: {logger.current_interval.target_distance:.2f}km\n\n"
        f"You can update your location again by using /location before the interval ends.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
    
async def cancel_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Location sharing cancelled. You can try again with /location",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def download_blockchain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for downloading blockchain data"""
    try:
        filepath = logger.export_blockchain_xml()
        with open(filepath, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename="blockchain_export.xml",
                caption="Here's the current blockchain data in XML format."
            )
    except Exception as e:
        logging.error(f"Error exporting blockchain: {e}")
        await update.message.reply_text("Sorry, there was an error generating the blockchain export.")

async def download_coordinates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for downloading user's coordinates"""
    user_id = update.effective_user.id

    if user_id not in logger.user_keys:
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
                caption="Here are your logged coordinates (encrypted)."
            )
    except Exception as e:
        logging.error(f"Error sending coordinates file: {e}")
        await update.message.reply_text("Sorry, there was an error retrieving your coordinates.")

async def get_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for getting user statistics"""
    user_id = update.effective_user.id

    if user_id not in logger.user_keys:
        await update.message.reply_text("Please use /start first to generate your keys.")
        return

    stats = logger.get_user_stats(user_id)
    await update.message.reply_text(
        f"📊 Your Statistics:\n\n"
        f"🏆 Total Wins: {stats['total_wins']}\n"
        f"💰 Total Rewards: {stats['total_rewards']} MERA\n"
        f"🎯 Participated Intervals: {stats['participated_intervals']}\n\n"
        f"Use /download_coordinates to get your logged coordinates\n"
        f"Use /download_blockchain to get the complete blockchain data"
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    location = update.message.location

    if user_id not in logger.user_keys:
        await update.message.reply_text("Please use /start first to generate your keys.")
        return

    if user_id not in logger.user_addresses:
        await update.message.reply_text("Please set your Solana address using /setaddress first.")
        return

    if not logger.current_interval.is_active:
        await update.message.reply_text("No active interval. Please wait for the next interval to start.")
        return

    coordinates = (location.latitude, location.longitude)
    logger.current_interval.stage_coordinates(user_id, coordinates)

    time_remaining = int(600 - (time.time() - logger.current_interval.start_time))

    await update.message.reply_text(
        f"Location staged for this interval!\n"
        f"Time remaining: {time_remaining} seconds\n"
        f"Your coordinates will be finalized at interval end.\n"
        f"Target distance: {logger.current_interval.target_distance:.2f}km\n"
        f"You can update your location until the interval ends."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🌍 GPS Bikera MERA distribution Bot Commands:

/start - Initialize your encryption keys
/setaddress - Set your Solana address
/location - Start location sharing process
/status - Check current interval status
/rewards - View your mining statistics and rewards
/help - Show this help message
/download_blockchain - Download complete blockchain data
/download_coordinates - Download your logged coordinates
/cancel - cancel inputs

📱 Share your location to participate!
You can update your location multiple times during an active interval

⛏️ Mining Process:
• First two intervals collect initial data
• Winners determined from third interval onward
• Each interval lasts 10 minutes
• Target distance generated randomly (0.01-10km)
• Closest to target distance wins the interval
• Winners receive rewards to Solana address

🔒 Security:
• All location data is encrypted
• RSA encryption for coordinates
• Blockchain-based logging
"""
    await update.message.reply_text(help_text)
    
address_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('setaddress', start_address_conversation)],
    states={
        WAITING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address_input)]
    },
    fallbacks=[CommandHandler('cancel', cancel_address)]
)

location_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('location', start_location_conversation)],
    states={
        WAITING_LOCATION: [
            MessageHandler(filters.LOCATION, handle_location_input),
            MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text("Please use the location share button or /cancel"))
        ]
    },
    fallbacks=[CommandHandler('cancel', cancel_location)]
)

async def run_polling(application):
    """Run the bot polling in a separate coroutine"""
    await application.initialize()
    try:
        await application.start()
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        await application.stop()
        await application.shutdown()

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.app = ApplicationBuilder().token(token).build()
        self.mining_task = None
        self.stop_flag = asyncio.Event()

    async def mining_loop(self):
        while not self.stop_flag.is_set():
            try:
                logger.interval_count += 1
                target_distance = logger.current_interval.start()
                logging.info(f"Starting interval {logger.interval_count}")

                # Wait for either 10 minutes or stop signal
                try:
                    await asyncio.wait_for(self.stop_flag.wait(), timeout=600)
                except asyncio.TimeoutError:
                    pass

                if not self.stop_flag.is_set():
                    current_coords = logger.current_interval.finalize_interval()
                    if logger.previous_interval and logger.interval_count > 2:
                        winner = logger.determine_winner(logger.previous_interval, current_coords, target_distance)
                        if winner:
                            logger.process_winner(winner, target_distance)
                    logger.previous_interval = current_coords
                    logger.current_interval = MiningInterval()
            except Exception as e:
                logging.error(f"Mining error: {e}")
                if not self.stop_flag.is_set():
                    await asyncio.sleep(5)

    async def start(self):
        # Add handlers
        self.app.add_handler(CommandHandler("start", start))
        self.app.add_handler(CommandHandler("help", help_command))
        self.app.add_handler(address_conv_handler) 
        self.app.add_handler(location_conv_handler)
        self.app.add_handler(CommandHandler("status", interval_status))
        self.app.add_handler(CommandHandler("rewards", get_stats))
        self.app.add_handler(CommandHandler("download_blockchain", download_blockchain))
        self.app.add_handler(CommandHandler("download_coordinates", download_coordinates))
        self.app.add_handler(MessageHandler(filters.LOCATION, handle_location))

        # Start mining in background
        self.mining_task = asyncio.create_task(self.mining_loop())

        # Start bot
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        logging.info("Bot started successfully")

        # Wait for stop signal
        await self.stop_flag.wait()

    async def stop(self):
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
        logging.info("Bot stopped successfully")

async def main():
    # Set up logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    # Initialize global logger
    global logger
    logger = LocationLogger()

    # Create bot instance
    bot = TelegramBot(TELEGRAM_TOKEN)

    # Handle shutdown gracefully
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.stop()))

    try:
        await bot.start()
    finally:
        await bot.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Fatal error: {e}")
