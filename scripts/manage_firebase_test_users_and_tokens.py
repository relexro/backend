#!/usr/bin/env python3
"""
Manages Firebase Authentication Test Users and Generates ID Tokens.

This script will:
1. Define test user personas (UID, email, description).
2. Use 'firebase-service-account-key.json' (expected in project root).
3. For each test user:
   - Check if the Firebase Auth user exists by UID.
   - If not, create the user with the specified UID and email.
   - Generate a Firebase custom token for the UID.
   - Exchange the custom token for a standard Firebase ID token.
4. Update ~/.zshenv with the new ID tokens.
"""
import json
import os
import re
import sys
import time
from pathlib import Path
import base64

try:
    import firebase_admin
    from firebase_admin import auth, credentials
except ImportError:
    print("❌ Missing dependency: firebase-admin. Please install it: pip install firebase-admin")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ Missing dependency: requests. Please install it: pip install requests")
    sys.exit(1)

# --- Configuration ---
TEST_USER_DEFINITIONS = {
    "RELEX_TEST_JWT": {
        "uid": "individual-test-acc-uid",
        "email": "individual@test.org",
        "display_name": "Individual Test Account",
        "description": "Individual Test Account (for non-organization specific tests)"
    },
    "RELEX_ORG_ADMIN_TEST_JWT": {
        "uid": "admin-test-acc-uid",
        "email": "admin@test.org",
        "display_name": "Admin Test Account",
        "description": "Organization Admin Test Account (for org admin role tests)"
    },
    "RELEX_ORG_USER_TEST_JWT": {
        "uid": "user-test-acc-uid",
        "email": "user@test.org",
        "display_name": "User Test Account",
        "description": "Organization User/Staff Test Account (for org staff role tests)"
    }
}

SERVICE_ACCOUNT_KEY_PATH = Path(__file__).resolve().parent.parent / "firebase-service-account-key.json"
FIREBASE_WEB_API_KEY = os.environ.get("FIREBASE_WEB_API_KEY", "AIzaSyDoAzsda-TOwoqcAt7DAsL1GDsp_2NSi30") # Default from test-auth.html

ZSHENV_PATH = Path.home() / ".zshenv"
# --- End Configuration ---

def initialize_firebase_admin():
    if not SERVICE_ACCOUNT_KEY_PATH.exists():
        print(f"❌ Service Account Key not found at: {SERVICE_ACCOUNT_KEY_PATH}")
        print("   Please download it from Firebase Console (Project Settings > Service accounts)")
        print("   and save it as 'firebase-service-account-key.json' in the project root (e.g., backend_folder/).")
        sys.exit(1)
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(SERVICE_ACCOUNT_KEY_PATH))
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK initialized successfully.")
        else:
            print("ℹ️ Firebase Admin SDK already initialized.")
        return True
    except Exception as e:
        print(f"❌ Error initializing Firebase Admin SDK: {e}")
        sys.exit(1)

def get_or_create_firebase_user(uid, email, display_name):
    try:
        user = auth.get_user(uid)
        print(f"   ℹ️  Found existing Firebase user: {user.uid} (Email: {user.email})")
        if user.email != email or user.display_name != display_name:
            auth.update_user(uid, email=email, display_name=display_name)
            print(f"   🔄 Updated user {uid} with email: {email}, display_name: {display_name}")
        return user
    except firebase_admin.auth.UserNotFoundError:
        print(f"   ✨ Creating new Firebase user: UID={uid}, Email={email}, Name={display_name}")
        try:
            user = auth.create_user(
                uid=uid, email=email, email_verified=True,
                display_name=display_name, disabled=False
            )
            print(f"   ✅ Successfully created Firebase user: {user.uid}")
            return user
        except Exception as e_create:
            print(f"   ❌ Error creating Firebase user {uid}: {e_create}")
            return None
    except Exception as e_get:
        print(f"   ❌ Error retrieving Firebase user {uid}: {e_get}")
        return None

def generate_id_token_for_user(uid):
    try:
        custom_token = auth.create_custom_token(uid)
        rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_WEB_API_KEY}"
        payload = json.dumps({"token": custom_token, "returnSecureToken": True})
        headers = {"Content-Type": "application/json"}
        response = requests.post(rest_api_url, data=payload, headers=headers)
        response.raise_for_status()
        id_token = response.json().get("idToken")
        if not id_token:
            print(f"   ❌ Could not retrieve ID token for UID {uid}.")
            return None
        print(f"   🔑 Successfully generated ID token for UID {uid}.")
        return id_token
    except Exception as e:
        print(f"   ❌ An unexpected error occurred generating ID token for UID {uid}: {e}")
        if hasattr(e, 'response') and e.response is not None: print(f"      Response: {e.response.text}")
        return None

def update_zshenv(tokens_to_update):
    try:
        content = ""
        if ZSHENV_PATH.exists(): content = ZSHENV_PATH.read_text()
        else: print(f"ℹ️  {ZSHENV_PATH} does not exist. Will create it.")
        for token_name, token_value in tokens_to_update.items():
            content = re.sub(rf'^export {re.escape(token_name)}=.*\n?', '', content, flags=re.MULTILINE)
            content += f'\nexport {token_name}="{token_value}"'
        content = re.sub(r'\n\s*\n', '\n\n', content).strip()
        if content: content += '\n'
        ZSHENV_PATH.write_text(content)
        print(f"✅ Successfully updated {ZSHENV_PATH}")
        return True
    except Exception as e:
        print(f"❌ Failed to update {ZSHENV_PATH}: {e}")
        return False

def decode_jwt_payload_simple(token):
    if not token: return None
    try:
        parts = token.split('.')
        if len(parts) != 3: return None
        payload = parts[1]; payload += '=' * (4 - len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload).decode('utf-8', errors='replace'))
    except Exception: return None

def main():
    print("🚀 Starting Firebase Test User and Token Management...")
    if not FIREBASE_WEB_API_KEY or "AIzaS" not in FIREBASE_WEB_API_KEY:
        print("‼️ ERROR: Firebase Web API Key (FIREBASE_WEB_API_KEY) appears to be invalid or missing.")
        sys.exit(1)
    initialize_firebase_admin()
    generated_tokens = {}
    for token_var_name, config in TEST_USER_DEFINITIONS.items():
        print(f"\n👤 Processing Test Persona: {config['description']}")
        firebase_user = get_or_create_firebase_user(config['uid'], config['email'], config['display_name'])
        if not firebase_user: continue
        id_token = generate_id_token_for_user(firebase_user.uid)
        if id_token: generated_tokens[token_var_name] = id_token
        else: print(f"   ❌ Failed to generate ID token for {token_var_name}")
    if not generated_tokens: print("\n❌ No ID tokens were generated. Exiting."); sys.exit(1)
    print("\n🔑 Generated Firebase ID Tokens (valid for 1 hour):")
    for name, val in generated_tokens.items():
        payload = decode_jwt_payload_simple(val)
        email = payload.get('email', 'N/A') if payload else 'N/A'
        uid = payload.get('user_id', payload.get('sub', 'N/A')) if payload else 'N/A'
        print(f"   Token: {name} (UID: {uid}, Email: {email})")
    if update_zshenv(generated_tokens):
        print(f"\n💡 Tokens written to {ZSHENV_PATH}. Run 'source ~/.zshenv' to load them.")
    else:
        print(f"\n⚠️  Could not update {ZSHENV_PATH}. Set exports manually.")
    print("\n✅ Process finished.")
if __name__ == "__main__": main()
