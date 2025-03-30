#!/bin/bash

# Set text colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Configuration ---
# Attempt to get project from gcloud config, default to 'relexro' if not set
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT" ]; then
  echo -e "${YELLOW}gcloud project not set, using default 'relexro'. Set with 'gcloud config set project YOUR_PROJECT_ID'${NC}"
  PROJECT="relexro"
fi
# Assuming region from original script/openapi_spec.yaml
REGION="europe-west1"

echo -e "${GREEN}Configuration:${NC}"
echo -e "Project: ${PROJECT}"
echo -e "Region:  ${REGION}"
echo "----------------------------------"

# --- Get List of All Functions ---
echo -e "${YELLOW}Fetching list of all Cloud Functions in '$REGION'...${NC}"
# Get the full resource name for accurate filtering later
FUNCTION_LIST=$(gcloud functions list --project "$PROJECT" --regions "$REGION" --format='value(name)')

if [ -z "$FUNCTION_LIST" ]; then
  echo -e "${YELLOW}No Cloud Functions found in project '$PROJECT' and region '$REGION'. Exiting.${NC}"
  exit 0
fi

echo -e "${GREEN}Found Functions:${NC}"
echo "$FUNCTION_LIST" # Displaying full names like projects/.../functions/...
echo "----------------------------------"

# --- Loop and Delete Each Function and Dependencies ---
echo -e "${YELLOW}Attempting to forcefully delete functions and related resources...${NC}"
echo -e "${YELLOW}This will attempt to delete dependencies first, then the function.${NC}"

TOTAL_FUNCTIONS=$(echo "$FUNCTION_LIST" | wc -l)
CURRENT_FUNCTION=0

