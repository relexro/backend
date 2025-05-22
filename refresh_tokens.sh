#!/bin/bash
# Quick token refresh script
# Usage: ./refresh_tokens.sh

set -e  # Exit on any error

echo "🔄 Refreshing all 3 Firebase JWT tokens..."
echo "   - RELEX_TEST_JWT"
echo "   - RELEX_ORG_ADMIN_TEST_JWT" 
echo "   - RELEX_ORG_USER_TEST_JWT"
echo

# Run the Python refresh script
python scripts/refresh_tokens.py

if [ $? -eq 0 ]; then
    echo
    echo "✅ Tokens refreshed successfully!"
    echo "💡 Loading new tokens into current shell..."
    
    # Source the updated environment
    source ~/.zshenv
    
    echo "✅ Environment updated!"
    echo
    echo "📋 Token status:"
    echo "   RELEX_TEST_JWT: ${#RELEX_TEST_JWT} characters"
    echo "   RELEX_ORG_ADMIN_TEST_JWT: ${#RELEX_ORG_ADMIN_TEST_JWT} characters"
    echo "   RELEX_ORG_USER_TEST_JWT: ${#RELEX_ORG_USER_TEST_JWT} characters"
    echo
    echo "🎉 Ready to run tests!"
else
    echo "❌ Token refresh failed!"
    exit 1
fi
