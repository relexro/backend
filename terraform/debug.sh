#!/bin/bash

# Set text colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default project and region values
PROJECT="relexro"
REGION="europe-west3"

# --- Timestamp for log queries ---
# Go back e.g., 1 hour to catch recent deployment attempts
LOG_START_TIME=$(date -u -d '1 hour ago' +'%Y-%m-%dT%H:%M:%SZ')

# Parse command line arguments
while getopts "p:r:" opt; do
  case $opt in
    p)
      PROJECT=$OPTARG
      ;;
    r)
      REGION=$OPTARG
      ;;
    \?)
      echo -e "${RED}Invalid option: -$OPTARG${NC}" >&2
      exit 1
      ;;
  esac
done

# --- Function to extract service name from function resource name ---
get_service_name() {
  local func_resource_name=$1
  # Example: projects/relexro/locations/europe-west3/functions/my-function
  local func_name=$(basename "$func_resource_name")
  # V2 functions often map to Cloud Run services with the same name
  echo "$func_name"
}

echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}Starting Cloud Functions Debug Script${NC}"
echo -e "${GREEN}Project: ${YELLOW}$PROJECT${NC}"
echo -e "${GREEN}Region: ${YELLOW}$REGION${NC}"
echo -e "${GREEN}Checking logs since: ${YELLOW}${LOG_START_TIME}${NC}"
echo -e "${GREEN}===================================================${NC}"

# Check for Cloud Functions v1 (1st gen)
echo -e "\n${GREEN}Checking for Cloud Functions (1st gen)...${NC}"
gcloud functions list --project=$PROJECT --regions=$REGION --format="table(name.basename(), status, entryPoint, runtime)" || echo -e "${RED}Error listing Cloud Functions v1${NC}"

# Check for Cloud Functions v2 (2nd gen) - CORRECTED FLAG
echo -e "\n${GREEN}Checking for Cloud Functions (2nd gen)...${NC}"
gcloud functions list --project=$PROJECT --regions=$REGION --v2 --format="table(name.basename(), state, environment, updateTime)" || echo -e "${RED}Error listing Cloud Functions v2${NC}"

# Find functions in DEPLOYING state (v2 only for this detailed debug) - CORRECTED FLAG
echo -e "\n${YELLOW}Searching for v2 functions stuck in DEPLOYING state...${NC}"
DEPLOYING_FUNCS=$(gcloud functions list --project=$PROJECT --regions=$REGION --v2 --filter="state=DEPLOYING" --format="value(name)")

if [ -z "$DEPLOYING_FUNCS" ]; then
  echo -e "${GREEN}No v2 functions found in DEPLOYING state.${NC}"
