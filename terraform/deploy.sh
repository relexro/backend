#!/bin/bash

# Don't exit immediately on error, we want to handle some errors gracefully
set +e

# Ensure we're in the terraform directory
cd "$(dirname "$0")"

# Set variables
BUCKET_NAME="tf-state-relex"
BUCKET_LOCATION="europe-west1"
STATE_PREFIX="backend"
PROJECT_ID=$(gcloud config get-value project)

# Configuration options
FORCE_UNLOCK=true                           # Always use -y for all operations
VERIFY_API_CONSISTENCY=${VERIFY_API_CONSISTENCY:-false}  # Set to true to check API consistency

# Function to check and release state lock if needed
check_and_release_lock() {
  # Check if there's a state lock
  LOCK_INFO=$(terraform force-unlock -force=false 2>&1 | grep "ID:")
  if [[ $? -eq 0 && -n "$LOCK_INFO" ]]; then
    LOCK_ID=$(echo "$LOCK_INFO" | awk '{print $2}')
    echo "Found Terraform state lock with ID: $LOCK_ID"
    echo "Automatically unlocking state..."
    terraform force-unlock -force=true "$LOCK_ID"
  fi
}

# Create GCS bucket if it doesn't exist
if ! gsutil ls -b "gs://${BUCKET_NAME}" &>/dev/null; then
    echo "Creating GCS bucket for Terraform state..."
    gsutil mb -l ${BUCKET_LOCATION} "gs://${BUCKET_NAME}"

    # Enable versioning for state files
    gsutil versioning set on "gs://${BUCKET_NAME}"

    echo "Bucket created successfully!"
else
    echo "Bucket already exists, proceeding with Terraform initialization..."
fi

# Create backend configuration
cat > backend.tf <<EOF
terraform {
  backend "gcs" {
    bucket = "${BUCKET_NAME}"
    prefix = "${STATE_PREFIX}"
  }
}
EOF

# Check if there are any .tf files
if ! ls *.tf &>/dev/null; then
    echo "Error: No Terraform configuration files (.tf) found in the current directory!"
    echo "Please create your Terraform configuration files first."
    exit 1
fi

# Check for state lock before initializing
check_and_release_lock

# Initialize Terraform with reconfigure flag to handle backend changes
echo "Initializing Terraform..."
terraform init -reconfigure -input=false
if [ $? -ne 0 ]; then
    echo "Terraform initialization failed. Checking for state lock..."
    check_and_release_lock
    echo "Retrying initialization..."
    terraform init -reconfigure -input=false
    if [ $? -ne 0 ]; then
        echo "Terraform initialization failed again. Exiting."
        exit 1
    fi
fi

# Plan the changes
echo "Planning Terraform changes..."
terraform plan -out=tfplan -input=false
if [ $? -ne 0 ]; then
    echo "Terraform plan failed. Checking for state lock..."
    check_and_release_lock
    echo "Retrying plan..."
    terraform plan -out=tfplan -input=false
    if [ $? -ne 0 ]; then
        echo "Terraform plan failed again. Exiting."
        exit 1
    fi
fi

# Apply the changes
echo "Applying Terraform changes..."
echo "Note: This may take a long time, especially with many Cloud Functions."

# Apply the changes
terraform apply -auto-approve tfplan

# Check the exit code
APPLY_EXIT_CODE=$?
echo "Terraform apply exit code: $APPLY_EXIT_CODE"

# Format the output for better readability and save to file
if [ -f "terraform.tfstate" ]; then
  echo "Formatting function URLs for better readability..."
  echo "============== FUNCTION URLS ================"
  terraform output -json function_urls | jq -r 'to_entries | sort_by(.key) | .[] | "\(.key):\n  \(.value)"' | sed 's/-dev-apmzkjwhqq-ew.a.run.app/-dev.../g'
  echo "============================================="

  echo "Other outputs:"
  echo "- API Domain: $(terraform output -raw api_domain 2>/dev/null || echo 'N/A')"
  echo "- API Gateway URL: $(terraform output -raw api_gateway_url 2>/dev/null || echo 'N/A')"
  echo "- Environment: $(terraform output -raw environment 2>/dev/null || echo 'N/A')"
  echo "- Files Bucket: $(terraform output -raw files_bucket_name 2>/dev/null || echo 'N/A')"
  echo "- Functions Bucket: $(terraform output -raw functions_bucket_name 2>/dev/null || echo 'N/A')"
  echo "- Service Account: $(terraform output -raw service_account_email 2>/dev/null || echo 'N/A')"
fi

# Optional: Test API consistency if needed
if [ "$VERIFY_API_CONSISTENCY" = "true" ]; then
  echo ""
  echo "================ API CONSISTENCY CHECK ================"
  FUNCTION_NAME="relex-backend-agent-handler-dev"
  REGION="europe-west1"
  PROJECT_ID=$(gcloud config get-value project)

  echo "Checking function: $FUNCTION_NAME"

  # Get states but don't show verbose output
  gcloud functions describe $FUNCTION_NAME --gen2 --region=$REGION --format=json > function-state-gcloud.json 2>/dev/null
  terraform state show "module.cloud_functions.google_cloudfunctions2_function.functions[\"relex-backend-agent-handler\"]" > function-state-terraform.txt 2>/dev/null

  # Check if there are differences in key fields
  echo "Checking key fields:"
  echo "- Name: $(jq -r '.name' function-state-gcloud.json | xargs basename)"
  echo "- State: $(jq -r '.state' function-state-gcloud.json)"
  echo "- Runtime: $(jq -r '.buildConfig.runtime' function-state-gcloud.json)"
  echo "- Entry Point: $(jq -r '.buildConfig.entryPoint' function-state-gcloud.json)"
  echo "- Memory: $(jq -r '.serviceConfig.availableMemory' function-state-gcloud.json)"
  echo "- Timeout: $(jq -r '.serviceConfig.timeoutSeconds' function-state-gcloud.json) seconds"
  echo "- URL: $(jq -r '.url' function-state-gcloud.json)"
  echo "======================================================="
fi

# Handle interruption
if [ $APPLY_EXIT_CODE -ne 0 ]; then
    echo "Terraform apply reported an error code: $APPLY_EXIT_CODE"
    echo "This may be the normal 'execution halted' message which can be ignored if functions were deployed successfully."
    echo "Checking state..."
    terraform state list > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "State may be locked. Attempting to unlock..."
        check_and_release_lock
    fi
    echo "Run 'terraform plan' to check if any changes are still pending."
else
    echo "Terraform apply completed successfully!"

    # Save the output to docs/terraform_outputs.log
    DOCS_DIR="../docs"
    OUTPUT_FILE="${DOCS_DIR}/terraform_outputs.log"

    # Create docs directory if it doesn't exist
    mkdir -p "$DOCS_DIR"

    echo "Saving Terraform outputs to ${OUTPUT_FILE}..."

    # Write a header to the file
    echo "# Terraform Deployment Output - ${ENVIRONMENT}" > "$OUTPUT_FILE"
    echo "# Generated on: $(date)" >> "$OUTPUT_FILE"
    echo "# Project: ${PROJECT_ID}" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    # Save the raw terraform output
    echo "## Raw Terraform Output" >> "$OUTPUT_FILE"
    terraform output >> "$OUTPUT_FILE"

    echo "Deployment outputs have been saved to docs/terraform_outputs.log"
fi

# Clean up the plan file
rm -f tfplan

echo "Deployment process completed."