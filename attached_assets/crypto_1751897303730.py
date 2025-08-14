"""
Cryptography and VRF implementation
"""
import hashlib
import json
import logging
from dataclasses import dataclass
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
    """Manages RSA encryption for user coordinates"""
    
    def __init__(self):
        self.user_keys = {}
    
    def generate_user_keys(self, user_id):
        """Generate RSA key pair for a user"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        self.user_keys[user_id] = {
            'private': private_key,
            'public': public_key
        }
        
        return public_key
    
    def encrypt_coordinates(self, public_key, coordinates):
        """Encrypt coordinates using RSA"""
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
    
    def export_user_keys(self, user_id):
        """Export user keys to PEM format"""
        if user_id not in self.user_keys:
            raise ValueError("No keys found for this user.")

        private_key = self.user_keys[user_id]['private']
        public_key = self.user_keys[user_id]['public']

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
            'public_key': public_key_pem
        }

    def import_user_keys(self, user_id, private_key_pem):
        """Import user keys from PEM format"""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        self.user_keys[user_id] = {
            'private': private_key,
            'public': public_key
        }