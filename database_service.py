"""
Database service for Bikera Mining Bot
Handles all database operations with PostgreSQL
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Import models
from models import Base, User, Location, Block, MiningRecord, P2PNode

logger = logging.getLogger(__name__)

class DatabaseService:
    """Database service for blockchain and mining operations"""
    
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.engine = create_engine(
            self.database_url,
            pool_recycle=300,
            pool_pre_ping=True
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database service initialized")
    
    def get_db_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def create_user(self, telegram_id: str, username: str = None, 
                   first_name: str = None, last_name: str = None,
                   solana_address: str = None) -> User:
        """Create or update user"""
        session = self.get_db_session()
        try:
            # Check if user exists
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            
            if user:
                # Update existing user
                user.username = username or user.username
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.solana_address = solana_address or user.solana_address
                user.updated_at = datetime.utcnow()
            else:
                # Create new user
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    solana_address=solana_address
                )
                session.add(user)
            
            session.commit()
            logger.info(f"User created/updated: {telegram_id}")
            return user
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating/updating user: {e}")
            raise
        finally:
            session.close()
    
    def get_user_by_telegram_id(self, telegram_id: str) -> Optional[User]:
        """Get user by Telegram ID"""
        session = self.get_db_session()
        try:
            return session.query(User).filter(User.telegram_id == telegram_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user: {e}")
            return None
        finally:
            session.close()
    
    def save_location(self, user_id: int, interval_number: int, 
                     encrypted_coordinates: bytes, obfuscated_x: float,
                     obfuscated_y: float, zone_hash: str, user_hash: str) -> Location:
        """Save location data"""
        session = self.get_db_session()
        try:
            location = Location(
                user_id=user_id,
                interval_number=interval_number,
                encrypted_coordinates=encrypted_coordinates,
                obfuscated_x=obfuscated_x,
                obfuscated_y=obfuscated_y,
                zone_hash=zone_hash,
                user_hash=user_hash
            )
            session.add(location)
            session.commit()
            logger.info(f"Location saved for user {user_id}, interval {interval_number}")
            return location
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving location: {e}")
            raise
        finally:
            session.close()
    
    def save_block(self, block_number: int, block_hash: str, previous_hash: str,
                   merkle_root: str, interval_number: int, target_distance: float,
                   winner_id: int = None, winner_solana_address: str = None,
                   travel_distance: float = None, reward_amount: float = None,
                   data_json: str = None) -> Block:
        """Save blockchain block"""
        session = self.get_db_session()
        try:
            block = Block(
                block_number=block_number,
                hash=block_hash,
                previous_hash=previous_hash,
                merkle_root=merkle_root,
                interval_number=interval_number,
                target_distance=target_distance,
                winner_id=winner_id,
                winner_solana_address=winner_solana_address,
                travel_distance=travel_distance,
                reward_amount=reward_amount,
                data_json=data_json or "{}"
            )
            session.add(block)
            session.commit()
            logger.info(f"Block {block_number} saved to database")
            return block
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving block: {e}")
            raise
        finally:
            session.close()
    
    def get_latest_block(self) -> Optional[Block]:
        """Get the latest block"""
        session = self.get_db_session()
        try:
            return session.query(Block).order_by(Block.block_number.desc()).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting latest block: {e}")
            return None
        finally:
            session.close()
    
    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        session = self.get_db_session()
        try:
            stats = {}
            
            # Basic counts
            stats['total_blocks'] = session.query(Block).count()
            stats['total_users'] = session.query(User).count()
            stats['total_locations'] = session.query(Location).count()
            stats['total_mining_records'] = session.query(MiningRecord).count()
            
            # Latest block info
            latest_block = session.query(Block).order_by(Block.block_number.desc()).first()
            if latest_block:
                stats['latest_block'] = {
                    'number': latest_block.block_number,
                    'hash': latest_block.hash,
                    'timestamp': latest_block.timestamp.isoformat(),
                    'winner_address': latest_block.winner_solana_address
                }
            
            # Active users (users with recent activity)
            active_users = session.query(User).filter(User.is_active == True).count()
            stats['active_users'] = active_users
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting blockchain stats: {e}")
            return {}
        finally:
            session.close()
    
    def record_mining_participation(self, user_id: int, block_id: int, 
                                   interval_number: int, travel_distance: float = None,
                                   won: bool = False, reward_earned: float = None) -> MiningRecord:
        """Record mining participation"""
        session = self.get_db_session()
        try:
            mining_record = MiningRecord(
                user_id=user_id,
                block_id=block_id,
                interval_number=interval_number,
                participated=True,
                won=won,
                travel_distance=travel_distance,
                reward_earned=reward_earned
            )
            session.add(mining_record)
            session.commit()
            logger.info(f"Mining participation recorded for user {user_id}")
            return mining_record
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error recording mining participation: {e}")
            raise
        finally:
            session.close()
    
    def get_user_mining_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user mining statistics"""
        session = self.get_db_session()
        try:
            stats = {}
            
            # Get mining records
            records = session.query(MiningRecord).filter(MiningRecord.user_id == user_id).all()
            
            stats['total_participations'] = len(records)
            stats['total_wins'] = sum(1 for r in records if r.won)
            stats['total_rewards'] = sum(r.reward_earned or 0 for r in records)
            stats['win_rate'] = stats['total_wins'] / stats['total_participations'] if stats['total_participations'] > 0 else 0
            
            # Get user info
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                stats['solana_address'] = user.solana_address
                stats['telegram_id'] = user.telegram_id
                stats['username'] = user.username
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting user mining stats: {e}")
            return {}
        finally:
            session.close()
    
    def migrate_json_data(self, json_file_path: str):
        """Migrate existing JSON data to PostgreSQL"""
        try:
            if not os.path.exists(json_file_path):
                logger.info(f"No JSON file found at {json_file_path}")
                return
                
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            # Migrate blockchain data
            if 'chain' in data:
                for block_data in data['chain']:
                    existing_block = self.get_db_session().query(Block).filter(
                        Block.block_number == block_data.get('index', 0)
                    ).first()
                    
                    if not existing_block:
                        self.save_block(
                            block_number=block_data.get('index', 0),
                            block_hash=block_data.get('hash', ''),
                            previous_hash=block_data.get('previous_hash', ''),
                            merkle_root=block_data.get('merkle_root', ''),
                            interval_number=block_data.get('interval_number', 0),
                            target_distance=block_data.get('target_distance', 0.0),
                            winner_id=block_data.get('winner_id'),
                            winner_solana_address=block_data.get('miner_address'),
                            travel_distance=block_data.get('travel_distance'),
                            reward_amount=block_data.get('reward_amount'),
                            data_json=json.dumps(block_data)
                        )
            
            logger.info("JSON data migration completed")
            
        except Exception as e:
            logger.error(f"Error migrating JSON data: {e}")

# Global database service instance
db_service = None

def get_database_service() -> DatabaseService:
    """Get global database service instance"""
    global db_service
    if db_service is None:
        db_service = DatabaseService()
    return db_service