while IFS= read -r full_function_name; do
  ((CURRENT_FUNCTION++))
  # Extract the short function name from the full resource path
  # e.g., projects/relexro/locations/europe-west3/functions/relex-backend-get-user-profile -> relex-backend-get-user-profile
  SHORT_FUNCTION_NAME=$(basename "$full_function_name")

  echo "======================================================================"
  echo -e "${YELLOW}Processing function ${CURRENT_FUNCTION} of ${TOTAL_FUNCTIONS}: $SHORT_FUNCTION_NAME${NC}"
  echo "(Full resource name: $full_function_name)"
  echo "======================================================================"

  # 1. (Optional but recommended) Cancel related Cloud Build jobs
  # Gen 2 functions use Cloud Build. Stuck builds can prevent deletion.
  # Filtering based on standard tags used by Cloud Functions deployment.
  echo -e "${YELLOW}[Step 1/4] Searching for and canceling related ongoing Cloud Build jobs...${NC}"
  # This filter targets standard build tags for Gen2 functions
  BUILD_FILTER="tags:'gcp-cloud-build-deploy-cloud-functions' AND tags:'gcf-gen2' AND tags:'$REGION' AND tags:'$SHORT_FUNCTION_NAME' AND status='WORKING'"

  ONGOING_BUILDS=$(gcloud builds list --project "$PROJECT" --filter="$BUILD_FILTER" --format='value(id)')
  if [ -n "$ONGOING_BUILDS" ]; then
    echo "   Found ongoing builds:"
    echo "$ONGOING_BUILDS"
    while IFS= read -r build_id; do
      echo -e "${YELLOW}   -> Canceling build: $build_id${NC}"
      gcloud builds cancel "$build_id" --project "$PROJECT" --quiet || echo -e "${RED}      Failed to cancel build $build_id (might have already finished or error occurred)${NC}"
    done <<< "$ONGOING_BUILDS"
    echo "   Waiting briefly for cancellations to register..."
    sleep 3 # Give cancellations a moment
  else
    echo "   No relevant ongoing Cloud Build jobs found."
  fi
  echo "----------------------------------"

  # 2. Delete associated Eventarc triggers
  # Triggers can prevent function deletion.
  echo -e "${YELLOW}[Step 2/4] Deleting associated Eventarc triggers...${NC}"
  # Use the full function name identifier for accurate destination filtering
  TRIGGER_FILTER="destination.cloudFunction=$full_function_name"
  TRIGGERS=$(gcloud eventarc triggers list --project "$PROJECT" --location="$REGION" --filter="$TRIGGER_FILTER" --format='value(name)')

  if [ -n "$TRIGGERS" ]; then
     echo "   Found Eventarc triggers:"
     echo "$TRIGGERS"
    while IFS= read -r trigger_name; do
      # Extract the trigger ID from the full name projects/.../triggers/trigger-id
      TRIGGER_ID=$(basename "$trigger_name")
      echo -e "${YELLOW}   -> Deleting trigger: $TRIGGER_ID${NC}"
      gcloud eventarc triggers delete "$TRIGGER_ID" --project "$PROJECT" --location="$REGION" --quiet || echo -e "${RED}      Failed to delete trigger $TRIGGER_ID (might be already gone or error occurred)${NC}"
    done <<< "$TRIGGERS"
    echo "   Waiting briefly for trigger deletions..."
    sleep 3 # Give deletions a moment
  else
    echo "   No relevant Eventarc triggers found."
  fi
  echo "----------------------------------"

  # 3. Delete the associated Cloud Run service (for Gen 2 functions)
  # This is often the resource that gets stuck.
  echo -e "${YELLOW}[Step 3/4] Deleting associated Cloud Run service...${NC}"
  # Gen 2 function name matches the underlying Cloud Run service name.
  if gcloud run services delete "$SHORT_FUNCTION_NAME" --project "$PROJECT" --region "$REGION" --platform managed --quiet; then
      echo -e "${GREEN}   -> Successfully initiated deletion of Cloud Run service: $SHORT_FUNCTION_NAME${NC}"
      echo "   Waiting for service deletion to progress..."
      sleep 10 # Wait longer for service deletion as it can take time
  else
      # Check if it failed because it doesn't exist (non-zero exit code from describe means not found)
      if gcloud run services describe "$SHORT_FUNCTION_NAME" --project "$PROJECT" --region "$REGION" --platform managed &> /dev/null; then
           echo -e "${RED}   -> Failed to delete Cloud Run service: $SHORT_FUNCTION_NAME. It might still exist or have deletion issues. Manual check required.${NC}"
      else
           echo -e "${YELLOW}   -> Cloud Run service $SHORT_FUNCTION_NAME already deleted or did not exist.${NC}"
      fi
  fi
  echo "----------------------------------"

  # 4. Delete the Cloud Function itself
  # This might fail if dependencies weren't fully removed, but attempt anyway.
  echo -e "${YELLOW}[Step 4/4] Deleting the Cloud Function resource...${NC}"
  if gcloud functions delete "$SHORT_FUNCTION_NAME" --project "$PROJECT" --region "$REGION" --quiet; then
    echo -e "${GREEN}   -> Successfully initiated deletion of function: $SHORT_FUNCTION_NAME${NC}"
  else
    # Check if it failed because it doesn't exist
     if gcloud functions describe "$SHORT_FUNCTION_NAME" --project "$PROJECT" --region "$REGION" &> /dev/null; then
        echo -e "${RED}   -> Failed to delete function: $SHORT_FUNCTION_NAME. Dependencies might still be present or another issue occurred. Manual check required.${NC}"
     else
        echo -e "${YELLOW}   -> Function $SHORT_FUNCTION_NAME already deleted or did not exist.${NC}"
     fi
  fi

done <<< "$FUNCTION_LIST"

echo "======================================================================"
echo -e "${GREEN}Force deletion script completed for all found functions.${NC}"
echo -e "${YELLOW}Note: Deletion operations can be asynchronous.${NC}"
echo -e "${YELLOW}Please verify resource cleanup in the Google Cloud Console (Cloud Functions, Cloud Run, Eventarc, Cloud Build).${NC}"
echo "======================================================================"