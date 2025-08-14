#!/bin/bash
# Deployment script for Bikera Mining Bot
# This script is used by Cloud Run deployment

# Set the PORT environment variable if not already set
export PORT=${PORT:-5000}

# Run the unified application
python run_app.py