"""
Utility functions for the Bikera Mining Bot
"""
import os
import logging
import sys
from math import radians, sin, cos, sqrt, atan2
from typing import Tuple
from config.settings import DATA_DIR, LOGS_DIR, LOG_FORMAT, LOG_LEVEL, LOG_FILE

def setup_logging():
    """Configure logging for the application"""
    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE)
        ]
    )
    return logging.getLogger(__name__)

def ensure_directories():
    """Ensure all required directories exist"""
    directories = [DATA_DIR, LOGS_DIR, os.path.join(DATA_DIR, "user_logs")]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
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

def calculate_travel_distance(start_coords: Tuple[float, float], 
                            end_coords: Tuple[float, float]) -> float:
    """Calculate the distance traveled between two coordinate pairs"""
    return calculate_distance(start_coords, end_coords)

def validate_solana_address(address: str) -> bool:
    """Validate Solana address format"""
    if not address or not isinstance(address, str):
        return False
    
    # Basic validation: Solana addresses are base58 encoded and 32-44 characters
    if len(address) < 32 or len(address) > 44:
        return False
    
    # Check for valid base58 characters
    base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    for char in address:
        if char not in base58_chars:
            return False
    
    return True

def format_solana_address(address: str) -> str:
    """Format Solana address for display"""
    if not address or len(address) < 16:
        return address
    return f"{address[:8]}...{address[-8:]}"

def debug_startup():
    """Debug function to check what's happening during startup"""
    print("🔍 Debug: Starting up...")
    print(f"🐍 Python version: {sys.version}")
    print(f"💻 Platform: {sys.platform}")
    
    try:
        import zmq
        print(f"✅ ZeroMQ version: {zmq.zmq_version()}")
    except ImportError:
        print("❌ ZeroMQ not available")
    
    from config.settings import TELEGRAM_TOKEN
    if TELEGRAM_TOKEN:
        print(f"✅ Telegram token found (length: {len(TELEGRAM_TOKEN)})")
    else:
        print("❌ Telegram token not found")
    
    print("🔍 Debug: Startup checks complete\n")

def format_time_remaining(seconds: int) -> str:
    """Format time remaining in a human-readable format"""
    if seconds <= 0:
        return "0s"
    
    minutes = seconds // 60
    seconds = seconds % 60
    
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def format_distance(distance: float) -> str:
    """Format distance in a human-readable format"""
    if distance < 1.0:
        return f"{distance * 1000:.0f}m"
    else:
        return f"{distance:.3f}km"
