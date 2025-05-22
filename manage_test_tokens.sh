#!/bin/bash
# Manages Firebase test users and generates new ID tokens.

echo "🚀 Managing Firebase test users and generating tokens..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

python3 "${SCRIPT_DIR}/scripts/manage_firebase_test_users_and_tokens.py"

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Token management script completed successfully."
    echo "💡 Attempting to automatically source environment variables from ~/.zshenv..."
    if [ -f ~/.zshenv ]; then
        source ~/.zshenv
        echo "✅ ~/.zshenv sourced. New tokens should be available in this session."
    else
        echo "⚠️  ~/.zshenv not found. Please source it manually if it exists elsewhere or set tokens from the script's output."
    fi
else
    echo "❌ Token management script failed with exit code $EXIT_CODE. Check output above for errors."
    exit 1
fi
