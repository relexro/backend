#!/bin/bash
# Unified deployment script for all Cloud Functions including PDF generation

# Stop on errors
set -e

# Configuration
PROJECT_ID="relexro"
REGION="europe-west1"
SOURCE_DIR="./src"
MEMORY="512MB"
TIMEOUT="180s"
MIN_INSTANCES=0
MAX_INSTANCES=50
CONCURRENCY=10
SERVICE_ACCOUNT="relex-backend@relexro.iam.gserviceaccount.com"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=======================================${NC}"
echo -e "${YELLOW}Deploying Cloud Functions to GCP${NC}"
echo -e "${YELLOW}=======================================${NC}"

# Function to deploy a Cloud Function
deploy_function() {
  local function_name=$1
  local entry_point=$2
  local memory=${3:-$MEMORY}
  local timeout=${4:-$TIMEOUT}
  local min_instances=${5:-$MIN_INSTANCES}
  local max_instances=${6:-$MAX_INSTANCES}
  local concurrency=${7:-$CONCURRENCY}
  
  echo -e "\n${YELLOW}Deploying function: ${function_name}${NC}"
  
  gcloud functions deploy $function_name \
    --gen2 \
    --region=$REGION \
    --runtime=python311 \
    --source=$SOURCE_DIR \
    --entry-point=$entry_point \
    --trigger-http \
    --allow-unauthenticated \
    --memory=$memory \
    --timeout=$timeout \
    --min-instances=$min_instances \
    --max-instances=$max_instances \
    --concurrency=$concurrency \
    --service-account=$SERVICE_ACCOUNT
    
  echo -e "${GREEN}✓ Function ${function_name} deployed successfully${NC}"
}

echo -e "\n${YELLOW}Deploying main backend functions...${NC}"

# Deploy the PDF generator function with higher memory and lower concurrency (since PDF generation is more resource-intensive)
deploy_function "pdf-generator" "relex_backend_agent_handler" "1024MB" "300s" 0 20 5

# Deploy other functions
deploy_function "agent-handler" "relex_backend_agent_handler" 
deploy_function "create-case" "relex_backend_create_case"
deploy_function "get-case" "relex_backend_get_case"
deploy_function "list-cases" "relex_backend_list_cases"
deploy_function "archive-case" "relex_backend_archive_case"
deploy_function "delete-case" "relex_backend_delete_case"
deploy_function "upload-file" "relex_backend_upload_file"
deploy_function "download-file" "relex_backend_download_file"
deploy_function "attach-party" "relex_backend_attach_party"
deploy_function "detach-party" "relex_backend_detach_party"
deploy_function "validate-user" "relex_backend_validate_user"
deploy_function "check-permissions" "relex_backend_check_permissions"
deploy_function "get-user-role" "relex_backend_get_user_role"
deploy_function "create-organization" "relex_backend_create_organization"
deploy_function "get-organization" "relex_backend_get_organization"
deploy_function "update-organization" "relex_backend_update_organization"
deploy_function "delete-organization" "relex_backend_delete_organization"
deploy_function "add-organization-member" "relex_backend_add_organization_member"
deploy_function "set-organization-member-role" "relex_backend_set_organization_member_role"
deploy_function "list-organization-members" "relex_backend_list_organization_members"
deploy_function "remove-organization-member" "relex_backend_remove_organization_member"
deploy_function "get-user-organization-role" "relex_backend_get_user_organization_role"
deploy_function "list-user-organizations" "relex_backend_list_user_organizations"
deploy_function "get-user-profile" "relex_backend_get_user_profile"
deploy_function "update-user-profile" "relex_backend_update_user_profile"
deploy_function "create-party" "relex_backend_create_party"
deploy_function "get-party" "relex_backend_get_party"
deploy_function "update-party" "relex_backend_update_party"
deploy_function "delete-party" "relex_backend_delete_party"
deploy_function "list-parties" "relex_backend_list_parties"
deploy_function "assign-case" "relex_backend_assign_case"
deploy_function "create-payment-intent" "relex_backend_create_payment_intent"
deploy_function "create-checkout-session" "relex_backend_create_checkout_session"
deploy_function "handle-stripe-webhook" "relex_backend_handle_stripe_webhook"
deploy_function "cancel-subscription" "relex_backend_cancel_subscription"
deploy_function "redeem-voucher" "relex_backend_redeem_voucher"
deploy_function "get-products" "relex_backend_get_products"

echo -e "\n${GREEN}=======================================${NC}"
echo -e "${GREEN}All functions deployed successfully${NC}"
echo -e "${GREEN}=======================================${NC}"

# Show the URLs
echo -e "\n${YELLOW}Function URLs:${NC}"
echo -e "${GREEN}PDF Generator:${NC} https://${REGION}-${PROJECT_ID}.cloudfunctions.net/pdf-generator"
echo -e "${GREEN}Agent Handler:${NC} https://${REGION}-${PROJECT_ID}.cloudfunctions.net/agent-handler" 