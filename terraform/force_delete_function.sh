#!/bin/bash

# Set text colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
PROJECT="relexro"
REGION="europe-west3"
FUNCTION_NAME=""

# Parse command line arguments
while getopts "p:r:f:" opt; do
  case $opt in
    p) PROJECT=$OPTARG ;;
    r) REGION=$OPTARG ;;
    f) FUNCTION_NAME=$OPTARG ;;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
  esac
done

if [ -z "$FUNCTION_NAME" ]; then
  echo "Function name is required. Usage: $0 -f function-name [-p project-id] [-r region]"
  exit 1
fi

echo -e "${GREEN}Attempting to force delete function: $FUNCTION_NAME${NC}"

# Get access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

# Function to irradiate API calls and return status code and response
# Args: method (e.g., GET), url, data (optional)
make_api_call() {
  local method=$1
  local url=$2
  local data=$3
  local response
  local status_code

  if [ -n "$data" ]; then
    response=$(curl -X "$method" "$url" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$data" \
      --silent --write-out "HTTPSTATUS:%{http_code}")
  else
    response=$(curl -X "$method" "$url" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      --silent --write-out "HTTPSTATUS:%{http_code}")
  fi

  # Extract status code and body
  status_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]\+" | cut -d':' -f2)
  body=$(echo "$response" | sed '$d')

  # Log outcome
  if [ "$status_code" -eq 200 ] || [ "$status_code" -eq 202 ] || [ "$status_code" -eq 204 ]; then
    echo -e "${GREEN}Success (HTTP $status_code)${NC}"
  elif [ "$status_code" -eq 404 ]; then
    echo -e "${YELLOW}Resource not found (HTTP $status_code), may already be deleted${NC}"
  else
    echo -e "${RED}Failed (HTTP $status_code): $body${NC}"
  fi

  echo "$body"
  return "$status_code"
}

# 1. Cancel ongoing Cloud Build jobs
echo -e "${YELLOW}1. Canceling ongoing Cloud Build jobs...${NC}"
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT/cloud-run-source-deploy/$FUNCTION_NAME"
BUILDS_URL="https://cloudbuild.googleapis.com/v1/projects/$PROJECT/builds?filter=images:\"$IMAGE_NAME\"+status=\"WORKING\""
BUILDS_RESPONSE=$(make_api_call "GET" "$BUILDS_URL")
BUILDS=$(echo "$BUILDS_RESPONSE" | jq -r '.builds[]?.id // empty')

for BUILD_ID in $BUILDS; do
  echo -e "${YELLOW}Canceling build: $BUILD_ID${NC}"
  CANCEL_URL="https://cloudbuild.googleapis.com/v1/projects/$PROJECT/builds/$BUILD_ID:cancel"
  make_api_call "POST" "$CANCEL_URL"
done
sleep 5  # Wait for cancellations to process

# 2. Delete Eventarc triggers
echo -e "${YELLOW}2. Deleting Eventarc triggers...${NC}"
TRIGGERS_URL="https://eventarc.googleapis.com/v1/projects/$PROJECT/locations/$REGION/triggers"
TRIGGERS_RESPONSE=$(make_api_call "GET" "$TRIGGERS_URL")
TRIGGERS=$(echo "$TRIGGERS_RESPONSE" | jq -r '.triggers[] | select(.destination.run.service == "'$FUNCTION_NAME'") | .name')

for TRIGGER_NAME in $TRIGGERS; do
  echo -e "${YELLOW}Deleting trigger: $TRIGGER_NAME${NC}"
  make_api_call "DELETE" "https://eventarc.googleapis.com/v1/$TRIGGER_NAME"
done
sleep 5  # Wait for deletions to process

# 3. Delete the Cloud Run service
echo -e "${YELLOW}3. Deleting Cloud Run service...${NC}"
CLOUD_RUN_URL="https://run.googleapis.com/v1/projects/$PROJECT/locations/$REGION/services/$FUNCTION_NAME"
make_api_call "DELETE" "$CLOUD_RUN_URL"
sleep 5

# 4. Remove IAM bindings from Cloud Run service
echo -e "${YELLOW}4. Removing IAM bindings from Cloud Run service...${NC}"
IAM_POLICY='{"policy": {"bindings": []}}'
make_api_call "POST" "$CLOUD_RUN_URL:setIamPolicy" "$IAM_POLICY"

# 5. Delete the function using Cloud Functions API
echo -e "${YELLOW}5. Deleting Cloud Function...${NC}"
FUNCTION_URL="https://cloudfunctions.googleapis.com/v2/projects/$PROJECT/locations/$REGION/functions/$FUNCTION_NAME"
make_api_call "DELETE" "$FUNCTION_URL"
sleep 5

# 6. Remove IAM bindings from the function
echo -e "${YELLOW}6. Removing IAM bindings from Cloud Function...${NC}"
make_api_call "POST" "$FUNCTION_URL:setIamPolicy" "$IAM_POLICY"

# 7. Delete any associated revisions in Cloud Run
echo -e "${YELLOW}7. Deleting Cloud Run revisions...${NC}"
REVISIONS_URL="https://run.googleapis.com/v1/projects/$PROJECT/locations/$REGION/services/$FUNCTION_NAME/revisions"
REVISIONS_RESPONSE=$(make_api_call "GET" "$REVISIONS_URL")
REVISIONS=$(echo "$REVISIONS_RESPONSE" | jq -r '.items[]?.metadata.name // empty')

for REVISION in $REVISIONS; do
  echo -e "${YELLOW}Deleting revision: $REVISION${NC}"
  make_api_call "DELETE" "https://run.googleapis.com/v1/$REVISION"
done

echo -e "${GREEN}Force deletion attempts completed for $FUNCTION_NAME${NC}"
echo -e "${YELLOW}Note: Some operations are asynchronous.${NC}"
echo -e "${YELLOW}Verify cleanup in the Cloud Console under Cloud Functions, Cloud Run, Cloud Build, and Eventarc.${NC}"