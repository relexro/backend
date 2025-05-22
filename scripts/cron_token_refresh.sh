#!/bin/bash
# Cron job script for automatic token refresh every 10 minutes
# This script is designed to be run by cron

# Set up logging
LOG_FILE="/tmp/relex_token_refresh.log"
BACKEND_DIR="/Users/george/relex/backend"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Start logging
log "=== Starting token refresh cron job ==="

# Change to backend directory
cd "$BACKEND_DIR" || {
    log "ERROR: Failed to change to backend directory: $BACKEND_DIR"
    exit 1
}

# Source environment variables
source ~/.zshenv || {
    log "ERROR: Failed to source ~/.zshenv"
    exit 1
}

# Check if tokens exist
if [[ -z "$RELEX_TEST_JWT" || -z "$RELEX_ORG_ADMIN_TEST_JWT" || -z "$RELEX_ORG_USER_TEST_JWT" ]]; then
    log "ERROR: One or more JWT tokens are missing from environment"
    exit 1
fi

# Run the token refresh script
log "Running token refresh script..."
/Users/george/.pyenv/versions/3.10.17/bin/python scripts/refresh_tokens.py >> "$LOG_FILE" 2>&1

# Check the exit status
if [ $? -eq 0 ]; then
    log "✅ Token refresh completed successfully"
else
    log "❌ Token refresh failed"
    exit 1
fi

# For now, since we don't have automatic refresh capability,
# we'll just check token status and log warnings for expired tokens
log "Token status check completed"
log "=== Token refresh cron job finished ==="
