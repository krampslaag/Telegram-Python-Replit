"""
Node Manager for distributed Telegram bot handling
Ensures only one node handles the bot per era (100 intervals)
"""
import os
import json
import time
import socket
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class NodeManager:
    """Manages node rotation for Telegram bot handling"""
    
    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or self._generate_node_id()
        self.nodes_file = "data/active_nodes.json"
        self.current_era = 1
        self.is_active_handler = False
        self.last_heartbeat = time.time()
        
    def _generate_node_id(self) -> str:
        """Generate unique node ID based on hostname and timestamp"""
        hostname = socket.gethostname()
        timestamp = int(time.time())
        return f"{hostname}_{timestamp}"
    
    def get_current_era(self, interval_count: int) -> int:
        """Calculate current era based on interval count"""
        return ((interval_count - 1) // 100) + 1 if interval_count > 0 else 1
    
    def register_node(self) -> bool:
        """Register this node in the active nodes list"""
        try:
            nodes = self._load_nodes()
            
            # Add or update this node
            nodes[self.node_id] = {
                'last_heartbeat': time.time(),
                'registered_at': time.time(),
                'hostname': socket.gethostname(),
                'status': 'active'
            }
            
            self._save_nodes(nodes)
            logger.info(f"Node {self.node_id} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register node: {e}")
            return False
    
    def update_heartbeat(self) -> bool:
        """Update node heartbeat to show it's still active"""
        try:
            nodes = self._load_nodes()
            
            if self.node_id in nodes:
                nodes[self.node_id]['last_heartbeat'] = time.time()
                nodes[self.node_id]['status'] = 'active'
                self._save_nodes(nodes)
                self.last_heartbeat = time.time()
                return True
            else:
                # Re-register if not found
                return self.register_node()
                
        except Exception as e:
            logger.error(f"Failed to update heartbeat: {e}")
            return False
    
    def get_active_nodes(self, timeout: int = 60) -> List[str]:
        """Get list of active nodes (heartbeat within timeout seconds)"""
        nodes = self._load_nodes()
        current_time = time.time()
        active_nodes = []
        
        for node_id, node_data in nodes.items():
            if current_time - node_data['last_heartbeat'] < timeout:
                active_nodes.append(node_id)
                
        return sorted(active_nodes)  # Sort for consistent ordering
    
    def should_handle_telegram(self, interval_count: int) -> Tuple[bool, str]:
        """Determine if this node should handle Telegram bot for current era"""
        current_era = self.get_current_era(interval_count)
        
        # Update heartbeat first
        self.update_heartbeat()
        
        # Get active nodes
        active_nodes = self.get_active_nodes()
        
        if not active_nodes:
            # No active nodes? Register and become handler
            self.register_node()
            return True, f"No active nodes found, {self.node_id} becoming handler"
        
        # Calculate which node should handle this era
        handler_index = (current_era - 1) % len(active_nodes)
        designated_handler = active_nodes[handler_index]
        
        should_handle = (designated_handler == self.node_id)
        
        # Log decision
        if should_handle:
            logger.info(f"Era {current_era}: Node {self.node_id} is the designated Telegram handler")
        else:
            logger.info(f"Era {current_era}: Node {designated_handler} is handling Telegram, not {self.node_id}")
        
        return should_handle, designated_handler
    
    def cleanup_inactive_nodes(self, timeout: int = 300) -> int:
        """Remove nodes that haven't sent heartbeat in timeout seconds"""
        try:
            nodes = self._load_nodes()
            current_time = time.time()
            removed_count = 0
            
            # Find inactive nodes
            inactive_nodes = []
            for node_id, node_data in nodes.items():
                if current_time - node_data['last_heartbeat'] > timeout:
                    inactive_nodes.append(node_id)
            
            # Remove inactive nodes
            for node_id in inactive_nodes:
                del nodes[node_id]
                removed_count += 1
                logger.info(f"Removed inactive node: {node_id}")
            
            if removed_count > 0:
                self._save_nodes(nodes)
                
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup inactive nodes: {e}")
            return 0
    
    def get_node_status(self) -> Dict:
        """Get current node status information"""
        nodes = self._load_nodes()
        active_nodes = self.get_active_nodes()
        
        return {
            'node_id': self.node_id,
            'total_nodes': len(nodes),
            'active_nodes': len(active_nodes),
            'is_registered': self.node_id in nodes,
            'is_active': self.node_id in active_nodes,
            'nodes': nodes
        }
    
    def _load_nodes(self) -> Dict:
        """Load nodes data from file"""
        try:
            if os.path.exists(self.nodes_file):
                with open(self.nodes_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load nodes file: {e}")
        
        return {}
    
    def _save_nodes(self, nodes: Dict) -> bool:
        """Save nodes data to file"""
        try:
            os.makedirs(os.path.dirname(self.nodes_file), exist_ok=True)
            
            # Atomic write
            temp_file = self.nodes_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(nodes, f, indent=2)
            
            os.rename(temp_file, self.nodes_file)
            return True
            
        except Exception as e:
            logger.error(f"Failed to save nodes file: {e}")
            return False