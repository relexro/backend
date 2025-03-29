#!/bin/bash

# === Terraform State Cleanup Script for Cloud Functions ===
#
# Purpose: Removes Cloud Function resources (V1 & V2) from the Terraform state.
# Usage: Run this script *after* the actual Cloud Functions have been deleted
#        (e.g., using gcloud or manually). It helps sync your state file
#        with the reality of the deleted resources.
#
# Warning: Directly manipulating Terraform state can be risky. Ensure you
#          understand the implications. This is intended for cleanup after
#          out-of-band deletions.

# Set text colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Script to remove Cloud Function resources from Terraform state.${NC}"
echo -e "${YELLOW}This assumes the actual Cloud Functions have already been deleted.${NC}"
echo "----------------------------------"

# --- Terraform Initialization ---
echo -e "${YELLOW}Ensuring Terraform is initialized...${NC}"
# Assumes backend.tf exists from a previous deploy.sh run and configures the backend
if [ ! -d ".terraform" ]; then
  echo "Directory .terraform not found. Running terraform init..."
  # Use -reconfigure to ensure backend settings are applied
  terraform init -reconfigure || { echo -e "${RED}Terraform init failed! Check configuration and backend access.${NC}"; exit 1; }
else
  echo "Terraform already initialized."
fi
# Add a brief pause to ensure initialization completes if it just ran
sleep 1
echo "----------------------------------"

# --- List Function Resources from Terraform State ---
echo -e "${YELLOW}Listing Cloud Function resources currently tracked in Terraform state...${NC}"
# Grep for both V1 and V2 function resource types
TF_FUNCTION_RESOURCES=$(terraform state list | grep '^google_cloudfunctions[2]?_function\.' || true)

if [ -z "$TF_FUNCTION_RESOURCES" ]; then
  echo -e "${YELLOW}No Cloud Function resources (google_cloudfunctions_function or google_cloudfunctions2_function) found in Terraform state. Exiting.${NC}"
  exit 0
fi

echo -e "${GREEN}Found Terraform function resources in state:${NC}"
echo "$TF_FUNCTION_RESOURCES"
echo "----------------------------------"

# --- Loop and Remove Each from State ---
echo -e "${YELLOW}Attempting to remove the listed function resources from Terraform state...${NC}"

TOTAL_RESOURCES=$(echo "$TF_FUNCTION_RESOURCES" | wc -l | xargs) # Get count
CURRENT_RESOURCE=0
SUCCESSFUL_REMOVALS=0
FAILED_REMOVALS=0

while IFS= read -r resource_address; do
  # Ensure resource_address is not empty
  if [ -z "$resource_address" ]; then
      continue
  fi

  ((CURRENT_RESOURCE++))
  echo "======================================================================"
  echo -e "${YELLOW}Processing resource ${CURRENT_RESOURCE} of ${TOTAL_RESOURCES}: $resource_address${NC}"
  echo "======================================================================"

  echo -e "${YELLOW}   -> Attempting command: terraform state rm \"$resource_address\"${NC}"

  # Execute terraform state rm
  if terraform state rm "$resource_address"; then
      echo -e "${GREEN}      Successfully removed \"$resource_address\" from Terraform state.${NC}"
      ((SUCCESSFUL_REMOVALS++))
  else
      # Log the error, but continue with the next resource
      echo -e "${RED}      Failed to remove \"$resource_address\" from Terraform state.${NC}"
      echo -e "${RED}      It might have already been removed, the name could be slightly different, or another error occurred.${NC}"
      ((FAILED_REMOVALS++))
  fi
  # Add a small delay between commands if needed, especially with remote state backends
  # sleep 1

done <<< "$TF_FUNCTION_RESOURCES"

# --- Summary ---
echo "======================================================================"
echo -e "${GREEN}Terraform state cleanup script completed.${NC}"
echo -e "Summary: ${GREEN}${SUCCESSFUL_REMOVALS} removed${NC}, ${RED}${FAILED_REMOVALS} failed${NC}."
if [ $FAILED_REMOVALS -gt 0 ]; then
     echo -e "${RED}Please check the logs above for any failed state removals. You may need to remove them manually or investigate further.${NC}"
fi
echo -e "${YELLOW}Run 'terraform plan' to verify the state changes and ensure no unexpected differences remain.${NC}"
echo "======================================================================"