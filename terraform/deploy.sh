#!/bin/bash

set -e  # Exit on error

# Ensure we're in the terraform directory
cd "$(dirname "$0")"

# Set variables
BUCKET_NAME="tf-state-relex"
BUCKET_LOCATION="europe-west3"
STATE_PREFIX="backend"
PROJECT_ID=$(gcloud config get-value project)

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

# Initialize Terraform with reconfigure flag to handle backend changes
terraform init -reconfigure

# Plan the changes
terraform plan -out=tfplan

# Apply the changes
terraform apply -auto-approve tfplan

# Clean up the plan file
rm -f tfplan 