"""
Location logger with hybrid user identification and blockchain state recovery
"""
import os
import json
import logging
import time
import datetime
from typing import Dict, Any, Optional
from core.blockchain import Blockchain
from core.mining import MiningInterval, WinnerDetermination
from core.crypto import CryptoManager
from storage.data_manager import DataManager
from config.settings import USER_DATA_FILE

logger = logging.getLogger(__name__)

class LocationLogger:
    """Manages location data, blockchain state, and hybrid user identification"""
    
    def __init__(self):
        # Core components
        self.blockchain = Blockchain()
        self.crypto_manager = CryptoManager()
        self.data_manager = DataManager()
        
        # Mining state
        self.current_interval = MiningInterval()
        self.previous_interval = None
        self.previous_interval_obj = None
        self.interval_count = 0
        
        # User data with hybrid identification
        self.user_addresses = {}  # telegram_user_id -> solana_address (for compatibility)
        self.is_initialized = False
        
        logger.info("🔧 LocationLogger initialized with hybrid user identification")

    async def initialize(self):
        """Initialize all components with proper loading sequence"""
        if self.is_initialized:
            return
            
        try:
            # Initialize blockchain first
            await self.blockchain.initialize()
            
            # Load user data
            await self.load_user_data()
            
            # Initialize data manager
            await self.data_manager.initialize()
            
            self.is_initialized = True
            logger.info("✅ LocationLogger fully initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LocationLogger: {e}")
            raise

    async def load_blockchain_state(self):
        """Load blockchain state with integrity verification"""
        try:
            # Initialize blockchain and load from file
            await self.blockchain.initialize()
            
            # Verify blockchain integrity
            if await self.blockchain._verify_chain_integrity():
                logger.info("✅ Blockchain integrity verified")
                
                # Get block count (excluding genesis)
                block_count = len(self.blockchain.chain) - 1
                
                # Handle interval reset at 100
                if block_count >= 100:
                    # Calculate interval from block count
                    self.interval_count = block_count % 100
                    if self.interval_count == 0:
                        self.interval_count = 100
                    logger.info(f"🔄 Interval: {self.interval_count} (Block {block_count})")
                else:
                    self.interval_count = block_count
                
                logger.info(f"📊 Current interval: {self.interval_count}, Total blocks: {block_count}")
            else:
                logger.error("❌ Blockchain integrity check failed!")
                # Start fresh if integrity check fails
                self.blockchain.chain = [self.blockchain.create_genesis_block()]
                await self.blockchain.save_blockchain()
                self.interval_count = 0
                
            logger.info("📂 Blockchain state loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load blockchain state: {e}")
            raise

    async def _get_peer_chains(self):
        """Get blockchain data from network peers (placeholder for P2P implementation)"""
        # This would connect to P2P network and fetch peer chains
        # For now, return empty list as P2P is not fully implemented
        return []
    
    async def _save_epoch_blocks(self):
        """Save blockchain blocks to epoch file (every 100 blocks)"""
        try:
            # Create blocks directory if it doesn't exist
            blocks_dir = os.path.join('data', 'blocks')
            os.makedirs(blocks_dir, exist_ok=True)
            
            # Calculate which epoch we're in based on total blocks
            total_blocks = len(self.blockchain.chain) - 1  # Exclude genesis
            if total_blocks == 0:
                return
                
            # Calculate epoch range (1-100, 101-200, etc.)
            epoch_num = ((total_blocks - 1) // 100) + 1
            epoch_start = (epoch_num - 1) * 100 + 1
            epoch_end = min(epoch_num * 100, total_blocks)
            
            # Only save if we have a complete epoch (100 blocks) or if specifically requested
            if total_blocks % 100 != 0:
                return
            
            # Generate filename with epoch and block range
            filename = f"era_{epoch_num}_blocks_{epoch_start}-{epoch_end}.era"
            filepath = os.path.join(blocks_dir, filename)
            
            # Get the blocks for this epoch
            start_index = epoch_start  # Account for genesis block at index 0
            end_index = epoch_end + 1  # +1 for slice
            blocks_to_save = self.blockchain.chain[start_index:end_index]
            
            # Serialize blocks
            block_data = []
            for block in blocks_to_save:
                block_data.append(block.to_dict())
            
            # Save to .era file
            with open(filepath, 'w') as f:
                json.dump({
                    'metadata': {
                        'timestamp': datetime.datetime.now().isoformat(),
                        'epoch': epoch_num,
                        'block_range': f"{epoch_start}-{epoch_end}",
                        'total_blocks': len(blocks_to_save),
                        'chain_height': total_blocks
                    },
                    'blocks': block_data
                }, f, indent=2)
            
            logger.info(f"📦 Saved era {epoch_num} (blocks {epoch_start}-{epoch_end}) to {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Failed to save epoch block file: {e}")
            raise

    async def load_user_data(self):
        """Load user data with hybrid identification support"""
        try:
            if not os.path.exists(USER_DATA_FILE):
                logger.info("📄 No existing user data file found, starting fresh")
                await self.save_user_data()
                return
            
            with open(USER_DATA_FILE, 'r') as f:
                data = json.load(f)
            
            # Load legacy user addresses
            self.user_addresses = data.get('user_addresses', {})
            
            # Convert string keys to integers for telegram user IDs
            if self.user_addresses:
                self.user_addresses = {
                    int(k): v for k, v in self.user_addresses.items()
                }
            
            # Load interval state
            self.interval_count = data.get('interval_count', 0)
            
            # Load previous interval data and reconstruct ObfuscatedCoordinate objects
            previous_interval_data = data.get('previous_interval')
            if previous_interval_data:
                from core.mining import ObfuscatedCoordinate
                self.previous_interval = {}
                for user_hash, coord_data in previous_interval_data.items():
                    if isinstance(coord_data, dict) and 'x' in coord_data:
                        # Reconstruct ObfuscatedCoordinate from dict
                        self.previous_interval[user_hash] = ObfuscatedCoordinate(
                            x=coord_data['x'],
                            y=coord_data['y'],
                            zone_hash=coord_data['zone_hash'],
                            timestamp=coord_data['timestamp'],
                            user_id_hash=coord_data['user_id_hash']
                        )
                    else:
                        # Legacy format
                        self.previous_interval[user_hash] = coord_data
            else:
                self.previous_interval = None
            
            # Load crypto manager mappings
            crypto_mappings = data.get('crypto_mappings', {})
            if crypto_mappings:
                # Convert string keys to integers
                self.crypto_manager.solana_mappings = {
                    int(k): v for k, v in crypto_mappings.items()
                }
            
            # Migrate legacy data to new hybrid system
            await self._migrate_legacy_data()
            
            logger.info(f"📂 User data loaded: {len(self.user_addresses)} users")
            logger.info(f"🔐 Crypto mappings: {len(self.crypto_manager.solana_mappings)} mappings")
            
        except Exception as e:
            logger.error(f"❌ Failed to load user data: {e}")
            # Initialize with empty state
            self.user_addresses = {}
            self.interval_count = 0
            self.previous_interval = None
            await self.save_user_data()

    async def _migrate_legacy_data(self):
        """Migrate legacy user data to hybrid identification system"""
        try:
            migrations_needed = 0
            
            # Migrate user addresses to crypto manager
            for telegram_user_id, solana_address in self.user_addresses.items():
                if telegram_user_id not in self.crypto_manager.solana_mappings:
                    self.crypto_manager.set_solana_address(telegram_user_id, solana_address)
                    migrations_needed += 1
                    
                # Generate keys if user doesn't have them
                if telegram_user_id not in self.crypto_manager.telegram_user_keys:
                    self.crypto_manager.generate_user_keys(telegram_user_id)
                    migrations_needed += 1
            
            if migrations_needed > 0:
                logger.info(f"🔄 Migrated {migrations_needed} legacy user records to hybrid system")
                await self.save_user_data()
                
        except Exception as e:
            logger.error(f"❌ Failed to migrate legacy data: {e}")

    async def save_user_data(self):
        """Save user data with hybrid identification support"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
            
            # Serialize previous interval data (convert ObfuscatedCoordinate to dict)
            serialized_previous_interval = None
            if self.previous_interval:
                serialized_previous_interval = {}
                for user_hash, coord in self.previous_interval.items():
                    if hasattr(coord, 'to_dict'):
                        serialized_previous_interval[user_hash] = coord.to_dict()
                    else:
                        serialized_previous_interval[user_hash] = coord
            
            # Prepare data for saving
            data = {
                'user_addresses': self.user_addresses,
                'interval_count': self.interval_count,
                'previous_interval': serialized_previous_interval,
                'crypto_mappings': self.crypto_manager.solana_mappings,
                'last_updated': time.time(),
                'version': '2.0',  # Hybrid identification version
                'migration_complete': True
            }
            
            # Atomic write
            temp_file = USER_DATA_FILE + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Backup existing file
            if os.path.exists(USER_DATA_FILE):
                backup_file = USER_DATA_FILE + '.backup'
                os.rename(USER_DATA_FILE, backup_file)
            
            # Move temp file to final location
            os.rename(temp_file, USER_DATA_FILE)
            
            logger.info("💾 User data saved successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to save user data: {e}")
            raise

    async def process_winner(self, winner: Dict[str, Any], target_distance: float):
        """Process winner with hybrid identification"""
        try:
            if not winner:
                logger.warning("No winner to process")
                return None
            
            # Extract winner information
            telegram_user_id = winner['user_id']
            solana_address = winner['solana_address']
            travel_distance = winner['travel_distance']
            
            # Create block data
            block_data = f"Winner: {winner['user_hash'][:8]}, Distance: {travel_distance:.3f}km"
            
            # Add block to blockchain
            new_block = await self.blockchain.add_block(
                data=block_data,
                target_distance=target_distance,
                winner_id=telegram_user_id,  # Store Telegram ID for notifications
                travel_distance=travel_distance,
                miner_address=solana_address  # Store Solana address for rewards
            )
            
            # Log winner with hybrid identification
            logger.info(f"🏆 Winner processed - Telegram: {telegram_user_id}, Solana: {solana_address[:8]}...{solana_address[-8:]}")
            logger.info(f"⛏️ Block #{new_block.block_height} added to blockchain")
            
            # Save user activity log
            await self.data_manager.log_user_activity(
                telegram_user_id=telegram_user_id,
                solana_address=solana_address,
                activity_type="win",
                data={
                    'block_height': new_block.block_height,
                    'target_distance': target_distance,
                    'travel_distance': travel_distance,
                    'difference': winner['difference'],
                    'reward': new_block.reward,
                    'timestamp': new_block.timestamp
                }
            )
            
            return new_block
            
        except Exception as e:
            logger.error(f"❌ Error processing winner: {e}")
            return None

    def determine_winner(self, previous_coords: Dict[str, Any], current_coords: Dict[str, Any], 
                        target_distance: float) -> Optional[Dict[str, Any]]:
        """Determine winner using hybrid identification"""
        return WinnerDetermination.determine_winner(
            previous_coords, 
            current_coords, 
            target_distance,
            self.previous_interval_obj,
            self.current_interval
        )

    async def get_user_stats(self, telegram_user_id: int) -> Dict[str, Any]:
        """Get user statistics with hybrid identification"""
        try:
            # Get user's Solana address
            solana_address = self.crypto_manager.get_solana_address(telegram_user_id)
            
            if not solana_address:
                return {
                    'telegram_user_id': telegram_user_id,
                    'solana_address': None,
                    'total_rewards': 0,
                    'blocks_mined': 0,
                    'error': 'No Solana address found'
                }
            
            # Get blockchain stats for the Solana address
            blockchain_stats = self.blockchain.get_user_rewards(solana_address)
            
            # Get user activity logs
            activity_logs = await self.data_manager.get_user_activity_logs(telegram_user_id)
            
            return {
                'telegram_user_id': telegram_user_id,
                'solana_address': solana_address,
                'total_rewards': blockchain_stats['total_rewards'],
                'blocks_mined': blockchain_stats['blocks_mined'],
                'first_block_time': blockchain_stats['first_block_time'],
                'last_block_time': blockchain_stats['last_block_time'],
                'total_activities': len(activity_logs),
                'has_encryption_keys': telegram_user_id in self.crypto_manager.telegram_user_keys
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting user stats for {telegram_user_id}: {e}")
            return {
                'telegram_user_id': telegram_user_id,
                'error': str(e)
            }

    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Save final state
            await self.save_user_data()
            
            # Cleanup data manager
            await self.data_manager.cleanup()
            
            logger.info("🧹 LocationLogger cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        blockchain_stats = self.blockchain.get_stats()
        crypto_stats = self.crypto_manager.get_user_stats()
        
        return {
            'blockchain': blockchain_stats,
            'users': crypto_stats,
            'intervals': {
                'current_interval': self.interval_count,
                'interval_active': self.current_interval.is_active if self.current_interval else False,
                'participants_current': len(self.current_interval.staged_coordinates) if self.current_interval else 0
            },
            'hybrid_identification': {
                'enabled': True,
                'telegram_users': len(self.crypto_manager.telegram_user_keys),
                'solana_addresses': len(set(self.crypto_manager.solana_mappings.values())),
                'user_mappings': len(self.crypto_manager.solana_mappings)
            }
        }
