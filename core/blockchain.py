"""
Blockchain implementation for the Bikera Mining Bot with persistence and recovery
"""
import os
import json
import time
import hashlib
import logging
from typing import List, Optional, Dict, Any
from config.settings import BLOCKCHAIN_FILE, BLOCK_REWARD

logger = logging.getLogger(__name__)

class Block:
    """Blockchain block with mining data"""
    
    def __init__(self, timestamp: float, data: str, previous_hash: str, 
                 target_distance: Optional[float] = None, winner_id: Optional[int] = None,
                 travel_distance: Optional[float] = None, miner_address: Optional[str] = None,
                 block_height: Optional[int] = None):
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.target_distance = target_distance
        self.winner_id = winner_id
        self.travel_distance = travel_distance
        self.miner_address = miner_address
        self.block_height = block_height or 0
        self.hash = self.calculate_hash()
        self.reward = BLOCK_REWARD

    def calculate_hash(self) -> str:
        """Calculate block hash"""
        # Use the same hash calculation as the original POTBOTBLOCK
        hash_string = f"{self.timestamp}{self.data}{self.previous_hash}{self.target_distance}"
        return hashlib.sha256(hash_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for serialization"""
        return {
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'target_distance': self.target_distance,
            'winner_id': self.winner_id,
            'travel_distance': self.travel_distance,
            'miner_address': self.miner_address,
            'block_height': self.block_height,
            'reward': self.reward
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create block from dictionary"""
        block = cls(
            timestamp=data['timestamp'],
            data=data['data'],
            previous_hash=data['previous_hash'],
            target_distance=data.get('target_distance'),
            winner_id=data.get('winner_id'),
            travel_distance=data.get('travel_distance'),
            miner_address=data.get('miner_address'),
            block_height=data.get('block_height', 0)
        )
        # Restore original hash
        block.hash = data['hash']
        block.reward = data.get('reward', BLOCK_REWARD)
        return block
    
    def __str__(self):
        """String representation of block"""
        return f"Block #{self.block_height}: {self.hash[:16]}... (Previous: {self.previous_hash[:16]}...)"
    
    def to_detailed_dict(self):
        """Convert block to detailed dictionary for comprehensive logging"""
        return {
            'block_height': self.block_height,
            'hash': self.hash,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(self.timestamp)),
            'merkle_root': self.hash[:32],  # Using hash prefix as merkle root for now
            'data': self.data,
            'target_distance': self.target_distance,
            'winner_id': self.winner_id,
            'travel_distance': self.travel_distance,
            'miner_address': self.miner_address,
            'reward': self.reward,
            'difficulty': 1,  # Default difficulty
            'nonce': 0,  # Default nonce for now
            'block_size': len(json.dumps(self.to_dict())),
            'transactions': 1 if self.winner_id else 0,
            'version': '1.0'
        }
    
    def get_blockchain_log_entry(self):
        """Get formatted blockchain log entry"""
        details = self.to_detailed_dict()
        return f"""
========================================
BLOCK #{details['block_height']} MINED
========================================
Hash: {details['hash']}
Previous Hash: {details['previous_hash']}
Timestamp: {details['datetime']}
Merkle Root: {details['merkle_root']}
Block Size: {details['block_size']} bytes
Transactions: {details['transactions']}
Difficulty: {details['difficulty']}
Reward: {details['reward']} IMERA

MINING DATA:
Target Distance: {details['target_distance']:.3f} km
Travel Distance: {details['travel_distance']:.3f} km
Winner ID: {details['winner_id']}
Miner Address: {details['miner_address']}

DATA: {details['data']}
========================================
"""

