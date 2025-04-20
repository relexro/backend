locals {
  # Merge default functions with additional functions
  merged_functions = merge(var.functions)

  # Create function names with environment suffix (only in non-prod)
  function_names = {
    for k, v in local.merged_functions : k => "${k}${var.environment == "prod" ? "" : "-${var.environment}"}"
  }

  # Common environment variables for all functions
  common_env_vars = {
    ENVIRONMENT         = var.environment
    GOOGLE_CLOUD_PROJECT = var.project_id
    GOOGLE_CLOUD_REGION  = var.region
    GCS_BUCKET          = var.functions_bucket_name
  }

  # Merge common and function-specific env vars
  functions_with_env = {
    for k, v in local.merged_functions : k => merge(v, {
      env_vars = merge(local.common_env_vars, v.env_vars)
    })
  }
} 