# Deployment Configuration for Bikera Mining Bot

## Important: Deployment Setup

### For Replit Deployment:

1. **Update Run Command in Deployment Settings:**
   - Change from: `Bash Start` 
   - To: `bash start.sh`

2. **Environment Variables to Set in Deployment:**
   ```
   DEPLOYMENT_MODE=production
   TELEGRAM_TOKEN=<your_telegram_bot_token>
   ```

3. **What Happens in Each Environment:**

   **Development (Local):**
   - Only Flask API runs (port 8000)
   - NO Telegram bot (to avoid conflicts)
   - Use `Flask Dev` workflow

   **Production (Deployment):**
   - Both Flask API and Telegram bot run
   - Flask API on PORT (usually 5000)
   - Telegram bot in background thread
   - Uses `production_unified.py`

4. **Files Used:**
   - `start.sh` → Entry point for deployment
   - `production_unified.py` → Runs both services in production
   - `dev_flask_only.py` → Development Flask-only server

## Troubleshooting

If you see "Conflict: terminated by other getUpdates request":
- This means multiple Telegram bot instances are running
- Make sure only ONE deployment is active
- The development environment should NOT run the Telegram bot

## Testing

- **Test Flask API locally:** Visit http://localhost:8000/api/status
- **Test Telegram bot:** Only works in production deployment