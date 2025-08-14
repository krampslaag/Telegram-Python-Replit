"""
Consensus mechanisms for the P2P network
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from core.crypto import VRF, VRFProof
from network.p2p import P2PMessage, P2PNetworkLayer
from config.settings import CONSENSUS_ROUND_DURATION, MIN_NODES

logger = logging.getLogger(__name__)

@dataclass
class ConsensusRound:
    """Consensus round data"""
    round_number: int
    start_time: float
    duration: int
    participants: List[str]
    proposals: Dict[str, Any]
    votes: Dict[str, str]  # voter_id -> proposal_id
    is_complete: bool = False
    winner: Optional[str] = None

class ConsensusManager:
    """Manages consensus rounds and voting"""
    
    def __init__(self, network_layer: P2PNetworkLayer):
        self.network = network_layer
        self.vrf = VRF()
        self.node_id = network_layer.node_id
        
        # Consensus state
        self.current_round: Optional[ConsensusRound] = None
        self.round_counter = 0
        self.is_leader = False
        self.consensus_task = None
        
        # Register message handlers
        self.network.register_message_handler("consensus_proposal", self._handle_proposal)
        self.network.register_message_handler("consensus_vote", self._handle_vote)
        self.network.register_message_handler("consensus_result", self._handle_result)
        
        logger.info(f"Consensus manager initialized for node {self.node_id}")

    async def start_consensus(self):
        """Start consensus process"""
        if self.consensus_task:
            logger.warning("Consensus already running")
            return
            
        self.consensus_task = asyncio.create_task(self._consensus_loop())
        logger.info("Consensus process started")

    async def _consensus_loop(self):
        """Main consensus loop"""
        while True:
            try:
                active_peers = self.network.get_active_peers()
                
                # Check if we have enough nodes for consensus
                if len(active_peers) < MIN_NODES:
                    logger.info(f"Not enough nodes for consensus ({len(active_peers)}/{MIN_NODES})")
                    await asyncio.sleep(30)
                    continue
                
                # Start new consensus round
                await self._start_round()
                
                # Wait for round completion
                await asyncio.sleep(CONSENSUS_ROUND_DURATION)
                
                # Finalize round
                await self._finalize_round()
                
            except Exception as e:
                logger.error(f"Error in consensus loop: {e}")
                await asyncio.sleep(10)

    async def _start_round(self):
        """Start a new consensus round"""
        self.round_counter += 1
        active_peers = self.network.get_active_peers()
        
        # Create new round
        self.current_round = ConsensusRound(
            round_number=self.round_counter,
            start_time=time.time(),
            duration=CONSENSUS_ROUND_DURATION,
            participants=[peer.node_id for peer in active_peers] + [self.node_id],
            proposals={},
            votes={}
        )
        
        # Determine leader using VRF
        await self._elect_leader()
        
        logger.info(f"Started consensus round {self.round_counter}")
        logger.info(f"Participants: {len(self.current_round.participants)}")
        logger.info(f"Leader: {self.is_leader}")

    async def _elect_leader(self):
        """Elect round leader using VRF"""
        if not self.current_round:
            return
            
        # Create VRF proof
        seed = f"round_{self.current_round.round_number}_{int(self.current_round.start_time)}"
        proof = self.vrf.prove(seed, self.node_id)
        
        # For now, simple leader election (could be improved with proper VRF comparison)
        self.is_leader = True  # Simplified - each node can be leader
        
        if self.is_leader:
            logger.info(f"🎯 Node {self.node_id} elected as leader for round {self.current_round.round_number}")
            await self._make_proposal()

    async def _make_proposal(self):
        """Make a proposal as leader"""
        if not self.current_round or not self.is_leader:
            return
            
        proposal_data = {
            'round_number': self.current_round.round_number,
            'proposer': self.node_id,
            'timestamp': time.time(),
            'proposal_type': 'block_validation',
            'data': {
                'action': 'validate_interval',
                'interval_number': self.current_round.round_number
            }
        }
        
        # Store our proposal
        proposal_id = f"proposal_{self.node_id}_{self.current_round.round_number}"
        self.current_round.proposals[proposal_id] = proposal_data
        
        # Broadcast proposal
        proposal_msg = P2PMessage(
            type="consensus_proposal",
            sender_id=self.node_id,
            recipient_id="broadcast",
            timestamp=time.time(),
            data={
                'proposal_id': proposal_id,
                'proposal': proposal_data
            }
        )
        
        await self.network.broadcast_message(proposal_msg)
        logger.info(f"Broadcasted proposal {proposal_id}")

    async def _handle_proposal(self, message_data: Dict[str, Any]):
        """Handle incoming consensus proposal"""
        if not self.current_round:
            return
            
        proposal_id = message_data['data']['proposal_id']
        proposal = message_data['data']['proposal']
        
        # Store proposal
        self.current_round.proposals[proposal_id] = proposal
        
        # Vote on proposal (simplified voting - always approve for now)
        await self._vote_on_proposal(proposal_id, True)
        
        logger.info(f"Received proposal {proposal_id} from {message_data['sender_id']}")

    async def _vote_on_proposal(self, proposal_id: str, approve: bool):
        """Vote on a consensus proposal"""
        if not self.current_round:
            return
            
        vote_data = {
            'round_number': self.current_round.round_number,
            'voter': self.node_id,
            'proposal_id': proposal_id,
            'vote': 'approve' if approve else 'reject',
            'timestamp': time.time()
        }
        
        # Store our vote
        self.current_round.votes[self.node_id] = proposal_id
        
        # Broadcast vote
        vote_msg = P2PMessage(
            type="consensus_vote",
            sender_id=self.node_id,
            recipient_id="broadcast",
            timestamp=time.time(),
            data=vote_data
        )
        
        await self.network.broadcast_message(vote_msg)
        logger.info(f"Voted on proposal {proposal_id}: {vote_data['vote']}")

    async def _handle_vote(self, message_data: Dict[str, Any]):
        """Handle incoming consensus vote"""
        if not self.current_round:
            return
            
        vote_data = message_data['data']
        voter = vote_data['voter']
        proposal_id = vote_data['proposal_id']
        
        # Store vote
        self.current_round.votes[voter] = proposal_id
        
        logger.info(f"Received vote from {voter} for proposal {proposal_id}")

    async def _finalize_round(self):
        """Finalize consensus round"""
        if not self.current_round:
            return
            
        # Count votes
        vote_counts = {}
        for voter, proposal_id in self.current_round.votes.items():
            vote_counts[proposal_id] = vote_counts.get(proposal_id, 0) + 1
        
        # Determine winner
        if vote_counts:
            winner_proposal = max(vote_counts, key=vote_counts.get)
            self.current_round.winner = winner_proposal
            self.current_round.is_complete = True
            
            logger.info(f"Round {self.current_round.round_number} completed")
            logger.info(f"Winner: {winner_proposal} with {vote_counts[winner_proposal]} votes")
            
            # Broadcast result
            result_msg = P2PMessage(
                type="consensus_result",
                sender_id=self.node_id,
                recipient_id="broadcast",
                timestamp=time.time(),
                data={
                    'round_number': self.current_round.round_number,
                    'winner': winner_proposal,
                    'votes': vote_counts
                }
            )
            
            await self.network.broadcast_message(result_msg)
        else:
            logger.warning(f"No votes received for round {self.current_round.round_number}")

    async def _handle_result(self, message_data: Dict[str, Any]):
        """Handle consensus result"""
        result_data = message_data['data']
        round_number = result_data['round_number']
        winner = result_data['winner']
        
        logger.info(f"Received consensus result for round {round_number}: {winner}")

    async def stop(self):
        """Stop consensus process"""
        if self.consensus_task:
            self.consensus_task.cancel()
            self.consensus_task = None
        
        logger.info("Consensus process stopped")

    def get_consensus_stats(self) -> Dict[str, Any]:
        """Get consensus statistics"""
        return {
            'current_round': self.current_round.round_number if self.current_round else None,
            'is_leader': self.is_leader,
            'active_peers': len(self.network.get_active_peers()),
            'round_complete': self.current_round.is_complete if self.current_round else False
        }
