"""
P2P networking layer using ZeroMQ
"""
import asyncio
import json
import time
import hashlib
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
import zmq
import zmq.asyncio
from config.settings import (DEFAULT_P2P_PORT, HEARTBEAT_INTERVAL, 
                           PEER_TIMEOUT, MAX_PEERS)

logger = logging.getLogger(__name__)

@dataclass
class P2PMessage:
    """P2P message structure"""
    type: str
    sender_id: str
    recipient_id: str  # "broadcast" for all peers
    timestamp: float
    data: dict
    message_id: str = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = hashlib.sha256(
                f"{self.type}{self.sender_id}{self.timestamp}".encode()
            ).hexdigest()[:16]

@dataclass
class PeerInfo:
    """Information about a network peer"""
    node_id: str
    address: str
    port: int
    last_seen: float
    public_key: bytes = None
    is_authority: bool = False
    
    def is_alive(self) -> bool:
        return (time.time() - self.last_seen) < PEER_TIMEOUT

class P2PNetworkLayer:
    """Real P2P networking implementation using ZeroMQ"""
    
    def __init__(self, node_id: str, port: int = DEFAULT_P2P_PORT):
        self.node_id = node_id
        self.port = port
        self.context = zmq.asyncio.Context()
        
        # ZeroMQ sockets for different message types
        self.pub_socket = None  # Publisher for broadcasting
        self.sub_socket = None  # Subscriber for receiving broadcasts
        self.router_socket = None  # For direct peer communication
        self.dealer_socket = None  # For outgoing connections
        
        # Peer management
        self.peers: Dict[str, PeerInfo] = {}
        self.active_connections: Set[str] = set()
        self.message_handlers: Dict[str, callable] = {}
        self.seen_messages: Set[str] = set()
        
        # Network state
        self.is_running = False
        self.heartbeat_task = None
        self.message_processor_task = None
        
        logger.info(f"P2P Network Layer initialized for node {node_id} on port {port}")

    async def start(self):
        """Start the P2P network layer"""
        try:
            # Setup ZeroMQ sockets
            await self._setup_sockets()
            
            # Start background tasks
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.message_processor_task = asyncio.create_task(self._message_processor())
            
            self.is_running = True
            logger.info(f"P2P network started on port {self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start P2P network: {e}")
            await self.stop()

    async def _setup_sockets(self):
        """Setup ZeroMQ sockets for P2P communication"""
        # Publisher socket for broadcasting to all peers
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{self.port}")
        
        # Subscriber socket for receiving broadcasts
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"")  # Subscribe to all messages
        
        # Router socket for direct peer communication (server)
        self.router_socket = self.context.socket(zmq.ROUTER)
        self.router_socket.bind(f"tcp://*:{self.port + 1}")
        
        # Dealer socket for outgoing connections (client)
        self.dealer_socket = self.context.socket(zmq.DEALER)
        self.dealer_socket.setsockopt(zmq.IDENTITY, self.node_id.encode())
        
        logger.info("ZeroMQ sockets configured successfully")

    async def connect_to_peer(self, peer_address: str, peer_port: int, peer_id: str):
        """Connect to a specific peer"""
        try:
            peer_url = f"tcp://{peer_address}:{peer_port}"
            
            # Subscribe to peer's broadcasts
            self.sub_socket.connect(peer_url)
            
            # Connect dealer socket for direct communication
            self.dealer_socket.connect(f"tcp://{peer_address}:{peer_port + 1}")
            
            # Add peer to active connections
            peer_info = PeerInfo(
                node_id=peer_id,
                address=peer_address,
                port=peer_port,
                last_seen=time.time()
            )
            self.peers[peer_id] = peer_info
            self.active_connections.add(peer_id)
            
            logger.info(f"Connected to peer {peer_id} at {peer_address}:{peer_port}")
            
            # Send initial handshake
            await self.send_handshake(peer_id)
            
        except Exception as e:
            logger.error(f"Failed to connect to peer {peer_id}: {e}")

    async def send_handshake(self, peer_id: str):
        """Send handshake message to establish connection"""
        handshake_msg = P2PMessage(
            type="handshake",
            sender_id=self.node_id,
            recipient_id=peer_id,
            timestamp=time.time(),
            data={
                'node_id': self.node_id,
                'port': self.port,
                'version': '1.0.0'
            }
        )
        await self.send_direct_message(peer_id, handshake_msg)

    async def broadcast_message(self, message: P2PMessage):
        """Broadcast message to all connected peers"""
        try:
            message_bytes = json.dumps({
                'type': message.type,
                'sender_id': message.sender_id,
                'timestamp': message.timestamp,
                'data': message.data,
                'message_id': message.message_id
            }).encode()
            
            await self.pub_socket.send_multipart([
                message.type.encode(),  # Topic
                message_bytes  # Message data
            ])
            
            logger.debug(f"Broadcasted {message.type} message to all peers")
            
        except Exception as e:
            logger.error(f"Failed to broadcast message: {e}")

    async def send_direct_message(self, peer_id: str, message: P2PMessage):
        """Send direct message to specific peer"""
        try:
            message_data = {
                'type': message.type,
                'sender_id': message.sender_id,
                'recipient_id': message.recipient_id,
                'timestamp': message.timestamp,
                'data': message.data,
                'message_id': message.message_id
            }
            
            await self.dealer_socket.send_multipart([
                peer_id.encode(),
                json.dumps(message_data).encode()
            ])
            
            logger.debug(f"Sent {message.type} message to {peer_id}")
            
        except Exception as e:
            logger.error(f"Failed to send direct message to {peer_id}: {e}")

    async def _message_processor(self):
        """Process incoming messages from peers"""
        while self.is_running:
            try:
                # Check for broadcast messages
                if self.sub_socket.poll(timeout=100, flags=zmq.POLLIN):
                    topic, message_bytes = await self.sub_socket.recv_multipart()
                    await self._handle_broadcast_message(topic.decode(), message_bytes)
                
                # Check for direct messages
                if self.router_socket.poll(timeout=100, flags=zmq.POLLIN):
                    sender_id, message_bytes = await self.router_socket.recv_multipart()
                    await self._handle_direct_message(sender_id.decode(), message_bytes)
                    
                await asyncio.sleep(0.1)  # Prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in message processor: {e}")
                await asyncio.sleep(1)

    async def _handle_broadcast_message(self, topic: str, message_bytes: bytes):
        """Handle incoming broadcast message"""
        try:
            message_data = json.loads(message_bytes.decode())
            
            # Ignore our own messages
            if message_data['sender_id'] == self.node_id:
                return
            
            # Check for duplicate messages
            if message_data['message_id'] in self.seen_messages:
                return
            
            self.seen_messages.add(message_data['message_id'])
            
            # Update peer info
            sender_id = message_data['sender_id']
            if sender_id in self.peers:
                self.peers[sender_id].last_seen = time.time()
            
            # Handle message based on type
            message_type = message_data['type']
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](message_data)
                
            logger.debug(f"Processed broadcast message: {message_type} from {sender_id}")
            
        except Exception as e:
            logger.error(f"Error handling broadcast message: {e}")

    async def _handle_direct_message(self, sender_id: str, message_bytes: bytes):
        """Handle incoming direct message"""
        try:
            message_data = json.loads(message_bytes.decode())
            
            # Update peer info
            if sender_id in self.peers:
                self.peers[sender_id].last_seen = time.time()
            
            # Handle message based on type
            message_type = message_data['type']
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](message_data)
                
            logger.debug(f"Processed direct message: {message_type} from {sender_id}")
            
        except Exception as e:
            logger.error(f"Error handling direct message: {e}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages to maintain connections"""
        while self.is_running:
            try:
                # Send heartbeat to all peers
                heartbeat_msg = P2PMessage(
                    type="heartbeat",
                    sender_id=self.node_id,
                    recipient_id="broadcast",
                    timestamp=time.time(),
                    data={'status': 'alive'}
                )
                
                await self.broadcast_message(heartbeat_msg)
                
                # Clean up dead peers
                current_time = time.time()
                dead_peers = [
                    peer_id for peer_id, peer in self.peers.items()
                    if (current_time - peer.last_seen) > PEER_TIMEOUT
                ]
                
                for peer_id in dead_peers:
                    logger.info(f"Removing dead peer: {peer_id}")
                    del self.peers[peer_id]
                    self.active_connections.discard(peer_id)
                
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(HEARTBEAT_INTERVAL)

    def register_message_handler(self, message_type: str, handler: callable):
        """Register handler for specific message type"""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")

    async def discover_peers(self, bootstrap_addresses: List[Tuple[str, int, str]]):
        """Connect to bootstrap peers to join the network"""
        for address, port, peer_id in bootstrap_addresses:
            try:
                await self.connect_to_peer(address, port, peer_id)
                await asyncio.sleep(1)  # Stagger connections
            except Exception as e:
                logger.warning(f"Failed to connect to bootstrap peer {peer_id}: {e}")

    def get_active_peers(self) -> List[PeerInfo]:
        """Get list of currently active peers"""
        return [peer for peer in self.peers.values() if peer.is_alive()]

    async def stop(self):
        """Stop the P2P network layer"""
        self.is_running = False
        
        # Cancel background tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.message_processor_task:
            self.message_processor_task.cancel()
        
        # Close sockets
        if self.pub_socket:
            self.pub_socket.close()
        if self.sub_socket:
            self.sub_socket.close()
        if self.router_socket:
            self.router_socket.close()
        if self.dealer_socket:
            self.dealer_socket.close()
        
        # Terminate context
        self.context.term()
        
        logger.info("P2P network stopped")
