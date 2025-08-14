"""
Blockchain implementation for the Bikera Mining Bot
"""
import os
import json
import time
import hashlib
import logging
from config.settings import BLOCKCHAIN_FILE, BLOCK_REWARD

logger = logging.getLogger(__name__)

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
        self.reward = BLOCK_REWARD

    def calculate_hash(self):
        hash_string = f"{self.timestamp}{self.data}{self.previous_hash}{self.target_distance}"
        return hashlib.sha256(hash_string.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain_file = BLOCKCHAIN_FILE
        self.chain = self.load_blockchain() or [self.create_genesis_block()]
        
    def create_genesis_block(self):
        return Block(time.time(), "Genesis Block", "0")
    
    def save_blockchain(self):
        """Save blockchain to file"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.chain_file), exist_ok=True)
            
            # Convert blocks to serializable format
            chain_data = []
            for block in self.chain:
                block_data = {
                    'timestamp': block.timestamp,
                    'data': block.data,
                    'previous_hash': block.previous_hash,
                    'hash': block.hash,
                    'target_distance': block.target_distance,
                    'winner_id': block.winner_id,
                    'travel_distance': block.travel_distance,
                    'miner_address': block.miner_address,
                    'reward': block.reward
                }
                chain_data.append(block_data)
            
            # Save to file with backup
            temp_file = self.chain_file + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(chain_data, f, indent=2)
            
            # Atomic rename
            if os.path.exists(self.chain_file):
                backup_file = self.chain_file + ".backup"
                os.rename(self.chain_file, backup_file)
            
            os.rename(temp_file, self.chain_file)
            logger.info(f"Blockchain saved to {self.chain_file} ({len(self.chain)} blocks)")
            
        except Exception as e:
            logger.error(f"Failed to save blockchain: {e}")
    
    def load_blockchain(self):
        """Load blockchain from file"""
        try:
            if not os.path.exists(self.chain_file):
                logger.info("No existing blockchain file found, starting fresh")
                return None
            
            with open(self.chain_file, 'r') as f:
                chain_data = json.load(f)
            
            # Convert back to Block objects
            chain = []
            for block_data in chain_data:
                block = Block(
                    timestamp=block_data['timestamp'],
                    data=block_data['data'], 
                    previous_hash=block_data['previous_hash'],
                    target_distance=block_data.get('target_distance'),
                    winner_id=block_data.get('winner_id'),
                    travel_distance=block_data.get('travel_distance'),
                    miner_address=block_data.get('miner_address')
                )
                # Restore the hash instead of recalculating
                block.hash = block_data['hash']
                block.reward = block_data.get('reward', BLOCK_REWARD)
                chain.append(block)
            
            logger.info(f"Blockchain loaded from {self.chain_file} ({len(chain)} blocks)")
            
            # Verify chain integrity
            if self.verify_loaded_chain(chain):
                logger.info("✅ Blockchain integrity verified")
                return chain
            else:
                logger.warning("❌ Blockchain integrity check failed, starting fresh")
                return self.load_backup_blockchain()
                
        except Exception as e:
            logger.error(f"Failed to load blockchain: {e}")
            return self.load_backup_blockchain()
    
    def load_backup_blockchain(self):
        """Try to load from backup file"""
        backup_file = self.chain_file + ".backup"
        try:
            if os.path.exists(backup_file):
                logger.info("Attempting to load from backup...")
                with open(backup_file, 'r') as f:
                    chain_data = json.load(f)
                
                chain = []
                for block_data in chain_data:
                    block = Block(
                        timestamp=block_data['timestamp'],
                        data=block_data['data'],
                        previous_hash=block_data['previous_hash'],
                        target_distance=block_data.get('target_distance'),
                        winner_id=block_data.get('winner_id'),
                        travel_distance=block_data.get('travel_distance'),
                        miner_address=block_data.get('miner_address')
                    )
                    block.hash = block_data['hash']
                    block.reward = block_data.get('reward', BLOCK_REWARD)
                    chain.append(block)
                
                if self.verify_loaded_chain(chain):
                    logger.info("✅ Backup blockchain loaded and verified")
                    return chain
                    
        except Exception as e:
            logger.error(f"Failed to load backup blockchain: {e}")
        
        logger.info("Starting with fresh blockchain")
        return None
    
    def verify_loaded_chain(self, chain):
        """Verify the integrity of a loaded blockchain"""
        if not chain:
            return False
            
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i-1]
            
            # Check if previous hash matches
            if current.previous_hash != previous.hash:
                logger.error(f"Block {i}: previous_hash mismatch")
                return False
        
        return True
        
    def add_block(self, data, target_distance, winner_id, travel_distance, miner_address):
        """Add a new block to the blockchain"""
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
        
        # Save blockchain after adding new block
        self.save_blockchain()
        
        logger.info(f"New block added: #{len(self.chain)-1} by {winner_id}")
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
    
    def get_stats(self):
        """Get blockchain statistics"""
        total_blocks = len(self.chain)
        total_rewards = sum(block.reward for block in self.chain[1:])  # Skip genesis
        unique_miners = len(set(block.miner_address for block in self.chain[1:] if block.miner_address))
        
        return {
            'total_blocks': total_blocks,
            'total_rewards': total_rewards,
            'unique_miners': unique_miners,
            'last_block_time': self.chain[-1].timestamp if self.chain else None
        }