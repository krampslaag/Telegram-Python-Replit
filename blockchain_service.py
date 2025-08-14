#!/usr/bin/env python3
"""
Blockchain service singleton for sharing blockchain state between Flask and Telegram bot
"""
import asyncio
import logging
from storage.location_logger import LocationLogger

logger = logging.getLogger(__name__)

class BlockchainService:
    """Singleton service for blockchain access"""
    _instance = None
    _location_logger = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BlockchainService, cls).__new__(cls)
        return cls._instance
    
    async def initialize(self):
        """Initialize the blockchain service"""
        if self._initialized:
            return
            
        try:
            # Create location logger
            self._location_logger = LocationLogger()
            
            # Initialize it
            await self._location_logger.initialize()
            
            # Load blockchain state
            await self._location_logger.load_blockchain_state()
            
            self._initialized = True
            logger.info(f"✅ Blockchain service initialized with {len(self._location_logger.blockchain.chain)} blocks")
            
        except Exception as e:
            logger.error(f"Failed to initialize blockchain service: {e}")
            raise
    
    @property
    def location_logger(self):
        """Get the location logger instance"""
        if not self._initialized:
            raise RuntimeError("Blockchain service not initialized")
        return self._location_logger
    
    @property
    def blockchain(self):
        """Get the blockchain instance"""
        if not self._initialized:
            raise RuntimeError("Blockchain service not initialized")
        return self._location_logger.blockchain
    
    def get_status(self):
        """Get current blockchain status"""
        if not self._initialized:
            return {
                'initialized': False,
                'total_blocks': 0,
                'current_interval': 0
            }
        
        return {
            'initialized': True,
            'total_blocks': len(self._location_logger.blockchain.chain),
            'current_interval': self._location_logger.interval_count,
            'target_distance': getattr(self._location_logger.current_interval, 'target_distance', 5.2)
        }

# Create global instance
blockchain_service = BlockchainService()