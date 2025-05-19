import functions_framework
import flask
import logging
import os
from dotenv import load_dotenv
from flask import Request
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

from auth import (
    validate_user as logic_validate_user,
    check_permissions as logic_check_permissions,
    get_user_role as logic_get_user_role,
    get_authenticated_user
)
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
from organization import (
    create_organization as logic_create_organization,
    get_organization as logic_get_organization,
    update_organization as logic_update_organization,
    delete_organization as logic_delete_organization
)

from payments import (
    create_payment_intent as logic_create_payment_intent,
    create_checkout_session as logic_create_checkout_session,
    handle_stripe_webhook as logic_handle_stripe_webhook,
    cancel_subscription as logic_cancel_subscription,
    logic_redeem_voucher,
    logic_get_products
)
from organization_membership import (
    add_organization_member as logic_add_organization_member,
    set_organization_member_role as logic_set_organization_member_role,
    list_organization_members as logic_list_organization_members,
    remove_organization_member as logic_remove_organization_member,
    get_user_organization_role as logic_get_user_organization_role,
    list_user_organizations as logic_list_user_organizations
)
from user import (
    get_user_profile as logic_get_user_profile,
    update_user_profile as logic_update_user_profile
)
from party import (
    create_party as logic_create_party,
    get_party as logic_get_party,
    update_party as logic_update_party,
    delete_party as logic_delete_party,
    list_parties as logic_list_parties
)

from agent import handle_agent_request as logic_handle_agent_request

logging.basicConfig(level=logging.INFO)

# Decorator to add user context to request if available
def require_end_user_id(func):
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'end_user_id') or not request.end_user_id:
            logging.warning(f"Endpoint {request.path} requires end_user_id, but it was not available.")
            return flask.jsonify({"error": "Unauthorized: Valid end-user identity not available for this operation."}), 403
        return func(request, *args, **kwargs)
    wrapper._original_function = func # Preserve original for introspection if needed
    wrapper.__name__ = func.__name__ # Preserve name
    return wrapper

