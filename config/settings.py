"""
Configuration settings for the Bikera Mining Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Solana Configuration
SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
IMERA_TOKEN_CONTRACT = os.getenv('IMERA_TOKEN_CONTRACT', "FtrH7NCrPDkhDmKCCdTnsDBFxiibc1X5aJPHqKQnpump")
IMERA_TOKEN_THRESHOLD = int(os.getenv('IMERA_TOKEN_THRESHOLD', '100000'))

# Mining Configuration
MINING_INTERVAL_DURATION = int(os.getenv('MINING_INTERVAL_DURATION', '600'))  # 10 minutes
MIN_DISTANCE = float(os.getenv('MIN_DISTANCE', '0.1'))  # Minimum target distance in km
MAX_DISTANCE = float(os.getenv('MAX_DISTANCE', '10.0'))  # Maximum target distance in km
BLOCK_REWARD = float(os.getenv('BLOCK_REWARD', '1000.0'))  # Reward amount per block

# Network Constants
CONSENSUS_ROUND_DURATION = int(os.getenv('CONSENSUS_ROUND_DURATION', '30'))
MIN_NODES = int(os.getenv('MIN_NODES', '1'))
NODE_SYNC_INTERVAL = int(os.getenv('NODE_SYNC_INTERVAL', '150'))
BLOCK_PROPAGATION_DELAY = int(os.getenv('BLOCK_PROPAGATION_DELAY', '2'))

# P2P Network Constants
DEFAULT_P2P_PORT = int(os.getenv('DEFAULT_P2P_PORT', '8333'))
DEFAULT_CONSENSUS_PORT = int(os.getenv('DEFAULT_CONSENSUS_PORT', '5555'))
DEFAULT_GOSSIP_PORT = int(os.getenv('DEFAULT_GOSSIP_PORT', '5556'))
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '10'))
PEER_TIMEOUT = int(os.getenv('PEER_TIMEOUT', '30'))
MAX_PEERS = int(os.getenv('MAX_PEERS', '8'))

# File Paths
DATA_DIR = "data"
LOGS_DIR = "logs"
USER_LOGS_DIR = os.path.join(DATA_DIR, "user_logs")
BLOCKCHAIN_FILE = os.path.join(DATA_DIR, "blockchain.json")
USER_DATA_FILE = os.path.join(DATA_DIR, "user_data.json")
LOG_FILE = os.path.join(LOGS_DIR, "blockchain_bot.log")

# Conversation States
WAITING_ADDRESS = 1
WAITING_LOCATION = 1

# Logging Configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
