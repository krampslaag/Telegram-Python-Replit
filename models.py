"""
Database models for the Bikera Mining Bot
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, LargeBinary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    """User model with hybrid identification system"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False)
    solana_address = Column(String(100), nullable=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    locations = relationship("Location", back_populates="user")
    mining_records = relationship("MiningRecord", back_populates="user")

class Location(Base):
    """Location records with privacy protection"""
    __tablename__ = 'locations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    interval_number = Column(Integer, nullable=False)
    encrypted_coordinates = Column(LargeBinary, nullable=False)  # RSA encrypted
    obfuscated_x = Column(Float, nullable=False)
    obfuscated_y = Column(Float, nullable=False)
    zone_hash = Column(String(64), nullable=False)
    user_hash = Column(String(64), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="locations")

class Block(Base):
    """Blockchain blocks"""
    __tablename__ = 'blocks'
    
    id = Column(Integer, primary_key=True)
    block_number = Column(Integer, unique=True, nullable=False)
    hash = Column(String(64), unique=True, nullable=False)
    previous_hash = Column(String(64), nullable=False)
    merkle_root = Column(String(64), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    interval_number = Column(Integer, nullable=False)
    target_distance = Column(Float, nullable=False)
    winner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    winner_solana_address = Column(String(100), nullable=True)
    travel_distance = Column(Float, nullable=True)
    reward_amount = Column(Float, nullable=True)
    data_json = Column(Text, nullable=False)  # JSON string of block data
    
    # Relationships
    mining_records = relationship("MiningRecord", back_populates="block")
    winner = relationship("User", foreign_keys=[winner_id])

class MiningRecord(Base):
    """Mining participation records"""
    __tablename__ = 'mining_records'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    block_id = Column(Integer, ForeignKey('blocks.id'), nullable=False)
    interval_number = Column(Integer, nullable=False)
    participated = Column(Boolean, default=False)
    won = Column(Boolean, default=False)
    travel_distance = Column(Float, nullable=True)
    reward_earned = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="mining_records")
    block = relationship("Block", back_populates="mining_records")

class P2PNode(Base):
    """P2P network nodes"""
    __tablename__ = 'p2p_nodes'
    
    id = Column(Integer, primary_key=True)
    node_id = Column(String(64), unique=True, nullable=False)
    address = Column(String(100), nullable=False)
    port = Column(Integer, nullable=False)
    public_key = Column(LargeBinary, nullable=True)
    is_authority = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)