def _authenticate_and_call(request: Request, logic_function, *, needs_end_user_id_arg: bool = False, requires_auth: bool = True):
    """
    Authenticates the request using get_authenticated_user, then calls the logic_function.
    Passes end_user_id as the first argument to logic_function if needs_end_user_id_arg is True.
    Also sets request.end_user_id and request.end_user_email if available.
    """
    try:
        if not hasattr(request, 'method') or not hasattr(request, 'path'):
            logging.error("Invalid request object passed to _authenticate_and_call")
            return flask.jsonify({"error": "Internal Server Error", "message": "Invalid request object"}), 500

        # If the endpoint does not require authentication and does not need the end_user_id,
        # we can directly invoke the logic function.
        if not requires_auth and not needs_end_user_id_arg:
            try:
                return logic_function(request)
            except Exception as e:
                logging.error(f"Error executing logic_function {logic_function.__name__}: {str(e)}", exc_info=True)
                return flask.jsonify({"error": "Internal server error processing request"}), 500

        # Otherwise perform the authentication flow.
        auth_context, status_code, error_message = get_authenticated_user(request)  # from auth.py

        if error_message:
            return flask.jsonify({"error": error_message}), status_code

        if not auth_context:
            logging.error("Authentication context not properly established by get_authenticated_user.")
            return flask.jsonify({"error": "Internal authentication error"}), 500

        # Make end-user info available on the request object for general use or decorators
        request.end_user_id = auth_context.firebase_user_id
        request.end_user_email = auth_context.firebase_user_email
        request.end_user_locale = getattr(auth_context, "firebase_user_locale", None)
        request.gateway_sa_subject = getattr(auth_context, "gateway_sa_subject", None)

        logging.info(
            f"Request authenticated. End-user ID: {request.end_user_id}, Email: {request.end_user_email}, Locale: {request.end_user_locale}"
        )
        if request.gateway_sa_subject:
            logging.info(f"Request from Gateway SA: {request.gateway_sa_subject}")

        try:
            if needs_end_user_id_arg:
                if not request.end_user_id:
                    logging.error(
                        f"Logic function {logic_function.__name__} requires end_user_id, but it was not available from token claims."
                    )
                    return flask.jsonify({"error": "Unauthorized: End-user identity not available for this operation."}), 403
                return logic_function(request, request.end_user_id)
            else:
                return logic_function(request)
        except Exception as e:
            logging.error(f"Error executing logic_function {logic_function.__name__}: {str(e)}", exc_info=True)
            return flask.jsonify({"error": "Internal server error processing request"}), 500
    except Exception as e:
        logic_name = getattr(logic_function, '__name__', 'unknown')
        logging.error(f"Error in _authenticate_and_call for {logic_name}: {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

@functions_framework.http
def relex_backend_create_case(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_create_case: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_create_case",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_create_case)

@functions_framework.http
def relex_backend_get_case(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_get_case: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_get_case",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_get_case)

@functions_framework.http
def relex_backend_list_cases(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_list_cases: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_list_cases",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_list_cases)

@functions_framework.http
def relex_backend_archive_case(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_archive_case: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_archive_case",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_archive_case)

@functions_framework.http
def relex_backend_delete_case(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_delete_case: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_delete_case",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_delete_case)

@functions_framework.http
def relex_backend_upload_file(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_upload_file: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_upload_file",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_upload_file)

@functions_framework.http
def relex_backend_download_file(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_download_file: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_download_file",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_download_file)

@functions_framework.http
def relex_backend_attach_party(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_attach_party: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_attach_party",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_attach_party)

@functions_framework.http
def relex_backend_detach_party(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_detach_party: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_detach_party",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_detach_party)

@functions_framework.http
def relex_backend_validate_user(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_validate_user: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_validate_user",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_validate_user, requires_auth=False)

@functions_framework.http
def relex_backend_check_permissions(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_check_permissions: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_check_permissions",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_check_permissions, requires_auth=False)

@functions_framework.http
def relex_backend_get_user_role(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_get_user_role: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_get_user_role",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_get_user_role)

@functions_framework.http
def relex_backend_create_organization(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_create_organization: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_create_organization",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_create_organization)

@functions_framework.http
def relex_backend_get_organization(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_get_organization: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_get_organization",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_get_organization)

@functions_framework.http
def relex_backend_update_organization(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_update_organization: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_update_organization",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_update_organization)

@functions_framework.http
def relex_backend_delete_organization(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_delete_organization: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_delete_organization",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_delete_organization)

@functions_framework.http
def relex_backend_create_payment_intent(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_create_payment_intent: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_create_payment_intent",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_create_payment_intent)

@functions_framework.http
def relex_backend_create_checkout_session(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_create_checkout_session: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_create_checkout_session",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_create_checkout_session)

@functions_framework.http
def relex_backend_handle_stripe_webhook(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_handle_stripe_webhook: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_handle_stripe_webhook",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_handle_stripe_webhook, requires_auth=False)

@functions_framework.http
def relex_backend_cancel_subscription(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_cancel_subscription: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_cancel_subscription",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_cancel_subscription)

@functions_framework.http
def relex_backend_add_organization_member(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_add_organization_member: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_add_organization_member",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_add_organization_member)

@functions_framework.http
def relex_backend_set_organization_member_role(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_set_organization_member_role: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_set_organization_member_role",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_set_organization_member_role)

@functions_framework.http
def relex_backend_list_organization_members(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_list_organization_members: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_list_organization_members",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_list_organization_members)

@functions_framework.http
def relex_backend_remove_organization_member(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_remove_organization_member: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_remove_organization_member",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_remove_organization_member)

@functions_framework.http
def relex_backend_get_user_organization_role(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_get_user_organization_role: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_get_user_organization_role",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_get_user_organization_role)

@functions_framework.http
def relex_backend_list_user_organizations(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_list_user_organizations: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_list_user_organizations",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_list_user_organizations)

@functions_framework.http
def relex_backend_get_user_profile(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_get_user_profile: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_get_user_profile",
            "timestamp": datetime.now().isoformat()
        }), 200

    # Assumes logic_get_user_profile now expects (request, end_user_id)
    return _authenticate_and_call(request, logic_get_user_profile, needs_end_user_id_arg=True)

@functions_framework.http
def relex_backend_update_user_profile(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_update_user_profile: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_update_user_profile",
            "timestamp": datetime.now().isoformat()
        }), 200

    # Assumes logic_update_user_profile now expects (request, end_user_id)
    return _authenticate_and_call(request, logic_update_user_profile, needs_end_user_id_arg=True)

@functions_framework.http
def relex_backend_create_party(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_create_party: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_create_party",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_create_party)

@functions_framework.http
def relex_backend_get_party(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_get_party: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_get_party",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_get_party)

@functions_framework.http
def relex_backend_update_party(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_update_party: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_update_party",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_update_party)

@functions_framework.http
def relex_backend_delete_party(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_delete_party: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_delete_party",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_delete_party)

@functions_framework.http
def relex_backend_list_parties(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_list_parties: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_list_parties",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_list_parties)

@functions_framework.http
def relex_backend_list_organization_cases(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_list_organization_cases: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_list_organization_cases",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_list_cases)

@functions_framework.http
def relex_backend_assign_case(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_assign_case: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_assign_case",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_assign_case)

@functions_framework.http
def relex_backend_redeem_voucher(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_redeem_voucher: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_redeem_voucher",
            "timestamp": datetime.now().isoformat()
        }), 200

    return _authenticate_and_call(request, logic_redeem_voucher)

@functions_framework.http
def relex_backend_get_products(request: Request):
    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info(f"Function relex_backend_get_products: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_get_products",
            "timestamp": datetime.now().isoformat()
        }), 200

    try:
        return logic_get_products(request)
    except Exception as e:
        logging.error(f"Error in get_products: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "An unexpected error occurred."}, 500)

@functions_framework.http
def relex_backend_agent_handler(request: Request):
    """Cloud Function entry point for the agent handler.

    This function handles requests to the Lawyer AI Agent endpoint.
    It authenticates the user and delegates to the agent handler.
    """
    # Log request information for debugging
    logging.info(f"Agent handler received: {request.method} {request.path}")

    # Check for the X-Google-Health-Check header first
    if request.headers.get("X-Google-Health-Check"):
        logging.info("Function relex_backend_agent_handler: Responding to X-Google-Health-Check header.")
        return flask.jsonify({
            "status": "healthy",
            "message": "Service is running, health check via X-Google-Health-Check header successful.",
            "function_name": "relex_backend_agent_handler",
            "timestamp": datetime.now().isoformat()
        }), 200

    # If this is a normal request, process it through the agent handler
    return _authenticate_and_call(request, logic_handle_agent_request)