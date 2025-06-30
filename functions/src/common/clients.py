# FILE: functions/src/common/clients.py
import os
import firebase_admin
from google.cloud import firestore, storage
import stripe

# This module provides lazily-initialized, singleton clients for external services.
# This prevents resource contention and timeouts during Cloud Function cold starts.

_firebase_app_initialized = False
_db_client = None
_storage_client = None
_stripe_initialized = False

def _initialize_firebase():
    """Initializes the Firebase app if it hasn't been already."""
    global _firebase_app_initialized
    if not _firebase_app_initialized:
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app()
        _firebase_app_initialized = True

def get_db_client():
    """Returns a singleton Firestore client, initializing it on first use."""
    global _db_client
    if _db_client is None:
        _initialize_firebase()
        _db_client = firestore.Client()
    return _db_client

def get_storage_client():
    """Returns a singleton Cloud Storage client, initializing it on first use."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client

def initialize_stripe():
    """Initializes the Stripe API key if it hasn't been already."""
    global _stripe_initialized
    if not _stripe_initialized:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        if not stripe.api_key:
            # This will be logged by the payments module if the key is missing
            pass
        _stripe_initialized = True

def get_secret(secret_name: str) -> str:
    """
    Retrieves a secret value from environment variables.
    Raises KeyError if the secret is not found.
    """
    value = os.environ.get(secret_name)
    if value is None:
        raise KeyError(f"Secret '{secret_name}' not found in environment variables.")
    return value 