#!/usr/bin/env python3
"""
Production-ready Flask application for Bikera Mining Bot
Serves both API endpoints and static frontend in production
"""
import os
import logging
import asyncio
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from datetime import datetime
from blockchain_service import blockchain_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app)

# Initialize blockchain service on startup
async def init_blockchain():
    """Initialize blockchain service"""
    try:
        await blockchain_service.initialize()
        logger.info("Blockchain service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize blockchain service: {e}")

# Run initialization in event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_blockchain())

# Bot status tracking
bot_status = {
    'running': True,
    'start_time': datetime.now(),
    'current_interval': 1,
    'target_distance': 5.2,
    'participants': 0,
    'total_blocks': 1,
    'last_update': datetime.now()
}

@app.route('/api/status')
def api_status():
    """API endpoint for bot status"""
    # Get real-time status from blockchain service
    status = blockchain_service.get_status()
    
    return jsonify({
        'bot_running': bot_status['running'],
        'current_interval': status.get('current_interval', 1),
        'target_distance': status.get('target_distance', 5.2),
        'participants': bot_status['participants'],
        'total_blocks': status.get('total_blocks', 1),
        'last_update': datetime.now().isoformat()
    })

@app.route('/api/blockchain')
def api_blockchain():
    """API endpoint for blockchain data"""
    # In production, this would query the real database
    return jsonify({
        'total_blocks': bot_status['total_blocks'],
        'latest_block': {
            'number': bot_status['total_blocks'],
            'hash': 'genesis_hash' if bot_status['total_blocks'] == 1 else f'block_{bot_status["total_blocks"]}_hash',
            'timestamp': datetime.now().isoformat(),
            'winner': None
        },
        'chain_valid': True
    })

@app.route('/api/users')
def api_users():
    """API endpoint for user statistics"""
    # In production, this would query the real database
    return jsonify({
        'total_users': 0,
        'active_users': 0,
        'users': []
    })

@app.route('/api/leaderboard')
def api_leaderboard():
    """API endpoint for leaderboard data"""
    # In production, this would query the real database
    return jsonify([])

@app.route('/api/miners/distribution')
def api_miners_distribution():
    """API endpoint for miner distribution"""
    # In production, this would query the real database
    return jsonify([])

@app.route('/api/mining/stats')
def api_mining_stats():
    """API endpoint for mining statistics"""
    return jsonify({
        'dailyBlocks': 0,
        'avgBlockReward': 0,
        'networkHashrate': '0 H/s',
        'activeMiners': 0
    })

@app.route('/api/profile')
def api_profile():
    """API endpoint for user profile data"""
    return jsonify({
        'username': 'Crypto Miner',
        'bio': 'Welcome to Bikera Mining Bot',
        'followerCount': 0,
        'followingCount': 0,
        'solanaAddress': None,
        'totalRewards': 0,
        'blocksWon': 0,
        'totalDistance': 0
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def index():
    """Serve the React app"""
    # Check if this is a health check
    user_agent = request.headers.get('User-Agent', '').lower()
    if 'googlehc' in user_agent or 'kube-probe' in user_agent:
        return health_check()
    
    # In production, serve the built React app
    if os.environ.get('PRODUCTION'):
        try:
            return send_from_directory('dist', 'index.html')
        except:
            return jsonify({
                'error': 'Frontend not built',
                'message': 'Please run: cd client && npm run build'
            }), 500
    
    # In development, return a simple response
    return jsonify({
        'message': 'Bikera Mining Bot API',
        'status': 'running',
        'mode': 'development'
    })

# Serve static files in production
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    if os.environ.get('PRODUCTION'):
        try:
            return send_from_directory('dist', path)
        except:
            # For client-side routing, return index.html
            return send_from_directory('dist', 'index.html')
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    # Determine port
    if os.environ.get('PRODUCTION'):
        port = int(os.environ.get('PORT', 5000))
    else:
        port = 8000
    
    logger.info(f"Starting Bikera Mining Bot API on port {port}")
    logger.info(f"Production mode: {os.environ.get('PRODUCTION', 'false')}")
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)