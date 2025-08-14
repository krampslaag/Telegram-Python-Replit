# IMPORTANT: Deployment Instructions for Bikera Mining Bot

## The Telegram Bot Conflict Issue

You're seeing "Conflict: terminated by other getUpdates request" errors because:
- Multiple deployment instances are trying to use the same Telegram bot token
- Each Telegram bot can only have ONE active connection at a time

## Solution

### 1. Stop All Existing Deployments
Before deploying a new version, ensure all previous deployments are stopped.

### 2. Use the Correct Deployment Command
In Replit deployment settings, set the run command to:
```
bash start.sh
```

### 3. The Deployment Will:
- Wait 5 seconds for previous instances to shut down
- Retry up to 3 times if conflicts occur
- Run both Flask API (port 5000) and Telegram bot

### 4. Development Environment
- The local development environment runs ONLY the Flask API
- NO Telegram bot runs locally (to avoid conflicts)
- This is by design to prevent the conflict errors

## Architecture

**Development:**
- `Flask Dev` workflow → `dev_flask_only.py` → Flask API only (port 8000)

**Production:**
- `bash start.sh` → `production_unified.py` → Flask API + Telegram bot

## If Conflicts Persist

1. Check if you have multiple deployments running
2. Stop all deployments and wait 1 minute
3. Deploy only one instance
4. The production script includes retry logic to handle temporary conflicts

## Testing

- **Local:** Test the web dashboard at http://localhost:5000
- **Production:** Both web dashboard and Telegram bot will work