else
  echo -e "\n${YELLOW}Found functions stuck in DEPLOYING state:${NC}"
  # Print the list using the previously fetched variable
  echo "$DEPLOYING_FUNCS" | while IFS= read -r func_resource_name; do echo "- $(basename "$func_resource_name")"; done

  echo -e "\n${GREEN}--- Checking Logs for Stuck Functions ---${NC}"

  # Loop through each deploying function
  echo "$DEPLOYING_FUNCS" | while IFS= read -r func_resource_name
  do
    FUNC_NAME=$(basename "$func_resource_name")
    # Attempt to get the associated Cloud Run service name (often matches function name for v2) - CORRECTED FLAG
    SERVICE_NAME=$(gcloud functions describe "$func_resource_name" --project=$PROJECT --region=$REGION --v2 --format='value(serviceConfig.service)' 2>/dev/null | xargs basename || echo "$FUNC_NAME")

    echo -e "\n${YELLOW}Debugging Function: ${FUNC_NAME} (Service: ${SERVICE_NAME})${NC}"

    # --- Query 1: Cloud Function Logs for ERROR/CRITICAL ---
    # Look for errors directly reported by the function resource, potentially including build steps
    echo -e "${GREEN}1. Checking Cloud Function logs for recent errors (severity >= ERROR):${NC}"
    gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=$FUNC_NAME AND resource.labels.region=$REGION AND severity>=ERROR AND timestamp>=\"$LOG_START_TIME\"" \
      --project=$PROJECT --limit=20 --format="table(timestamp, severity, textPayload, protoPayload.status.message)" \
      || echo -e "${RED}Error fetching function logs for $FUNC_NAME${NC}"

    # --- Query 2: Cloud Build Logs for ERROR/CRITICAL ---
    # Look for build errors, potentially filtering by service name tag if available/reliable
    # Using a broader filter first, then mention how to refine if needed
    echo -e "\n${GREEN}2. Checking Cloud Build logs for recent errors (resource.type=build, severity >= ERROR):${NC}"
    # Note: Filtering precisely by function/service within build logs can be complex.
    # This searches broadly for build errors, review them for mentions of your function/service.
    gcloud logging read "resource.type=build AND severity>=ERROR AND timestamp>=\"$LOG_START_TIME\" AND (textPayload:\"$FUNC_NAME\" OR textPayload:\"$SERVICE_NAME\" OR jsonPayload.message:\"$FUNC_NAME\" OR jsonPayload.message:\"$SERVICE_NAME\" OR textPayload:\"pip install\" OR jsonPayload.message:\"pip install\")" \
      --project=$PROJECT --limit=30 --format="table(timestamp, logName.segment(5), severity, textPayload, jsonPayload.message)" \
      || echo -e "${RED}Error fetching Cloud Build logs (may need broader query)${NC}"
      echo -e "${YELLOW}Tip: Look for messages containing 'Step #1', 'pip install', 'dependency conflict', 'Build failed' above.${NC}"

  done

  # --- Query 3: Fetch Logs from the ABSOLUTE LATEST FAILED BUILD ---
  # This often contains the root cause if a build sequence completed with failure
  echo -e "\n${GREEN}--- Checking Latest Failed Cloud Build Log ---${NC}"
  LATEST_FAILED_BUILD_ID=$(gcloud builds list --project=$PROJECT --filter="status=FAILURE" --limit=1 --sort-by=~finishTime --format="value(id)")

  if [ -n "$LATEST_FAILED_BUILD_ID" ]; then
    echo -e "${YELLOW}Fetching logs for the most recent failed build: ${LATEST_FAILED_BUILD_ID}${NC}"
    gcloud builds log "$LATEST_FAILED_BUILD_ID" --project=$PROJECT || echo -e "${RED}Error fetching log for build $LATEST_FAILED_BUILD_ID${NC}"
    echo -e "${YELLOW}Tip: Search this log carefully for 'pip install', 'ERROR:', 'Traceback', dependency conflict details.${NC}"
  else
    echo -e "${GREEN}No recent failed builds found in the project.${NC}"
  fi

fi # End of check for deploying functions

# Check for Cloud Run services (where Cloud Functions v2 are deployed)
echo -e "\n${GREEN}--- Cloud Run Service Status ---${NC}"
gcloud run services list --project=$PROJECT --region=$REGION --format="table(name:label=SERVICE, status.latestReadyRevisionName:label=LATEST_READY_REVISION, status.conditions[0].type:label=STATUS, status.conditions[0].status:label=READY, status.conditions[0].message:label=MESSAGE)" || echo -e "${RED}Error listing Cloud Run services${NC}"

# Check for ongoing builds
echo -e "\n${GREEN}--- Ongoing Cloud Builds ---${NC}"
gcloud builds list --project=$PROJECT --ongoing --format="table(id, status, createTime, source.storageSource.object)" || echo -e "${RED}Error listing ongoing builds${NC}"

# Print recommendations
echo -e "\n${GREEN}===================================================${NC}"
echo -e "${GREEN}Debugging Recommendations:${NC}"
echo -e "1. ${YELLOW}Review the 'Latest Failed Cloud Build Log' above for specific error messages (esp. 'pip install' failures).${NC}"
echo -e "2. ${YELLOW}Check the 'Cloud Build logs' section for errors related to specific functions.${NC}"
echo -e "3. ${YELLOW}Fix dependency conflicts in 'requirements.txt' based on the errors found.${NC}"
echo -e "4. ${YELLOW}Common issues: conflicting package versions (e.g., firebase-admin vs google-cloud-firestore), incompatible Python versions, syntax errors.${NC}"
echo -e "5. ${YELLOW}After fixing code/dependencies, delete stuck functions before redeploying:${NC}" # CORRECTED FLAG
echo -e "   ${YELLOW}gcloud functions delete <function-name> --region=$REGION --v2 --project=$PROJECT${NC}"
echo -e "6. ${YELLOW}Check the 'Cloud Run Service Status' for messages related to the underlying service health.${NC}"
echo -e "${GREEN}===================================================${NC}"

echo -e "\n${GREEN}Debug script completed.${NC}"