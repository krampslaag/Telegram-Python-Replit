"""
Mining intervals and logic with coordinate obfuscation
"""
import time
import random
import logging
import hashlib
import math
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from config.settings import MINING_INTERVAL_DURATION, MIN_DISTANCE, MAX_DISTANCE
from core.utils import calculate_travel_distance

logger = logging.getLogger(__name__)

@dataclass
class ObfuscatedCoordinate:
    """Obfuscated coordinate that preserves distance relationships"""
    x: float  # Obfuscated X coordinate
    y: float  # Obfuscated Y coordinate
    zone_hash: str  # Geographic zone identifier
    timestamp: float
    user_id_hash: str  # Hashed user ID for linking intervals
    
    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'zone_hash': self.zone_hash,
            'timestamp': self.timestamp,
            'user_id_hash': self.user_id_hash
        }

class CoordinateObfuscator:
    """Handles coordinate obfuscation while preserving distance relationships"""
    
    def __init__(self, interval_salt: str = None):
        self.interval_salt = interval_salt or "default_salt"
        self.zone_size = 0.01  # ~1km grid zones
        
    def _get_geographic_zone(self, lat: float, lon: float) -> Tuple[int, int]:
        """Get the geographic zone (grid cell) for coordinates"""
        zone_lat = int(lat / self.zone_size)
        zone_lon = int(lon / self.zone_size)
        return zone_lat, zone_lon
    
    def _get_zone_hash(self, zone_lat: int, zone_lon: int) -> str:
        """Create a hash representing the geographic zone"""
        zone_data = f"{zone_lat}:{zone_lon}:{self.interval_salt}"
        return hashlib.sha256(zone_data.encode()).hexdigest()[:16]
    
    def _get_user_offset(self, user_id: int, interval_number: int) -> Tuple[float, float]:
        """Generate consistent random offset for user within an interval"""
        seed_data = f"{user_id}:{interval_number}:{self.interval_salt}"
        seed_hash = hashlib.sha256(seed_data.encode()).digest()
        
        # Use first 8 bytes for X offset, next 8 bytes for Y offset
        x_seed = int.from_bytes(seed_hash[:8], byteorder='big')
        y_seed = int.from_bytes(seed_hash[8:16], byteorder='big')
        
        # Generate offset in range [-0.005, 0.005] degrees (~500m max)
        x_offset = ((x_seed % 10000) / 10000.0 - 0.5) * 0.01
        y_offset = ((y_seed % 10000) / 10000.0 - 0.5) * 0.01
        
        return x_offset, y_offset
    
    def _get_user_hash(self, user_id: int, interval_number: int) -> str:
        """Generate consistent hash for user within interval"""
        user_data = f"{user_id}:{interval_number}:{self.interval_salt}"
        return hashlib.sha256(user_data.encode()).hexdigest()[:16]
    
    def obfuscate_coordinate(self, lat: float, lon: float, user_id: int, 
                           interval_number: int, timestamp: float) -> ObfuscatedCoordinate:
        """Obfuscate coordinates while preserving relative distances"""
        # Get geographic zone
        zone_lat, zone_lon = self._get_geographic_zone(lat, lon)
        zone_hash = self._get_zone_hash(zone_lat, zone_lon)
        
        # Get consistent offset for this user in this interval
        x_offset, y_offset = self._get_user_offset(user_id, interval_number)
        
        # Transform to local coordinate system within zone
        zone_center_lat = zone_lat * self.zone_size + self.zone_size / 2
        zone_center_lon = zone_lon * self.zone_size + self.zone_size / 2
        
        # Convert to local coordinates (relative to zone center) + offset
        local_x = (lon - zone_center_lon) + x_offset
        local_y = (lat - zone_center_lat) + y_offset
        
        # Scale to make coordinates less obviously geographic
        scale_factor = 100000
        obfuscated_x = local_x * scale_factor
        obfuscated_y = local_y * scale_factor
        
        # Generate user hash for this interval
        user_hash = self._get_user_hash(user_id, interval_number)
        
        return ObfuscatedCoordinate(
            x=obfuscated_x,
            y=obfuscated_y,
            zone_hash=zone_hash,
            timestamp=timestamp,
            user_id_hash=user_hash
        )
    
    def calculate_obfuscated_distance(self, coord1: ObfuscatedCoordinate, 
                                    coord2: ObfuscatedCoordinate) -> Optional[float]:
        """Calculate distance between obfuscated coordinates"""
        # Check if coordinates are in compatible zones
        if coord1.zone_hash != coord2.zone_hash:
            logger.warning(f"Cannot calculate distance across different zones")
            return None
        
        # Calculate Euclidean distance in obfuscated coordinate system
        dx = coord2.x - coord1.x
        dy = coord2.y - coord1.y
        
        # Convert back to approximate real-world distance
        scale_factor = 100000
        dx_real = dx / scale_factor
        dy_real = dy / scale_factor
        
        # Convert degrees to approximate kilometers
        lat_km_per_degree = 111.0
        lon_km_per_degree = 111.0 * math.cos(math.radians(45))
        
        distance_km = math.sqrt((dx_real * lon_km_per_degree)**2 + (dy_real * lat_km_per_degree)**2)
        
        return distance_km

