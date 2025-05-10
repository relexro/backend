locals {
  # Common environment variables for all functions
  common_env_vars = {
    ENVIRONMENT          = var.environment
    GOOGLE_CLOUD_PROJECT = var.project_id
    GOOGLE_CLOUD_REGION  = var.region
    GCS_BUCKET           = var.functions_bucket_name
    LOG_EXECUTION_ID     = "true"
  }

  # Define environment variables that should be excluded from the hash calculation
  # These are variables that might change but don't affect the function's behavior
  excluded_env_vars = [
    "LOG_EXECUTION_ID",
    "LOG_LEVEL",
    "DEBUG",
    "TRACE_ENABLED"
  ]

  # Process functions to include environment suffix, merged env vars, and explicit memory setting
  functions = {
    for k, v in var.functions : k => merge(v, {
      name     = "${k}${var.environment == "prod" ? "" : "-${var.environment}"}"
      env_vars = merge(local.common_env_vars, v.env_vars)
      memory   = lookup(v, "memory", "512Mi")
    })
  }

  # Create a stable representation of environment variables for hashing
  # by excluding variables that change frequently but don't affect functionality
  stable_env_vars = {
    for k, v in local.functions : k => {
      for env_key, env_value in v.env_vars :
      env_key => env_value
      if !contains(local.excluded_env_vars, env_key)
    }
  }
}