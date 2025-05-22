# Firebase Token Automation

This document explains how to set up automated refresh for all 3 Firebase JWT tokens used in testing.

## Problem

Firebase ID tokens expire after 1 hour, requiring manual refresh through the browser. This is time-consuming when running integration tests frequently.

## Solution

Automated token refresh using Firebase Admin SDK that:
- Generates fresh tokens for all 3 test users
- Updates ~/.zshenv automatically
- Can run on a schedule (cron job)
- Eliminates manual browser token copying

## Quick Setup

### 1. Install Dependencies

```bash
pip install firebase-admin requests
```

### 2. Initial Token Setup (Required First Time)

**Important**: Before setting up automation, you need to obtain initial tokens to get your test user UIDs:

```bash
# Navigate to tests directory
cd tests
python3 -m http.server 8080
# Open http://localhost:8080/test-auth.html in browser
# Sign in with each of your 3 test users and copy their tokens
```

Set the initial tokens:
```bash
export RELEX_TEST_JWT="your_initial_regular_user_token"
export RELEX_ORG_ADMIN_TEST_JWT="your_initial_org_admin_token"
export RELEX_ORG_USER_TEST_JWT="your_initial_org_user_token"
```

### 3. Run Setup Script

```bash
python scripts/setup_token_automation.py
```

This will guide you through:
- Setting up Firebase service account
- Finding your test user UIDs (from Firebase Console or existing tokens)
- Configuring the refresh script
- Setting up automatic refresh (optional)

### 4. Automated Refresh (After Setup)

```bash
./refresh_tokens.sh
```

**Note**: Once configured, the automation works independently and doesn't need existing valid tokens.

## Manual Setup (Alternative)

### 1. Download Service Account Key

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select project `relexro`
3. Go to Project Settings → Service accounts
4. Click "Generate new private key"
5. Save as `firebase-service-account-key.json` in project root

### 2. Find Test User UIDs

1. Go to Firebase Console → Authentication → Users
2. Find your 3 test users and copy their UIDs:
   - Regular test user (for `RELEX_TEST_JWT`)
   - Organization admin (for `RELEX_ORG_ADMIN_TEST_JWT`)
   - Organization staff (for `RELEX_ORG_USER_TEST_JWT`)

### 3. Update refresh_tokens.py

Edit `scripts/refresh_tokens.py` and replace the placeholder UIDs:

```python
USER_CONFIGS = {
    "RELEX_TEST_JWT": {
        "uid": "your-actual-test-user-uid",
        "description": "Regular test user (non-organization member)"
    },
    "RELEX_ORG_ADMIN_TEST_JWT": {
        "uid": "your-actual-org-admin-uid",
        "description": "Organization administrator user"
    },
    "RELEX_ORG_USER_TEST_JWT": {
        "uid": "your-actual-org-user-uid",
        "description": "Organization staff user"
    }
}
```

## Usage

### Manual Refresh (Recommended)

```bash
# Quick refresh all tokens
./refresh_tokens.sh

# Or run Python script directly
python scripts/refresh_tokens.py

# Load new tokens
source ~/.zshenv
```

### Automatic Refresh (Optional)

Set up a cron job to refresh tokens every 45 minutes:

```bash
# Edit crontab
crontab -e

# Add this line:
*/45 * * * * cd /path/to/relex/backend && python scripts/refresh_tokens.py >> /tmp/token_refresh.log 2>&1
```

### Check Token Status

```bash
echo "RELEX_TEST_JWT: ${#RELEX_TEST_JWT} characters"
echo "RELEX_ORG_ADMIN_TEST_JWT: ${#RELEX_ORG_ADMIN_TEST_JWT} characters"
echo "RELEX_ORG_USER_TEST_JWT: ${#RELEX_ORG_USER_TEST_JWT} characters"
```

## How It Works

1. **Firebase Admin SDK**: Uses service account to generate custom tokens
2. **Token Exchange**: Exchanges custom tokens for ID tokens via Firebase REST API
3. **Environment Update**: Updates ~/.zshenv with new tokens
4. **Automatic Loading**: Tokens are available in new shell sessions

## Token Lifecycle

- **Generation**: Custom tokens → ID tokens via Firebase API
- **Expiration**: ID tokens expire after 1 hour
- **Refresh**: Can be refreshed anytime before expiration
- **Storage**: Stored in ~/.zshenv for persistence

## Troubleshooting

### Service Account Issues

```bash
# Check if service account file exists
ls -la firebase-service-account-key.json

# Verify JSON format
python -c "import json; print('Valid JSON' if json.load(open('firebase-service-account-key.json')) else 'Invalid')"
```

### UID Issues

```bash
# Test with a single UID
python -c "
import firebase_admin
from firebase_admin import auth, credentials
cred = credentials.Certificate('firebase-service-account-key.json')
app = firebase_admin.initialize_app(cred)
token = auth.create_custom_token('your-uid-here')
print('Success:', len(token), 'bytes')
"
```

### Token Validation

```bash
# Test token with API
curl -H "Authorization: Bearer $RELEX_TEST_JWT" \
     https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/v1/users/me
```

## Benefits

- ✅ **No more manual browser token copying**
- ✅ **All 3 tokens refreshed automatically**
- ✅ **Can run on schedule (cron)**
- ✅ **Integrates with existing test workflow**
- ✅ **Tokens always fresh for testing**

## Files Created

- `scripts/refresh_tokens.py` - Main refresh script
- `scripts/setup_token_automation.py` - Setup helper
- `refresh_tokens.sh` - Quick manual refresh
- `firebase-service-account-key.json` - Service account credentials (you create this)

## Security Notes

- Service account key has admin privileges - keep secure
- Tokens are stored in ~/.zshenv (local file)
- Custom tokens can have longer expiration if needed
- Consider using environment-specific service accounts