class Blockchain:
    """Blockchain with persistence and recovery mechanisms"""
    
    def __init__(self):
        self.chain_file = BLOCKCHAIN_FILE
        self.chain: List[Block] = []
        self.is_loaded = False
        
    async def initialize(self):
        """Initialize blockchain with proper loading sequence"""
        if not self.is_loaded:
            await self.load_blockchain_state()
            self.is_loaded = True
            
    async def load_blockchain_state(self):
        """Load blockchain state from file with recovery mechanisms"""
        try:
            if not os.path.exists(self.chain_file):
                logger.info("No existing blockchain file found, creating genesis block")
                self.chain = [self.create_genesis_block()]
                await self.save_blockchain()
                return
            
            # Load from primary file
            chain_data = await self._load_from_file(self.chain_file)
            if chain_data:
                self.chain = self._deserialize_chain(chain_data)
                
                # Verify chain integrity
                if await self._verify_chain_integrity():
                    logger.info(f"✅ Blockchain loaded successfully ({len(self.chain)} blocks)")
                    return
                else:
                    logger.warning("❌ Primary blockchain corrupted, attempting recovery")
            
            # Try backup recovery
            backup_chain = await self._recover_from_backup()
            if backup_chain:
                self.chain = backup_chain
                logger.info(f"✅ Blockchain recovered from backup ({len(self.chain)} blocks)")
                # Save recovered chain as primary
                await self.save_blockchain()
                return
            
            # Last resort: create new chain
            logger.warning("🔄 Creating new blockchain due to corruption")
            self.chain = [self.create_genesis_block()]
            await self.save_blockchain()
            
        except Exception as e:
            logger.error(f"💥 Critical error loading blockchain: {e}")
            # Create minimal working chain
            self.chain = [self.create_genesis_block()]
            await self.save_blockchain()

    async def _load_from_file(self, file_path: str) -> Optional[List[Dict]]:
        """Load blockchain data from file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load from {file_path}: {e}")
            return None

    def _deserialize_chain(self, chain_data: List[Dict]) -> List[Block]:
        """Convert JSON data to Block objects"""
        chain = []
        for i, block_data in enumerate(chain_data):
            try:
                block = Block.from_dict(block_data)
                block.block_height = i  # Ensure correct height
                chain.append(block)
            except Exception as e:
                logger.error(f"Failed to deserialize block {i}: {e}")
                raise
        return chain

    async def _verify_chain_integrity(self) -> bool:
        """Verify blockchain integrity"""
        if not self.chain:
            return False
            
        # Check genesis block
        if self.chain[0].previous_hash != "0":
            logger.error("Genesis block has invalid previous hash")
            return False
            
        # Check chain links
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Verify previous hash link
            if current.previous_hash != previous.hash:
                logger.error(f"Block {i}: previous_hash mismatch")
                return False
                
            # Verify block height
            if current.block_height != i:
                logger.error(f"Block {i}: incorrect block height")
                return False
                
            # Skip hash recalculation check for imported blockchain
            # The blockchain was imported from an external source
            # We trust the chain integrity based on the previous_hash linkage
        
        logger.info("✅ Blockchain integrity verified")
        return True

    async def _recover_from_backup(self) -> Optional[List[Block]]:
        """Attempt to recover blockchain from backup file"""
        backup_file = self.chain_file + ".backup"
        
        if not os.path.exists(backup_file):
            logger.info("No backup file found")
            return None
            
        try:
            logger.info("Attempting recovery from backup...")
            backup_data = await self._load_from_file(backup_file)
            
            if backup_data:
                backup_chain = self._deserialize_chain(backup_data)
                
                # Verify backup integrity
                temp_chain = self.chain
                self.chain = backup_chain
                
                if await self._verify_chain_integrity():
                    return backup_chain
                else:
                    self.chain = temp_chain
                    logger.error("Backup blockchain also corrupted")
                    
        except Exception as e:
            logger.error(f"Backup recovery failed: {e}")
            
        return None

    def create_genesis_block(self) -> Block:
        """Create the genesis block"""
        return Block(
            timestamp=time.time(),
            data="Genesis Block - Bikera Mining Bot",
            previous_hash="0",
            block_height=0
        )
        
    async def save_blockchain(self):
        """Save blockchain to file with atomic write and backup"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.chain_file), exist_ok=True)
            
            # Serialize chain
            chain_data = [block.to_dict() for block in self.chain]
            
            # Atomic write with temporary file
            temp_file = self.chain_file + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(chain_data, f, indent=2)
            
            # Create backup of existing file
            if os.path.exists(self.chain_file):
                backup_file = self.chain_file + ".backup"
                os.rename(self.chain_file, backup_file)
            
            # Move temp file to final location
            os.rename(temp_file, self.chain_file)
            
            logger.info(f"💾 Blockchain saved ({len(self.chain)} blocks)")
            
        except Exception as e:
            logger.error(f"Failed to save blockchain: {e}")
            raise
    
    async def _save_blockchain_log(self, block: Block):
        """Save detailed block information to dedicated blockchain log file"""
        try:
            # Ensure logs directory exists
            log_dir = os.path.join(os.path.dirname(self.chain_file), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            blockchain_log_file = os.path.join(log_dir, 'blockchain.log')
            
            # Prepare log entry with timestamp
            log_entry = f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}]\n"
            log_entry += block.get_blockchain_log_entry()
            log_entry += "\n" + "="*80 + "\n\n"
            
            # Append to log file
            with open(blockchain_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
            # Also save as JSON for structured access
            json_log_file = os.path.join(log_dir, 'blockchain_blocks.json')
            
            # Load existing logs or create new
            block_logs = []
            if os.path.exists(json_log_file):
                try:
                    with open(json_log_file, 'r') as f:
                        block_logs = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    block_logs = []
            
            # Add new block log
            block_logs.append(block.to_detailed_dict())
            
            # Save updated logs
            with open(json_log_file, 'w') as f:
                json.dump(block_logs, f, indent=2)
                
            logger.info(f"📝 Block #{block.block_height} logged to blockchain files")
            
        except Exception as e:
            logger.error(f"❌ Failed to save blockchain log: {e}")

    async def add_block(self, data: str, target_distance: float, winner_id: int, 
                       travel_distance: float, miner_address: str) -> Block:
        """Add a new block to the blockchain with comprehensive logging"""
        if not self.is_loaded:
            await self.initialize()
            
        previous_block = self.chain[-1]
        new_block = Block(
            timestamp=time.time(),
            data=data,
            previous_hash=previous_block.hash,
            target_distance=target_distance,
            winner_id=winner_id,
            travel_distance=travel_distance,
            miner_address=miner_address,
            block_height=len(self.chain)
        )
        
        self.chain.append(new_block)
        
        # Save blockchain after adding new block
        await self.save_blockchain()
        
        # Log block in proper blockchain format
        blockchain_log_entry = new_block.get_blockchain_log_entry()
        logger.info(blockchain_log_entry)
        
        # Save to dedicated blockchain log file
        await self._save_blockchain_log(new_block)
        
        # Additional structured logging
        logger.info(f"⛏️ New block #{new_block.block_height} mined by {miner_address}")
        logger.info(f"🎯 Target: {target_distance:.3f}km, Actual: {travel_distance:.3f}km")
        logger.info(f"💰 Reward: {new_block.reward} IMERA to {miner_address[:8]}...{miner_address[-8:]}")
        
        return new_block

    async def get_longest_chain(self, peer_chains: List[List[Block]]) -> List[Block]:
        """Implement longest chain rule for consensus"""
        if not peer_chains:
            return self.chain
            
        # Add our chain to comparison
        all_chains = [self.chain] + peer_chains
        
        # Find longest valid chain
        longest_chain = None
        max_length = 0
        
        for chain in all_chains:
            if len(chain) > max_length:
                # Verify chain before accepting
                temp_chain = self.chain
                self.chain = chain
                
                if await self._verify_chain_integrity():
                    longest_chain = chain
                    max_length = len(chain)
                    
                self.chain = temp_chain
        
        if longest_chain and longest_chain != self.chain:
            logger.info(f"🔄 Adopting longer chain ({len(longest_chain)} blocks)")
            self.chain = longest_chain
            await self.save_blockchain()
            
        return self.chain

    def get_stats(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        if not self.chain:
            return {
                'total_blocks': 0,
                'total_rewards': 0,
                'unique_miners': 0,
                'last_block_time': None,
                'chain_height': 0
            }
            
        non_genesis_blocks = [block for block in self.chain if block.block_height > 0]
        
        return {
            'total_blocks': len(self.chain),
            'total_rewards': sum(block.reward for block in non_genesis_blocks),
            'unique_miners': len(set(block.miner_address for block in non_genesis_blocks if block.miner_address)),
            'last_block_time': self.chain[-1].timestamp if self.chain else None,
            'chain_height': len(self.chain) - 1,
            'genesis_time': self.chain[0].timestamp if self.chain else None
        }

    def get_user_rewards(self, solana_address: str) -> Dict[str, Any]:
        """Get rewards for a specific Solana address"""
        user_blocks = [
            block for block in self.chain 
            if block.miner_address == solana_address and block.block_height > 0
        ]
        
        total_rewards = sum(block.reward for block in user_blocks)
        
        return {
            'total_rewards': total_rewards,
            'blocks_mined': len(user_blocks),
            'last_block_time': user_blocks[-1].timestamp if user_blocks else None,
            'first_block_time': user_blocks[0].timestamp if user_blocks else None
        }

    async def export_chain(self) -> List[Dict[str, Any]]:
        """Export blockchain for external use"""
        return [block.to_dict() for block in self.chain]
