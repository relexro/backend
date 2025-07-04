import firebase_admin
from firebase_admin import auth, credentials
import os

def ensure_firebase_user(uid, email=None, display_name=None):
    """Ensure a Firebase user exists with the given UID. Create if not present."""
    # Initialize Firebase Admin if not already initialized
    try:
        firebase_admin.get_app()
    except ValueError:
        cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY", "firebase-service-account-key.json")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    try:
        user = auth.get_user(uid)
        return user
    except auth.UserNotFoundError:
        user = auth.create_user(
            uid=uid,
            email=email or f"{uid}@example.com",
            display_name=display_name or uid,
            email_verified=True
        )
        return user 