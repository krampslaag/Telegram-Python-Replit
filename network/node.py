"""
Network node implementation
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from network.p2p import P2PNetworkLayer
from network.consensus import ConsensusManager
from config.settings import DEFAULT_P2P_PORT, NODE_SYNC_INTERVAL

logger = logging.getLogger(__name__)

class NetworkNode:
    """Complete network node with P2P and consensus capabilities"""
    
    def __init__(self, node_id: str, port: int = DEFAULT_P2P_PORT):
        self.node_id = node_id
        self.port = port
        self.start_time = time.time()
        
        # Network components
        self.p2p_layer = P2PNetworkLayer(node_id, port)
        self.consensus_manager = ConsensusManager(self.p2p_layer)
        
        # Node state
        self.is_running = False
        self.sync_task = None
        self.bootstrap_peers = []
        
        # Register P2P message handlers
        self.p2p_layer.register_message_handler("node_info", self._handle_node_info)
        self.p2p_layer.register_message_handler("sync_request", self._handle_sync_request)
        
        logger.info(f"Network node {node_id} initialized on port {port}")

    async def start(self, bootstrap_peers: List[tuple] = None):
        """Start the network node"""
        try:
            self.bootstrap_peers = bootstrap_peers or []
            
            # Start P2P layer
            await self.p2p_layer.start()
            
            # Connect to bootstrap peers
            if self.bootstrap_peers:
                await self.p2p_layer.discover_peers(self.bootstrap_peers)
            
            # Start consensus
            await self.consensus_manager.start_consensus()
            
            # Start sync task
            self.sync_task = asyncio.create_task(self._sync_loop())
            
            self.is_running = True
            logger.info(f"Network node {self.node_id} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start network node: {e}")
            await self.stop()
            raise

    async def _sync_loop(self):
        """Periodic sync with peers"""
        while self.is_running:
            try:
                # Broadcast node info
                await self._broadcast_node_info()
                
                # Request sync from peers
                await self._request_sync()
                
                await asyncio.sleep(NODE_SYNC_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(30)

    async def _broadcast_node_info(self):
        """Broadcast node information to peers"""
        node_info = {
            'node_id': self.node_id,
            'port': self.port,
            'uptime': time.time() - self.start_time,
            'peer_count': len(self.p2p_layer.get_active_peers()),
            'consensus_stats': self.consensus_manager.get_consensus_stats()
        }
        
        from network.p2p import P2PMessage
        info_msg = P2PMessage(
            type="node_info",
            sender_id=self.node_id,
            recipient_id="broadcast",
            timestamp=time.time(),
            data=node_info
        )
        
        await self.p2p_layer.broadcast_message(info_msg)
        logger.debug(f"Broadcasted node info")

    async def _request_sync(self):
        """Request synchronization from peers"""
        from network.p2p import P2PMessage
        sync_msg = P2PMessage(
            type="sync_request",
            sender_id=self.node_id,
            recipient_id="broadcast",
            timestamp=time.time(),
            data={'request_type': 'full_sync'}
        )
        
        await self.p2p_layer.broadcast_message(sync_msg)
        logger.debug("Requested sync from peers")

    async def _handle_node_info(self, message_data: Dict[str, Any]):
        """Handle node info message"""
        sender_id = message_data['sender_id']
        node_info = message_data['data']
        
        logger.debug(f"Received node info from {sender_id}: {node_info['peer_count']} peers, uptime: {node_info['uptime']:.1f}s")

    async def _handle_sync_request(self, message_data: Dict[str, Any]):
        """Handle sync request from peer"""
        sender_id = message_data['sender_id']
        request_type = message_data['data']['request_type']
        
        logger.debug(f"Received sync request from {sender_id}: {request_type}")
        
        # Respond with our current state (simplified)
        await self._send_sync_response(sender_id)

    async def _send_sync_response(self, peer_id: str):
        """Send sync response to peer"""
        from network.p2p import P2PMessage
        sync_response = P2PMessage(
            type="sync_response",
            sender_id=self.node_id,
            recipient_id=peer_id,
            timestamp=time.time(),
            data={
                'node_id': self.node_id,
                'consensus_round': self.consensus_manager.current_round.round_number if self.consensus_manager.current_round else 0,
                'peer_count': len(self.p2p_layer.get_active_peers())
            }
        )
        
        await self.p2p_layer.send_direct_message(peer_id, sync_response)
        logger.debug(f"Sent sync response to {peer_id}")

    async def stop(self):
        """Stop the network node"""
        self.is_running = False
        
        # Cancel sync task
        if self.sync_task:
            self.sync_task.cancel()
        
        # Stop components
        await self.consensus_manager.stop()
        await self.p2p_layer.stop()
        
        logger.info(f"Network node {self.node_id} stopped")

    def get_network_stats(self) -> Dict[str, Any]:
        """Get comprehensive network statistics"""
        active_peers = self.p2p_layer.get_active_peers()
        
        return {
            'node_id': self.node_id,
            'port': self.port,
            'uptime': time.time() - self.start_time,
            'is_running': self.is_running,
            'active_peers': len(active_peers),
            'peer_list': [peer.node_id for peer in active_peers],
            'consensus_stats': self.consensus_manager.get_consensus_stats(),
            'bootstrap_peers': len(self.bootstrap_peers)
        }

    async def add_peer(self, peer_address: str, peer_port: int, peer_id: str):
        """Add a new peer to the network"""
        try:
            await self.p2p_layer.connect_to_peer(peer_address, peer_port, peer_id)
            logger.info(f"Added peer {peer_id} at {peer_address}:{peer_port}")
        except Exception as e:
            logger.error(f"Failed to add peer {peer_id}: {e}")
