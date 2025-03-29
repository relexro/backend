#!/bin/bash

set -e  # Exit on error

# Set variables
PROJECT_ID=$(gcloud config get-value project)

# Check if there are any .tf files
if ! ls *.tf &>/dev/null; then
    echo "Error: No Terraform configuration files (.tf) found in the current directory!"
    echo "Please create your Terraform configuration files first."
    exit 1
fi

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    terraform init
fi

# Simple destroy without trying imports
echo "Destroying all resources..."
terraform destroy -auto-approve


# Ask if the state bucket should also be deleted
echo "delete the Terraform state bucket"

BUCKET_NAME="tf-state-relex"
echo "Deleting Terraform state bucket..."
gsutil rm -r "gs://${BUCKET_NAME}"
echo "State bucket deleted successfully!"