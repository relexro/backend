import functions_framework
import flask
import logging
from flask import Request
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
from chat import (
    receive_prompt as logic_receive_prompt,
    send_to_vertex_ai as logic_send_to_vertex_ai,
    store_conversation as logic_store_conversation,
    enrich_prompt as logic_enrich_prompt
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

logging.basicConfig(level=logging.INFO)

def _authenticate_and_call(request: Request, logic_func, requires_auth=True):
    try:
        user_data = None
        auth_user_id = None
        if requires_auth:
            auth_user_data, status_code, error_message = get_authenticated_user(request)
            if status_code != 200:
                logging.warning(f"Authentication failed for {logic_func.__name__}: {error_message}")
                return flask.jsonify({"error": "Unauthorized", "message": error_message}), status_code
            auth_user_id = auth_user_data["userId"]
            setattr(request, 'user_id', auth_user_id)
            setattr(request, 'user_email', auth_user_data.get("email"))
            user_data = auth_user_data
        response = logic_func(request)
        if isinstance(response, tuple):
            return response
        elif isinstance(response, flask.Response):
            return response
        elif isinstance(response, dict) or response is None:
            return flask.jsonify(response), 200
        else:
            logging.error(f"Unexpected return type from {logic_func.__name__}: {type(response)}")
            return flask.jsonify({"error": "Internal Server Error", "message": "Invalid function response type"}), 500
    except Exception as e:
        logging.error(f"Error in function '{logic_func.__name__}': {str(e)}", exc_info=True)
        return flask.jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

@functions_framework.http
def relex_backend_create_case(request: Request):
    return _authenticate_and_call(request, logic_create_case)

@functions_framework.http
def relex_backend_get_case(request: Request):
    return _authenticate_and_call(request, logic_get_case)

@functions_framework.http
def relex_backend_list_cases(request: Request):
    return _authenticate_and_call(request, logic_list_cases)

@functions_framework.http
def relex_backend_archive_case(request: Request):
    return _authenticate_and_call(request, logic_archive_case)

@functions_framework.http
def relex_backend_delete_case(request: Request):
    return _authenticate_and_call(request, logic_delete_case)

@functions_framework.http
def relex_backend_upload_file(request: Request):
    return _authenticate_and_call(request, logic_upload_file)

@functions_framework.http
def relex_backend_download_file(request: Request):
    return _authenticate_and_call(request, logic_download_file)

@functions_framework.http
def relex_backend_attach_party(request: Request):
    return _authenticate_and_call(request, logic_attach_party)

@functions_framework.http
def relex_backend_detach_party(request: Request):
    return _authenticate_and_call(request, logic_detach_party)

@functions_framework.http
def relex_backend_validate_user(request: Request):
    return _authenticate_and_call(request, logic_validate_user, requires_auth=False)

@functions_framework.http
def relex_backend_check_permissions(request: Request):
    return _authenticate_and_call(request, logic_check_permissions, requires_auth=False)

@functions_framework.http
def relex_backend_get_user_role(request: Request):
    return _authenticate_and_call(request, logic_get_user_role)

@functions_framework.http
def relex_backend_create_organization(request: Request):
    return _authenticate_and_call(request, logic_create_organization)

@functions_framework.http
def relex_backend_get_organization(request: Request):
    return _authenticate_and_call(request, logic_get_organization)

@functions_framework.http
def relex_backend_update_organization(request: Request):
    return _authenticate_and_call(request, logic_update_organization)

@functions_framework.http
def relex_backend_delete_organization(request: Request):
    return _authenticate_and_call(request, logic_delete_organization)

@functions_framework.http
def relex_backend_receive_prompt(request: Request):
    return _authenticate_and_call(request, logic_receive_prompt)

@functions_framework.http
def relex_backend_send_to_vertex_ai(request: Request):
    return _authenticate_and_call(request, logic_send_to_vertex_ai)

@functions_framework.http
def relex_backend_store_conversation(request: Request):
    return _authenticate_and_call(request, logic_store_conversation)

@functions_framework.http
def relex_backend_enrich_prompt(request: Request):
    return _authenticate_and_call(request, logic_enrich_prompt)

@functions_framework.http
def relex_backend_create_payment_intent(request: Request):
    return _authenticate_and_call(request, logic_create_payment_intent)

@functions_framework.http
def relex_backend_create_checkout_session(request: Request):
    return _authenticate_and_call(request, logic_create_checkout_session)

@functions_framework.http
def relex_backend_handle_stripe_webhook(request: Request):
    return _authenticate_and_call(request, logic_handle_stripe_webhook, requires_auth=False)

@functions_framework.http
def relex_backend_cancel_subscription(request: Request):
    return _authenticate_and_call(request, logic_cancel_subscription)

@functions_framework.http
def relex_backend_add_organization_member(request: Request):
    return _authenticate_and_call(request, logic_add_organization_member)

@functions_framework.http
def relex_backend_set_organization_member_role(request: Request):
    return _authenticate_and_call(request, logic_set_organization_member_role)

@functions_framework.http
def relex_backend_list_organization_members(request: Request):
    return _authenticate_and_call(request, logic_list_organization_members)

@functions_framework.http
def relex_backend_remove_organization_member(request: Request):
    return _authenticate_and_call(request, logic_remove_organization_member)

@functions_framework.http
def relex_backend_get_user_organization_role(request: Request):
    return _authenticate_and_call(request, logic_get_user_organization_role)

@functions_framework.http
def relex_backend_list_user_organizations(request: Request):
    return _authenticate_and_call(request, logic_list_user_organizations)

@functions_framework.http
def relex_backend_get_user_profile(request: Request):
    return _authenticate_and_call(request, logic_get_user_profile)

@functions_framework.http
def relex_backend_update_user_profile(request: Request):
    return _authenticate_and_call(request, logic_update_user_profile)

@functions_framework.http
def relex_backend_create_party(request: Request):
    return _authenticate_and_call(request, logic_create_party)

@functions_framework.http
def relex_backend_get_party(request: Request):
    return _authenticate_and_call(request, logic_get_party)

@functions_framework.http
def relex_backend_update_party(request: Request):
    return _authenticate_and_call(request, logic_update_party)

@functions_framework.http
def relex_backend_delete_party(request: Request):
    return _authenticate_and_call(request, logic_delete_party)

@functions_framework.http
def relex_backend_list_parties(request: Request):
    return _authenticate_and_call(request, logic_list_parties)

@functions_framework.http
def relex_backend_list_organization_cases(request: Request):
    return _authenticate_and_call(request, logic_list_cases)

@functions_framework.http
def relex_backend_assign_case(request: Request):
    return _authenticate_and_call(request, logic_assign_case)

@functions_framework.http
def relex_backend_redeem_voucher(request: Request):
    return _authenticate_and_call(request, logic_redeem_voucher)

@functions_framework.http
def relex_backend_get_products(request: Request):
    try:
        return logic_get_products(request)
    except Exception as e:
        logging.error(f"Error in get_products: {str(e)}", exc_info=True)
        return ({"error": "Internal Server Error", "message": "An unexpected error occurred."}, 500)