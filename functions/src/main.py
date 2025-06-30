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
    logic_get_products
)
# --- Additional logic imports (organization, party, membership, auth, user) ---
from organization import (
    create_organization as logic_create_organization,
    get_organization as logic_get_organization,
    update_organization as logic_update_organization,
    delete_organization as logic_delete_organization
)

from party import (
    create_party as logic_create_party,
    get_party as logic_get_party,
    update_party as logic_update_party,
    delete_party as logic_delete_party,
    list_parties as logic_list_parties
)

from organization_membership import (
    add_organization_member as logic_add_organization_member,
    set_organization_member_role as logic_set_org_member_role,
    list_organization_members as logic_list_organization_members,
    remove_organization_member as logic_remove_organization_member,
    get_user_organization_role as logic_get_user_organization_role,
    list_user_organizations as logic_list_user_organizations
)

from auth import (
    check_permissions as logic_check_permissions,
    validate_user as logic_validate_user,
    get_user_role as logic_get_user_role
)

from user import (
    get_user_profile as logic_get_user_profile,
    update_user_profile as logic_update_user_profile
)

from agent import handle_agent_request as logic_handle_agent_request

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

# --- Organization cases listing wrapper (uses existing list_cases logic) ---
@functions_framework.http
def relex_backend_list_organization_cases(request: Request):
    """Alias for list_cases; can filter by organizationId via query params."""
    return logic_list_cases(request)

@functions_framework.http
def relex_backend_create_organization(request: Request):
    return logic_create_organization(request)

@functions_framework.http
def relex_backend_get_organization(request: Request):
    return logic_get_organization(request)

@functions_framework.http
def relex_backend_update_organization(request: Request):
    return logic_update_organization(request)

@functions_framework.http
def relex_backend_delete_organization(request: Request):
    return logic_delete_organization(request)

# --- Party management ---
@functions_framework.http
def relex_backend_create_party(request: Request):
    return logic_create_party(request)

@functions_framework.http
def relex_backend_get_party(request: Request):
    return logic_get_party(request)

@functions_framework.http
def relex_backend_update_party(request: Request):
    return logic_update_party(request)

@functions_framework.http
def relex_backend_delete_party(request: Request):
    return logic_delete_party(request)

@functions_framework.http
def relex_backend_list_parties(request: Request):
    return logic_list_parties(request)

# --- Organization membership ---
@functions_framework.http
def relex_backend_add_organization_member(request: Request):
    return logic_add_organization_member(request)

@functions_framework.http
def relex_backend_set_organization_member_role(request: Request):
    return logic_set_org_member_role(request)

@functions_framework.http
def relex_backend_list_organization_members(request: Request):
    return logic_list_organization_members(request)

@functions_framework.http
def relex_backend_remove_organization_member(request: Request):
    return logic_remove_organization_member(request)

@functions_framework.http
def relex_backend_get_user_organization_role(request: Request):
    return logic_get_user_organization_role(request)

@functions_framework.http
def relex_backend_list_user_organizations(request: Request):
    return logic_list_user_organizations(request)

# --- Auth / Permissions ---
@functions_framework.http
def relex_backend_check_permissions(request: Request):
    return logic_check_permissions(request)

@functions_framework.http
def relex_backend_validate_user(request: Request):
    return logic_validate_user(request)

@functions_framework.http
def relex_backend_get_user_role(request: Request):
    return logic_get_user_role(request)

# --- User profile ---
@functions_framework.http
def relex_backend_get_user_profile(request: Request):
    user_id = getattr(request, 'end_user_id', None)
    return logic_get_user_profile(request, user_id)

@functions_framework.http
def relex_backend_update_user_profile(request: Request):
    user_id = getattr(request, 'end_user_id', None)
    return logic_update_user_profile(request, user_id)

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

@functions_framework.http
def relex_backend_agent_handler(request: Request):
    return logic_handle_agent_request(request)