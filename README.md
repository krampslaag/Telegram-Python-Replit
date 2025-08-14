# Bikera Mining Bot

A GPS-based cryptocurrency mining Telegram bot with hybrid user identification system, blockchain persistence, and secure cross-session data continuity.

## Features

- **GPS-based Mining**: Location-based cryptocurrency mining with privacy protection
- **Hybrid User Identification**: Solana addresses for rewards, Telegram IDs for private keys
- **Blockchain Persistence**: Continuous blockchain state across restarts
- **Privacy Protection**: Coordinate obfuscation while preserving distance relationships
- **Cross-session Continuity**: Same Solana address maintains rewards and history
- **Security Isolation**: Private keys remain Telegram user-specific
- **P2P Network**: ZeroMQ-based peer-to-peer networking
- **Data Export**: Blockchain and coordinate data export functionality

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```
4. Set your Telegram bot token in `.env`
5. Run the bot:
   ```bash
   python main.py
   ```

## Environment Variables

- `TELEGRAM_TOKEN`: Your Telegram bot token (required)
- `SOLANA_RPC_URL`: Solana RPC endpoint (optional)
- `IMERA_TOKEN_CONTRACT`: Token contract address (optional)

## Architecture

### Hybrid User Identification System

The bot uses a dual identification system:
- **Solana Addresses**: For rewards, data persistence, and blockchain records
- **Telegram User IDs**: For private key management and encryption

This allows:
- Multiple Telegram users can use the same Solana address for rewards
- Private keys remain isolated per Telegram user
- Cross-session data continuity via Solana addresses
- Secure reward distribution while maintaining key security

### Privacy Protection

- GPS coordinates are obfuscated using geographic zones
- Distance relationships are preserved for mining calculations
- Real coordinates never stored in blockchain
- User privacy maintained throughout the mining process

### Mining Process

1. **10-minute intervals**: Users submit GPS coordinates
2. **Target distance**: Random distance generated each interval
3. **Winner determination**: User closest to target distance wins
4. **Blockchain recording**: Winner and obfuscated data recorded
5. **Reward distribution**: Rewards sent to Solana addresses

## Bot Commands

- `/start` - Initialize and get started
- `/help` - Show available commands
- `/address` - Set your Solana address
- `/location` - Submit GPS coordinates
- `/status` - Check current mining interval
- `/rewards` - View your mining statistics
- `/blockchain` - View blockchain statistics
- `/download_blockchain` - Export blockchain data
- `/download_coordinates` - Export coordinate data
- `/export_keys` - Export your private keys
- `/import_keys` - Import private keys

## Security Features

- RSA encryption for sensitive data
- VRF (Verifiable Random Function) for consensus
- Coordinate obfuscation for privacy
- Secure key management per Telegram user
- Blockchain integrity verification

## Data Storage

- `data/blockchain.json` - Blockchain state
- `data/user_data.json` - User addresses and mappings
- `data/user_logs/` - Individual user activity logs
- `logs/` - Application logs

## Network Architecture

The bot includes P2P networking capabilities using ZeroMQ:
- Peer discovery and connection management
- Message broadcasting and direct communication
- Consensus mechanisms for distributed operation
- Heartbeat monitoring for network health

## Development

The project follows a modular architecture:
- `config/` - Configuration and settings
- `core/` - Core blockchain, mining, and crypto functionality
- `network/` - P2P networking and consensus
- `bot/` - Telegram bot interface
- `storage/` - Data persistence and management

## License

This project is licensed under the MIT License.
