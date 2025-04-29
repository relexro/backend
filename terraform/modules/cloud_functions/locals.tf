locals {
  # Common environment variables for all functions
  common_env_vars = {
    ENVIRONMENT          = var.environment
    GOOGLE_CLOUD_PROJECT = var.project_id
    GOOGLE_CLOUD_REGION  = var.region
    GCS_BUCKET          = var.functions_bucket_name
  }

  # Process functions to include environment suffix and merged env vars
  functions = {
    for k, v in var.functions : k => merge(v, {
      name     = "${k}${var.environment == "prod" ? "" : "-${var.environment}"}"
      env_vars = merge(local.common_env_vars, v.env_vars)
    })
  }
} 