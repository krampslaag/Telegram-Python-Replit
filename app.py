#!/usr/bin/env python3
"""
Web interface for Bikera Mining Bot
Provides a simple web dashboard for monitoring the bot status
"""
import os
import asyncio
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from threading import Thread
import time

# Import the main bot functionality
from main import main as bot_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bikera-mining-bot-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

# Initialize database with app
db.init_app(app)

# Global variables to track bot status
bot_status = {
    'running': False,
    'start_time': None,
    'current_interval': 0,
    'target_distance': 0.0,
    'participants': 0,
    'total_blocks': 0,
    'last_update': None
}

def run_bot():
    """Run the bot in a separate thread"""
    try:
        bot_status['running'] = True
        bot_status['start_time'] = datetime.now()
        
        # Run the bot
        asyncio.run(bot_main())
        
    except Exception as e:
        logger.error(f"Bot error: {e}")
        bot_status['running'] = False
    finally:
        bot_status['running'] = False

@app.route('/')
def index():
    """Main dashboard page - also serves as health check for deployment"""
    # Check if this is a health check request (deployment systems often use specific user agents)
    user_agent = request.headers.get('User-Agent', '')
    accept_header = request.headers.get('Accept', '')
    
    # Health check conditions: JSON accept header, health query param, or known deployment user agents
    is_health_check = (
        'application/json' in accept_header or
        request.args.get('health') == 'true' or
        'kube-probe' in user_agent.lower() or
        'googlehc' in user_agent.lower() or
        'cloud-run' in user_agent.lower()
    )
    
    if is_health_check:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        }), 200
    
    # In production, serve the React app
    if os.environ.get('PRODUCTION'):
        try:
            return send_from_directory('dist', 'index.html')
        except Exception as e:
            logger.error(f"Failed to serve React app: {e}")
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'message': 'Frontend not built, please run npm run build'
            }), 200
    
    # In development, serve the dashboard template
    try:
        return render_template('index.html', status=bot_status)
    except Exception as e:
        # Fallback to JSON response if template rendering fails
        logger.error(f"Template rendering failed: {e}")
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'message': 'Dashboard template not found, serving API response'
        }), 200

@app.route('/api/status')
def api_status():
    """API endpoint for bot status"""
    # Get database statistics
    try:
        from database_service import get_database_service
        db_service = get_database_service()
        db_stats = db_service.get_blockchain_stats()
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        db_stats = {}
    
    return jsonify({
        'status': 'running' if bot_status['running'] else 'stopped',
        'start_time': bot_status['start_time'].isoformat() if bot_status['start_time'] else None,
        'uptime': str(datetime.now() - bot_status['start_time']) if bot_status['start_time'] else None,
        'current_interval': bot_status['current_interval'],
        'target_distance': bot_status['target_distance'],
        'participants': bot_status['participants'],
        'total_blocks': bot_status['total_blocks'],
        'last_update': bot_status['last_update'].isoformat() if bot_status['last_update'] else None,
        'database_stats': db_stats
    })

@app.route('/api/blockchain')
def api_blockchain():
    """API endpoint for blockchain data"""
    try:
        from database_service import get_database_service
        db_service = get_database_service()
        stats = db_service.get_blockchain_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting blockchain data: {e}")
        return jsonify({'error': 'Failed to get blockchain data'}), 500

@app.route('/api/users')
def api_users():
    """API endpoint for user statistics"""
    try:
        from database_service import get_database_service
        db_service = get_database_service()
        session = db_service.get_db_session()
        
        from models import User
        users = session.query(User).all()
        
        user_data = []
        for user in users:
            user_stats = db_service.get_user_mining_stats(user.id)
            user_data.append({
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'solana_address': user.solana_address,
                'created_at': user.created_at.isoformat(),
                'is_active': user.is_active,
                'stats': user_stats
            })
        
        session.close()
        return jsonify(user_data)
        
    except Exception as e:
        logger.error(f"Error getting user data: {e}")
        return jsonify({'error': 'Failed to get user data'}), 500

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
    """Health check endpoint for deployment"""
    try:
        # Test database connection
        from database_service import get_database_service
        db_service = get_database_service()
        db_service.get_db_session().close()
        db_healthy = True
    except Exception as e:
        logger.error(f"Health check - Database error: {e}")
        db_healthy = False
    
    # Overall health status
    healthy = db_healthy
    
    return jsonify({
        'status': 'healthy' if healthy else 'unhealthy',
        'bot_running': bot_status['running'],
        'database_healthy': db_healthy,
        'timestamp': datetime.now().isoformat(),
        'uptime': str(datetime.now() - bot_status['start_time']) if bot_status['start_time'] else None
    }), 200 if healthy else 503

# Serve static files in production
if os.environ.get('PRODUCTION'):
    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files in production"""
        try:
            return send_from_directory('dist', path)
        except:
            # If file not found, serve index.html for client-side routing
            return send_from_directory('dist', 'index.html')

if __name__ == '__main__':
    # Initialize database tables
    with app.app_context():
        from models import User, Location, Block, MiningRecord, P2PNode
        db.create_all()
        logger.info("Database tables created successfully")
    
    # Start bot in background thread
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # In production, run on the PORT provided by the deployment platform
    # In development, run on port 8000
    if os.environ.get('PRODUCTION'):
        port = int(os.environ.get('PORT', 5000))
    else:
        port = int(os.environ.get('BACKEND_PORT', 8000))
    
    logger.info(f"Starting Flask app on port {port} (Production: {os.environ.get('PRODUCTION', 'false')})")
    app.run(host='0.0.0.0', port=port, debug=False)