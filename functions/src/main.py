# FILE: functions/src/main.py
# A minimal function to test the baseline deployment environment.

import functions_framework
import firebase_admin
from firebase_admin import firestore
import logging
from flask import Request

# --- Corrected imports for cases and payments ---
from cases import (
    create_case as logic_create_case,
    get_case as logic_get_case,
    list_cases as logic_list_cases,
    archive_case as logic_archive_case,
    delete_case as logic_delete_case,
    upload_file as logic_upload_file,
    download_file as logic_download_file,
    attach_party_to_case as logic_attach_party,
    detach_party_from_case as logic_detach_party,
    logic_assign_case
)
from payments import (
    create_payment_intent as logic_create_payment_intent,
    create_checkout_session as logic_create_checkout_session,
    handle_stripe_webhook as logic_handle_stripe_webhook,
    cancel_subscription as logic_cancel_subscription,
    logic_redeem_voucher,
    get_products as logic_get_products
)
# ... other necessary imports ...

# Initialize logging once.
logging.basicConfig(level=logging.INFO)

# Initialize Firebase Admin once.
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

# --- Cloud Function HTTP entry points ---
@functions_framework.http
def relex_backend_create_case(request: Request):
    return logic_create_case(request)

@functions_framework.http
def relex_backend_get_case(request: Request):
    return logic_get_case(request)

@functions_framework.http
def relex_backend_list_cases(request: Request):
    return logic_list_cases(request)

@functions_framework.http
def relex_backend_archive_case(request: Request):
    return logic_archive_case(request)

@functions_framework.http
def relex_backend_delete_case(request: Request):
    return logic_delete_case(request)

@functions_framework.http
def relex_backend_upload_file(request: Request):
    return logic_upload_file(request)

@functions_framework.http
def relex_backend_download_file(request: Request):
    return logic_download_file(request)

@functions_framework.http
def relex_backend_attach_party(request: Request):
    return logic_attach_party(request)

@functions_framework.http
def relex_backend_detach_party(request: Request):
    return logic_detach_party(request)

@functions_framework.http
def relex_backend_assign_case(request: Request):
    return logic_assign_case(request)

@functions_framework.http
def relex_backend_create_payment_intent(request: Request):
    return logic_create_payment_intent(request)

@functions_framework.http
def relex_backend_create_checkout_session(request: Request):
    return logic_create_checkout_session(request)

@functions_framework.http
def relex_backend_handle_stripe_webhook(request: Request):
    return logic_handle_stripe_webhook(request)

@functions_framework.http
def relex_backend_cancel_subscription(request: Request):
    return logic_cancel_subscription(request)

@functions_framework.http
def relex_backend_redeem_voucher(request: Request):
    return logic_redeem_voucher(request)

@functions_framework.http
def relex_backend_get_products(request: Request):
    return logic_get_products(request)

# ... add all other required function entry points as needed ...

@functions_framework.http
def relex_backend_smoke_test(request):
    """
    A minimal HTTP function that attempts a single Firestore read.
    If this function deploys and runs, the base environment is healthy.
    """
    logging.info("Smoke Test function started.")
    try:
        db = firestore.client()
        # Attempt a basic, low-risk read operation.
        # This document does not need to exist. The call itself is the test.
        doc_ref = db.collection(u'smoke_test').document(u'test_doc')
        doc = doc_ref.get()
        logging.info("Firestore client connection appears to be successful.")
        return "Smoke Test Succeeded: Environment is stable.", 200
    except Exception as e:
        logging.error(f"Smoke Test Failed: Could not connect to Firestore. Error: {e}", exc_info=True)
        return "Smoke Test Failed: Could not initialize Firestore client.", 500