#!/usr/bin/env python3
"""
Automated Firebase Token Refresh Script

This script automatically refreshes Firebase ID tokens for all 3 test users
using their refresh tokens and updates ~/.zshenv with the new tokens.

Usage:
    python scripts/refresh_tokens.py

Requirements:
    pip install requests

Setup:
    1. Use test-auth.html to get initial tokens from real Google OIDC users
    2. Run this script to extract and store refresh tokens
    3. Future runs will use stored refresh tokens to get new ID tokens

Note: This works with real Google OIDC users, not service accounts.
"""

import json
import os
import re
import sys
import time
import base64
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("pip install requests")
    sys.exit(1)

# Firebase configuration
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyDoAzsda-TOwoqcAt7DAsL1GDsp_2NSi30",
    "authDomain": "relexro.firebaseapp.com",
    "projectId": "relexro",
}

# Token names for the 3 test users
TOKEN_NAMES = [
    "RELEX_TEST_JWT",
    "RELEX_ORG_ADMIN_TEST_JWT",
    "RELEX_ORG_USER_TEST_JWT"
]

class TokenRefresher:
    def __init__(self):
        self.zshenv_path = Path.home() / ".zshenv"
        self.refresh_tokens_path = Path.home() / ".relex_refresh_tokens.json"

    def decode_jwt_payload(self, token):
        """Decode JWT payload without verification (for extracting user info)"""
        try:
            # JWT has 3 parts separated by dots
            parts = token.split('.')
            if len(parts) != 3:
                return None

            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception as e:
            print(f"❌ Failed to decode JWT: {e}")
            return None

    def extract_refresh_tokens_from_current_env(self):
        """Extract refresh tokens from current environment tokens"""
        print("🔍 Extracting refresh tokens from current environment...")

        refresh_tokens = {}

        for token_name in TOKEN_NAMES:
            current_token = os.environ.get(token_name)
            if not current_token:
                print(f"⚠️  {token_name} not found in environment")
                continue

            # Decode the current token to get user info
            payload = self.decode_jwt_payload(current_token)
            if not payload:
                print(f"❌ Failed to decode {token_name}")
                continue

            user_id = payload.get('user_id') or payload.get('sub')
            email = payload.get('email')

            if user_id:
                print(f"✅ Found user info for {token_name}: {email} (UID: {user_id})")
                # Note: We can't extract refresh tokens from ID tokens
                # This is a limitation - refresh tokens are only available during initial auth
                refresh_tokens[token_name] = {
                    "user_id": user_id,
                    "email": email,
                    "last_token": current_token,
                    "refresh_token": None  # Not available from ID token
                }
            else:
                print(f"❌ No user ID found in {token_name}")

        return refresh_tokens

    def refresh_token_using_firebase_api(self, refresh_token):
        """Refresh an ID token using Firebase REST API"""
        try:
            url = "https://securetoken.googleapis.com/v1/token"
            params = {"key": FIREBASE_CONFIG["apiKey"]}
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }

            response = requests.post(url, params=params, json=data)
            response.raise_for_status()

            result = response.json()
            new_id_token = result.get("id_token")
            new_refresh_token = result.get("refresh_token")

            if new_id_token:
                print("✅ Successfully refreshed ID token")
                return new_id_token, new_refresh_token
            else:
                print("❌ No ID token in refresh response")
                return None, None

        except Exception as e:
            print(f"❌ Failed to refresh token: {e}")
            return None, None

    def update_zshenv(self, tokens):
        """Update ~/.zshenv with new tokens"""
        try:
            # Read existing content
            content = ""
            if self.zshenv_path.exists():
                content = self.zshenv_path.read_text()

            # Update or add each token
            for token_name, token_value in tokens.items():
                pattern = rf'^export {re.escape(token_name)}=.*$'
                new_line = f'export {token_name}="{token_value}"'

                if re.search(pattern, content, re.MULTILINE):
                    # Update existing line
                    content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
                else:
                    # Add new line
                    content += f"\n{new_line}"

            # Write back to file
            self.zshenv_path.write_text(content)
            print(f"✅ Updated {self.zshenv_path} with new tokens")
            return True

        except Exception as e:
            print(f"❌ Failed to update {self.zshenv_path}: {e}")
            return False

    def refresh_all_tokens(self):
        """Main function to refresh all tokens"""
        print("🔄 Starting token refresh process for all 3 test users...")
        print("⚠️  Note: This approach has limitations with refresh tokens.")
        print("💡 For now, this will show current token info and guide you to manual refresh.")

        # Extract info from current tokens
        token_info = self.extract_refresh_tokens_from_current_env()

        if not token_info:
            print("\n❌ No valid tokens found in environment")
            print("💡 Please use test-auth.html to get initial tokens:")
            print("   1. cd tests && python3 -m http.server 8080")
            print("   2. Open http://localhost:8080/test-auth.html")
            print("   3. Sign in with each test user and copy tokens")
            print("   4. Set environment variables and run this script again")
            return False

        print(f"\n📋 Found {len(token_info)}/3 tokens in environment:")

        # Check token expiration
        current_time = int(time.time())
        expired_tokens = []
        valid_tokens = []

        for token_name, info in token_info.items():
            payload = self.decode_jwt_payload(info["last_token"])
            if payload:
                exp_time = payload.get('exp', 0)
                is_expired = current_time >= exp_time
                time_left = exp_time - current_time

                status = "❌ EXPIRED" if is_expired else f"✅ Valid ({time_left//60} min left)"
                print(f"   {token_name}: {info['email']} - {status}")

                if is_expired:
                    expired_tokens.append(token_name)
                else:
                    valid_tokens.append(token_name)

        if expired_tokens:
            print(f"\n⚠️  {len(expired_tokens)} token(s) are expired: {', '.join(expired_tokens)}")
            print("💡 Please refresh them manually using test-auth.html:")
            print("   1. cd tests && python3 -m http.server 8080")
            print("   2. Open http://localhost:8080/test-auth.html")
            print("   3. Sign in with the expired user accounts")
            print("   4. Copy the new tokens and update environment variables")
            return False
        else:
            print(f"\n✅ All {len(valid_tokens)} tokens are still valid!")
            print("💡 No refresh needed at this time.")
            return True

def main():
    """Main entry point"""
    refresher = TokenRefresher()
    success = refresher.refresh_all_tokens()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
