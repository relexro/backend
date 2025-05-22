#!/usr/bin/env python3
"""
Firebase ID Token Generation Script for Test Users

This script uses the Firebase Admin SDK to generate fresh ID tokens for
predefined test user UIDs.

Setup:
1. Ensure 'firebase-admin' is listed in your Python project's requirements.
   (It should already be in `functions/src/requirements.txt`).
2. Download your Firebase project's service account key JSON file and
   save it as 'firebase-service-account-key.json' in the project's root directory
   (i.e., the parent directory of this 'scripts' folder).
   You can get this from Firebase Console > Project Settings > Service accounts.
3. Update the `TEST_USER_CONFIGS` dictionary below with your actual test user UIDs.

Usage:
    python scripts/refresh_tokens.py

This script will:
1. Initialize Firebase Admin SDK using the service account key.
2. For each configured test user:
    a. Generate a custom token using their UID.
    b. Exchange the custom token for a Firebase ID token using a REST API call.
3. Print the export commands for setting the new ID tokens as environment variables.
4. Update the ~/.zshenv file with the new tokens.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import firebase_admin
    from firebase_admin import auth, credentials
except ImportError:
    print("❌ Missing dependency: firebase-admin")
    print("💡 Please install it: pip install firebase-admin")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ Missing dependency: requests")
    print("💡 Please install it: pip install requests")
    sys.exit(1)

# --- Configuration ---
# !!! IMPORTANT: Update these UIDs with your actual test user UIDs !!!
TEST_USER_CONFIGS = {
    "RELEX_TEST_JWT": {
        "uid": "your-regular-test-user-uid-here",  # Replace with actual UID
        "description": "Regular test user (e.g., george.poenaru@gmail.com)"
    },
    "RELEX_ORG_ADMIN_TEST_JWT": {
        "uid": "your-org-admin-test-user-uid-here",  # Replace with actual UID
        "description": "Organization admin user (e.g., admin@deev.ai)"
    },
    "RELEX_ORG_USER_TEST_JWT": {
        "uid": "your-org-staff-test-user-uid-here",  # Replace with actual UID
        "description": "Organization staff user (e.g., harmoniq.punk@gmail.com)"
    }
}

# Path to your Firebase service account key JSON file
# Assumes it's in the project root directory (parent of 'scripts/')
SERVICE_ACCOUNT_KEY_PATH = Path(__file__).resolve().parent.parent / "firebase-service-account-key.json"

# Firebase Web API Key (can be found in Firebase Console > Project Settings > General)
# This is a public, non-secret key.
FIREBASE_WEB_API_KEY = "AIzaSyDoAzsda-TOwoqcAt7DAsL1GDsp_2NSi30" # Replace with your actual Firebase Web API Key if different

ZSHENV_PATH = Path.home() / ".zshenv"
# --- End Configuration ---

def initialize_firebase_admin():
    """Initializes the Firebase Admin SDK."""
    if not SERVICE_ACCOUNT_KEY_PATH.exists():
        print(f"❌ Service account key not found at: {SERVICE_ACCOUNT_KEY_PATH}")
        print("💡 Please download it from Firebase Console and place it correctly.")
        sys.exit(1)
    try:
        cred = credentials.Certificate(str(SERVICE_ACCOUNT_KEY_PATH))
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin SDK initialized successfully.")
        return True
    except Exception as e:
        print(f"❌ Error initializing Firebase Admin SDK: {e}")
        sys.exit(1)

def generate_id_token(uid):
    """Generates a Firebase ID token for the given UID."""
    try:
        # Step 1: Create a custom token
        custom_token = auth.create_custom_token(uid)

        # Step 2: Exchange custom token for an ID token
        # This uses the Firebase Auth REST API for signing in with a custom token.
        rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_WEB_API_KEY}"
        payload = json.dumps({
            "token": custom_token,
            "returnSecureToken": True
        })
        headers = {"Content-Type": "application/json"}

        response = requests.post(rest_api_url, data=payload, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

        id_token = response.json().get("idToken")
        if not id_token:
            print(f"❌ Could not retrieve ID token for UID {uid} from response.")
            return None
        return id_token
    except firebase_admin.auth.FirebaseAuthError as e:
        print(f"❌ Firebase Auth error generating custom token for UID {uid}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error exchanging custom token for ID token for UID {uid}: {e}")
        if e.response is not None:
            print(f"   Response content: {e.response.text}")
    except Exception as e:
        print(f"❌ An unexpected error occurred generating token for UID {uid}: {e}")
    return None

def update_zshenv(tokens_to_update):
    """Updates or adds token export lines in ~/.zshenv."""
    try:
        content = ""
        if ZSHENV_PATH.exists():
            content = ZSHENV_PATH.read_text()

        for token_name, token_value in tokens_to_update.items():
            # Remove any existing old version of the token line to avoid duplicates
            content = re.sub(rf'^export {re.escape(token_name)}=.*\n?', '', content, flags=re.MULTILINE)
            # Add the new token export line
            content += f'\nexport {token_name}="{token_value}"'

        # Clean up potential multiple blank lines
        content = re.sub(r'\n\s*\n', '\n\n', content).strip() + '\n'

        ZSHENV_PATH.write_text(content)
        print(f"✅ Successfully updated {ZSHENV_PATH}")
        return True
    except Exception as e:
        print(f"❌ Failed to update {ZSHENV_PATH}: {e}")
        return False

def decode_jwt_payload_simple(token):
    """Decodes JWT payload without verification (for extracting basic info like exp)."""
    try:
        parts = token.split('.')
        if len(parts) != 3: return None
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4) # Pad if necessary
        decoded_payload = base64.urlsafe_b64decode(payload).decode('utf-8')
        return json.loads(decoded_payload)
    except Exception:
        return None

def main():
    print("🔄 Starting Firebase ID token generation process...")

    # Check if UIDs have been updated from placeholders
    placeholders_found = False
    for token_name, config in TEST_USER_CONFIGS.items():
        if "your-" in config["uid"] or "-here" in config["uid"]:
            print(f"⚠️ Placeholder UID found for {token_name}: \"{config['uid']}\".")
            placeholders_found = True
    if placeholders_found:
        print("‼️ Please update the UIDs in the TEST_USER_CONFIGS dictionary in this script before running.")
        sys.exit(1)


    if not FIREBASE_WEB_API_KEY or "AIzaS" not in FIREBASE_WEB_API_KEY:
         print(f"⚠️ Firebase Web API Key (FIREBASE_WEB_API_KEY) seems to be a placeholder or missing.")
         print("‼️ Please update it in this script (it's found in Firebase Console > Project Settings > General).")
         sys.exit(1)

    initialize_firebase_admin()

    new_tokens = {}
    print("\n✨ Generating new ID tokens:")
    for token_name, config in TEST_USER_CONFIGS.items():
        print(f"   Generating token for: {config['description']} (UID: {config['uid']})")
        id_token = generate_id_token(config['uid'])
        if id_token:
            new_tokens[token_name] = id_token
            print(f"   ✅ Successfully generated token for {token_name}")
        else:
            print(f"   ❌ Failed to generate token for {token_name}")

    if not new_tokens:
        print("\n❌ No tokens were generated. Exiting.")
        sys.exit(1)

    print("\n🔑 New Firebase ID Tokens (valid for 1 hour):")
    for token_name, token_value in new_tokens.items():
        print(f'   export {token_name}="{token_value}"')

    if update_zshenv(new_tokens):
        print(f"\n💡 Tokens have been written to {ZSHENV_PATH}.")
        print("   Run 'source ~/.zshenv' in your terminal to load them into your current session.")
    else:
        print(f"\n⚠️  Could not automatically update {ZSHENV_PATH}. Please set the exports manually.")

    print("\n📋 Verifying generated tokens (basic check):")
    current_time = int(time.time())
    for token_name, token_value in new_tokens.items():
        payload = decode_jwt_payload_simple(token_value)
        if payload and 'exp' in payload and 'uid' in payload:
            exp_time = payload['exp']
            time_left_seconds = exp_time - current_time
            time_left_minutes = time_left_seconds / 60
            print(f"   Token: {token_name}")
            print(f"     UID: {payload['uid']}")
            print(f"     Expires in: {time_left_minutes:.2f} minutes ({time_left_seconds} seconds)")
            if payload['uid'] != TEST_USER_CONFIGS[token_name]['uid']:
                print(f"     ⚠️ WARNING: Decoded UID ({payload['uid']}) does not match configured UID ({TEST_USER_CONFIGS[token_name]['uid']})")
        else:
            print(f"   Token: {token_name} - Could not decode or essential claims missing.")


    print("\n✅ Token generation process finished.")

if __name__ == "__main__":
    # Import base64 here if not already imported globally, for decode_jwt_payload_simple
    import base64
    main()
