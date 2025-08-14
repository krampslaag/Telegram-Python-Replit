"""
Cryptography and VRF implementation
"""
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Any
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding, ec
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

@dataclass
class VRFProof:
    """VRF proof containing signature and hash"""
    signature: bytes
    hash_value: bytes
    public_key: bytes
    node_id: str
    seed: str

class VRF:
    """Verified Random Function implementation using ECDSA"""
    
    def __init__(self):
        self.private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
        self.public_key = self.private_key.public_key()

    def prove(self, seed: str, node_id: str) -> VRFProof:
        """Generate VRF proof for given seed"""
        message = f"{seed}:{node_id}".encode('utf-8')
        signature = self.private_key.sign(message, ec.ECDSA(hashes.SHA256()))
        hash_value = hashlib.sha256(signature).digest()
        
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        return VRFProof(signature, hash_value, public_key_bytes, node_id, seed)

    @staticmethod
    def verify(proof: VRFProof) -> bool:
        """Verify VRF proof"""
        try:
            # Reconstruct public key
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256K1(), proof.public_key
            )
            
            # Verify signature
            message = f"{proof.seed}:{proof.node_id}".encode('utf-8')
            public_key.verify(proof.signature, message, ec.ECDSA(hashes.SHA256()))
            
            # Verify hash
            computed_hash = hashlib.sha256(proof.signature).digest()
            return computed_hash == proof.hash_value
            
        except Exception as e:
            logger.error(f"VRF verification failed: {e}")
            return False

class CryptoManager:
    """Manages RSA encryption for user coordinates with hybrid identification"""
    
    def __init__(self):
        # Private keys are stored per Telegram user ID
        self.telegram_user_keys = {}  # telegram_user_id -> keys
        # But we also track which Solana addresses they use
        self.solana_mappings = {}  # telegram_user_id -> solana_address
    
    def generate_user_keys(self, telegram_user_id: int) -> rsa.RSAPublicKey:
        """Generate RSA key pair for a Telegram user"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        self.telegram_user_keys[telegram_user_id] = {
            'private': private_key,
            'public': public_key
        }
        
        logger.info(f"🔑 Generated encryption keys for Telegram user {telegram_user_id}")
        return public_key
    
    def set_solana_address(self, telegram_user_id: int, solana_address: str):
        """Associate a Solana address with a Telegram user"""
        self.solana_mappings[telegram_user_id] = solana_address
        logger.info(f"💰 Telegram user {telegram_user_id} linked to Solana address {solana_address[:8]}...{solana_address[-8:]}")
    
    def get_solana_address(self, telegram_user_id: int) -> Optional[str]:
        """Get Solana address for a Telegram user"""
        return self.solana_mappings.get(telegram_user_id)
    
    def encrypt_coordinates(self, telegram_user_id: int, coordinates: tuple) -> bytes:
        """Encrypt coordinates using user's RSA key"""
        if telegram_user_id not in self.telegram_user_keys:
            raise ValueError(f"No keys found for Telegram user {telegram_user_id}")
            
        public_key = self.telegram_user_keys[telegram_user_id]['public']
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
    
    def decrypt_coordinates(self, telegram_user_id: int, encrypted_data: bytes) -> tuple:
        """Decrypt coordinates using user's RSA key"""
        if telegram_user_id not in self.telegram_user_keys:
            raise ValueError(f"No keys found for Telegram user {telegram_user_id}")
            
        private_key = self.telegram_user_keys[telegram_user_id]['private']
        
        decrypted = private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return json.loads(decrypted.decode())
    
    def export_user_keys(self, telegram_user_id: int) -> Dict[str, str]:
        """Export user keys to PEM format"""
        if telegram_user_id not in self.telegram_user_keys:
            raise ValueError(f"No keys found for Telegram user {telegram_user_id}")

        private_key = self.telegram_user_keys[telegram_user_id]['private']
        public_key = self.telegram_user_keys[telegram_user_id]['public']

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        return {
            'private_key': private_key_pem,
            'public_key': public_key_pem,
            'solana_address': self.get_solana_address(telegram_user_id)
        }

    def import_user_keys(self, telegram_user_id: int, private_key_pem: str, 
                        solana_address: Optional[str] = None):
        """Import user keys from PEM format"""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        self.telegram_user_keys[telegram_user_id] = {
            'private': private_key,
            'public': public_key
        }
        
        if solana_address:
            self.set_solana_address(telegram_user_id, solana_address)
        
        logger.info(f"🔑 Imported keys for Telegram user {telegram_user_id}")

    def get_user_stats(self) -> Dict[str, Any]:
        """Get statistics about managed users"""
        return {
            'total_telegram_users': len(self.telegram_user_keys),
            'total_solana_addresses': len(set(self.solana_mappings.values())),
            'unique_mappings': len(self.solana_mappings)
        }
