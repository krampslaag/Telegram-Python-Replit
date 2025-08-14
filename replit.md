# Bikera Mining Bot

## Overview

The Bikera Mining Bot is a GPS-based cryptocurrency mining Telegram bot that implements a hybrid user identification system with blockchain persistence and privacy-preserving coordinate obfuscation. The system combines location-based mining mechanics with secure data handling and cross-session continuity.

## System Architecture

### Core Architecture Pattern
- **Hybrid User Identification**: Dual identification system using Telegram IDs for private keys and Solana addresses for rewards
- **Privacy-First Design**: Coordinate obfuscation while preserving distance relationships
- **Blockchain Persistence**: Continuous blockchain state across restarts
- **Modular Structure**: Clear separation of concerns with dedicated packages

### Technology Stack
- **Backend**: Python 3.x with asyncio
- **Bot Framework**: python-telegram-bot for Telegram integration
- **Cryptography**: RSA encryption, ECDSA for VRF implementation
- **Networking**: ZeroMQ for P2P communication
- **Data Storage**: JSON-based file storage with encryption
- **Blockchain**: Custom implementation with mining intervals

## Key Components

### 1. Hybrid User Identification System
- **Problem**: Need secure cross-session continuity while maintaining privacy
- **Solution**: Dual identification using Telegram IDs for encryption and Solana addresses for rewards
- **Benefits**: Multiple users can share Solana addresses while maintaining private key isolation

### 2. Privacy Protection Layer
- **Coordinate Obfuscation**: Transforms GPS coordinates into obfuscated values while preserving distance relationships
- **Geographic Zones**: Divides world into ~1km grid zones for privacy protection
- **User Identity Hashing**: Interval-specific user hashes prevent cross-interval correlation

### 3. Blockchain Implementation
- **Custom Blockchain**: Purpose-built for GPS mining with block rewards
- **State Persistence**: Automatic blockchain state recovery across restarts
- **Mining Intervals**: 10-minute intervals with distance-based winner determination

### 4. P2P Network Layer
- **ZeroMQ-based**: Asynchronous P2P communication
- **Consensus Mechanism**: VRF-based consensus for decentralized operation
- **Peer Discovery**: Automatic peer discovery and heartbeat system

### 5. Node Rotation System
- **Era-based Rotation**: Different nodes handle Telegram bot per era (every 100 intervals)
- **Automatic Failover**: If designated node fails, next active node takes over
- **Heartbeat System**: Nodes maintain heartbeat to track active status
- **Deterministic Assignment**: Era number determines which node handles Telegram bot

### 6. Telegram Bot Interface
- **Conversation Handlers**: Structured flows for address setup and location submission
- **Command System**: Comprehensive command set for user interaction
- **Real-time Updates**: Status updates and mining progress notifications

## Data Flow

### User Registration Flow
1. User starts bot with `/start` command
2. System generates RSA encryption keys for Telegram user ID
3. User sets Solana address via conversation handler
4. Hybrid identification established (Telegram ID + Solana address)

### Mining Process Flow
1. Mining interval starts (10-minute duration)
2. Users submit locations via Telegram
3. Coordinates are obfuscated while preserving distances
4. System calculates travel distances using obfuscated coordinates
5. Winner determined based on target distance proximity
6. Block created and added to blockchain
7. Rewards distributed to winner's Solana address

### Privacy Protection Flow
1. Real coordinates encrypted with user's private key
2. Coordinates obfuscated for network communication
3. Geographic zones used for additional privacy
4. Only obfuscated data stored on blockchain

## External Dependencies

### Core Dependencies
- `python-telegram-bot==20.7`: Telegram bot framework
- `cryptography==41.0.7`: RSA encryption and ECDSA
- `pyzmq==25.1.2`: ZeroMQ for P2P networking
- `python-dotenv==1.0.0`: Environment variable management

### Data Processing
- `pandas==2.1.4`: Data manipulation and analysis
- `numpy==1.26.2`: Numerical computations
- `colorlog==6.8.0`: Enhanced logging (optional)

### Blockchain Integration
- Solana RPC endpoint for blockchain interaction
- Custom token contract support (IMERA token)

## Deployment Strategy

### Environment Configuration
- **Required**: `TELEGRAM_TOKEN` for bot authentication
- **Optional**: `SOLANA_RPC_URL`, `IMERA_TOKEN_CONTRACT`
- **Mining Parameters**: Configurable interval duration, distance thresholds

### File Structure
```
data/
├── blockchain.json          # Blockchain state
├── user_data.json          # User addresses and interval count
└── user_logs/              # Individual user activity logs

logs/
└── blockchain_bot.log      # Application logs
```

### Startup Process
1. Load environment variables
2. Initialize logging and directories
3. Load existing blockchain state
4. Start Telegram bot with handlers
5. Begin mining loop with 10-minute intervals

### Security Considerations
- Private keys remain isolated per Telegram user
- Coordinate obfuscation prevents location tracking
- Cross-session data continuity via Solana addresses
- Encrypted local storage for sensitive data

## Changelog

```
Changelog:
- July 07, 2025. Initial setup
- July 07, 2025. Added PostgreSQL database integration with comprehensive schema
- July 07, 2025. Fixed deployment issues for Cloud Run deployment:
  * Added health check endpoint at root path (/)
  * Enhanced health check with database connectivity testing
  * Improved content negotiation for deployment health checks
  * Created start.py script for deployment configuration
  * Ensured proper host binding (0.0.0.0) for external traffic
- July 07, 2025. Resolved deployment configuration:
  * Created unified run_app.py that runs both Flask API and Telegram bot
  * Fixed port conflicts - Flask runs on port 8000 in development, PORT env in production
  * Updated start.py to handle both services for deployment
  * Created start.sh wrapper script for Replit deployment
  * Deployment command should be: bash start.sh or python start.py
- July 07, 2025. Fixed Telegram bot conflicts:
  * Separated development and production environments to prevent multiple bot instances
  * Created production_unified.py for deployment (runs both Flask and Telegram bot)
  * Created dev_flask_only.py for development (runs only Flask API)
  * Deployment uses: bash start.sh → production_unified.py
  * Development uses: dev_flask_only.py (no Telegram bot to avoid conflicts)
- July 08, 2025. Fixed Telegram bot lifecycle in deployment:
  * Removed blocking wait() call that prevented bot from running continuously
  * Changed daemon thread to non-daemon to prevent premature termination
  * Added automatic restart logic if bot crashes (30-second delay)
  * Bot now runs independently without blocking the main thread
  * Added keep-alive loop to ensure thread persistence
- July 21, 2025. Implemented blockchain integrity checking and proper interval/block tracking:
  * Added blockchain integrity verification on startup - verifies chain links and hashes
  * Bot now displays both interval number and block number in status command
  * Intervals reset at 100 while blocks keep stacking continuously
  * Blocks are saved to .era files every 100 blocks (epoch 1: blocks 1-100, epoch 2: blocks 101-200, etc.)
  * Status shows "blocks until reset" to track progress toward next interval reset
  * Mining loop handles interval counter reset at 100 and epoch saving every 100 blocks
- July 21, 2025. Implemented node rotation system for distributed Telegram bot handling:
  * Added NodeManager class that tracks active nodes with heartbeat system
  * Nodes rotate Telegram bot handling responsibility by era (every 100 intervals)
  * Each era deterministically assigns one node to handle Telegram commands
  * Non-designated nodes remain in standby mode with handlers disabled
  * Automatic failover if designated node becomes inactive
  * Heartbeat system cleans up inactive nodes after 5 minutes
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```