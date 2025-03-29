import os
import flask
import logging
from flask import Flask, request, jsonify
import importlib

# Import the main module
import main

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Map of function names to their entry points
FUNCTION_MAP = {
    # Organization functions
    "relex-backend-create-organization": main.organization_create_organization,
    "relex-backend-get-organization": main.organization_get_organization,
    "relex-backend-add-organization-user": main.organization_add_organization_user,
    "relex-backend-set-user-role": main.organization_set_user_role,
    "relex-backend-update-organization": main.organization_update_organization,
    "relex-backend-list-organization-users": main.organization_list_organization_users,
    "relex-backend-remove-organization-user": main.organization_remove_organization_user,
    
    # Organization membership functions
    "relex-backend-add-organization-member": main.organization_membership_add_organization_member,
    "relex-backend-set-organization-member-role": main.organization_membership_set_organization_member_role, 
    "relex-backend-list-organization-members": main.organization_membership_list_organization_members,
    "relex-backend-remove-organization-member": main.organization_membership_remove_organization_member,
    "relex-backend-get-user-organization-role": main.organization_membership_get_user_organization_role,
    "relex-backend-list-user-organizations": main.organization_membership_list_user_organizations,
    
    # Chat functions
    "relex-backend-receive-prompt": main.chat_receive_prompt,
    "relex-backend-send-to-vertex-ai": main.chat_send_to_vertex_ai,
    "relex-backend-store-conversation": main.chat_store_conversation,
    "relex-backend-enrich-prompt": main.chat_enrich_prompt,
    
    # Payments functions
    "relex-backend-create-payment-intent": main.payments_create_payment_intent,
    "relex-backend-create-checkout-session": main.payments_create_checkout_session,
    "relex-backend-handle-stripe-webhook": main.payments_handle_stripe_webhook,
    "relex-backend-cancel-subscription": main.payments_cancel_subscription,
    
    # User functions
    "relex-backend-get-user-profile": main.user_get_profile,
    "relex-backend-update-user-profile": main.user_update_profile,
    
    # Case Management functions
    "relex-backend-create-case": main.cases_create_case,
    "relex-backend-get-case": main.cases_get_case,
    "relex-backend-list-cases": main.cases_list_cases,
    "relex-backend-archive-case": main.cases_archive_case,
    "relex-backend-delete-case": main.cases_delete_case,
    "relex-backend-upload-file": main.cases_upload_file,
    "relex-backend-download-file": main.cases_download_file,
    "relex-backend-attach-party": main.cases_attach_party,
    "relex-backend-detach-party": main.cases_detach_party,
    
    # Authentication functions
    "relex-backend-validate-user": main.auth_validate_user,
    "relex-backend-check-permissions": main.auth_check_permissions,
    "relex-backend-get-user-role": main.auth_get_user_role,
    
    # Party management functions
    "relex-backend-create-party": main.party_create_party,
    "relex-backend-get-party": main.party_get_party,
    "relex-backend-update-party": main.party_update_party,
    "relex-backend-delete-party": main.party_delete_party,
    "relex-backend-list-parties": main.party_list_parties,
}

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def function_handler(path):
    """Generic function handler that routes to the correct function"""
    # Get the Cloud Run service name from the environment
    service_name = os.environ.get('K_SERVICE', 'unknown')
    logger.info(f"Received request for service: {service_name}")
    
    # Get the correct function handler
    func = FUNCTION_MAP.get(service_name)
    if func:
        logger.info(f"Routing to function: {func.__name__}")
        return func(request)
    else:
        logger.error(f"Function not found for service: {service_name}")
        return jsonify({"error": f"Function not found for service: {service_name}"}), 404

if __name__ == '__main__':
    # Get the port from the environment or default to 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False) 