class MiningInterval:
    def __init__(self):
        self.start_time = None
        self.is_active = False
        self.staged_coordinates = {}  # user_id_hash -> ObfuscatedCoordinate
        self.finalized_coordinates = {}
        self.target_distance = None
        self.interval_number = 0
        self.obfuscator = None
        
        # Keep mapping for reward distribution (encrypted separately)
        self._user_id_mapping = {}  # user_id_hash -> real_user_id

    def start(self, interval_number):
        """Start a new mining interval"""
        self.start_time = time.time()
        self.is_active = True
        self.interval_number = interval_number
        self.target_distance = random.uniform(MIN_DISTANCE, MAX_DISTANCE)
        self.staged_coordinates = {}   #CHECK nazien of dit niet weg mag
        self._user_id_mapping = {}
        
        # Create interval-specific obfuscator
        interval_salt = f"interval_{interval_number}_{int(time.time() // 3600)}"
        self.obfuscator = CoordinateObfuscator(interval_salt)
        
        logger.info(f"🔒 Privacy-preserving interval {interval_number} started")
        logger.info(f"🎯 Target distance: {self.target_distance:.3f}km")
        return self.target_distance

    def stage_coordinates(self, user_id, coordinates):
        """Stage obfuscated coordinates for a user"""
        if not self.is_active:
            logger.warning("Interval not active")
            return
            
        lat, lon = coordinates
        timestamp = time.time()
        
        # Obfuscate the coordinates
        obfuscated_coord = self.obfuscator.obfuscate_coordinate(
            lat, lon, user_id, self.interval_number, timestamp
        )
        
        # Store using the hashed user ID
        user_hash = obfuscated_coord.user_id_hash
        self.staged_coordinates[user_hash] = obfuscated_coord
        self._user_id_mapping[user_hash] = user_id  # Keep for rewards
        
        logger.info(f"📍 User {user_id} staged obfuscated coordinates in zone {obfuscated_coord.zone_hash[:8]}")
        logger.debug(f"🔒 User hash: {user_hash[:8]}")

    def finalize_interval(self):
        """Finalize coordinates for all users at interval end"""
        self.is_active = False
        
        # Convert staged coordinates to finalized format
        finalized = {}
        for user_hash, coord_data in self.staged_coordinates.items():
            finalized[user_hash] = {
                'start_coords': coord_data,  # ObfuscatedCoordinate object
                'end_coords': coord_data,
                'timestamp': coord_data.timestamp
            }
        
        self.finalized_coordinates = finalized
        logger.info(f"✅ Privacy-preserving interval {self.interval_number} finalized with {len(finalized)} participants")
        
        return finalized

    def get_time_remaining(self):
        """Get remaining time in current interval"""
        if not self.is_active:
            return 0
        elapsed = time.time() - self.start_time
        remaining = max(0, MINING_INTERVAL_DURATION - elapsed)
        return int(remaining)
    
    def get_real_user_id(self, user_hash: str) -> Optional[int]:
        """Get real user ID from hash (for reward distribution)"""
        return self._user_id_mapping.get(user_hash)

class WinnerDetermination:
    """Handles winner determination logic"""
    
    @staticmethod
    def determine_winner(previous_coords, current_coords, target_distance, 
                        previous_interval=None, current_interval=None):
        """Determine winner using obfuscated coordinates"""
        if not previous_coords or not current_coords:
            logger.warning("Missing coordinate data for winner determination")
            return None
        
        if not previous_interval or not current_interval:
            logger.error("Missing interval objects for obfuscated coordinate processing")
            return None
            
        winner = None
        closest_difference = float('inf')
        
        logger.info(f"🎯 Determining winner for target distance: {target_distance:.3f}km")
        logger.info(f"Previous interval participants: {len(previous_coords)}")
        logger.info(f"Current interval participants: {len(current_coords)}")
        
        # Find users who participated in both intervals (by user hash)
        common_user_hashes = set(previous_coords.keys()) & set(current_coords.keys())
        logger.info(f"Users in both intervals: {len(common_user_hashes)}")
        
        if not common_user_hashes:
            logger.warning("No users participated in both intervals")
            return None
        
        successful_calculations = 0
        
        for user_hash in common_user_hashes:
            try:
                # Get obfuscated coordinates
                prev_coord = previous_coords[user_hash]['end_coords']
                curr_coord = current_coords[user_hash]['end_coords']
                
                # Calculate travel distance using current interval's obfuscator
                travel_distance = current_interval.obfuscator.calculate_obfuscated_distance(
                    prev_coord, curr_coord
                )
                
                if travel_distance is None:
                    logger.warning(f"Could not calculate distance for user {user_hash[:8]} (different zones)")
                    continue
                
                successful_calculations += 1
                difference = abs(travel_distance - target_distance)
                
                logger.info(f"User {user_hash[:8]}: moved {travel_distance:.3f}km, difference: {difference:.3f}km")
                
                if difference < closest_difference:
                    closest_difference = difference
                    
                    # Get real user ID for reward distribution
                    real_user_id = current_interval.get_real_user_id(user_hash)
                    
                    winner = {
                        'user_id': real_user_id,  # Real user ID for rewards
                        'user_hash': user_hash,   # Hash for privacy
                        'travel_distance': travel_distance,
                        'target_distance': target_distance,
                        'difference': difference,
                        'start_coords': prev_coord,  # Obfuscated
                        'end_coords': curr_coord     # Obfuscated
                    }
                    
            except Exception as e:
                logger.error(f"Error calculating distance for user {user_hash[:8]}: {e}")
                continue
        
        logger.info(f"Successfully calculated distances for {successful_calculations} users")
        
        if winner:
            logger.info(f"🏆 Winner: User {winner['user_hash'][:8]} with {winner['difference']:.3f}km difference")
        else:
            logger.warning("No winner could be determined")
        
        return winner
