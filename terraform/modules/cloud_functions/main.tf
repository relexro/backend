# Calculate a more stable hash of the source directory
locals {
  # Create a hash of all files in the source directory, excluding irrelevant files
  source_dir_files = fileset(var.functions_source_path, "**")

  # Filter out files that shouldn't affect the hash
  filtered_files = [
    for file in local.source_dir_files :
    file
    if !endswith(file, ".pyc") &&
       !contains(split("/", file), "__pycache__") &&
       !startswith(file, ".") &&
       !endswith(file, ".log") &&
       !endswith(file, ".tmp")
  ]

  # Sort the files to ensure consistent ordering
  sorted_files = sort(local.filtered_files)

  # Create a stable hash that doesn't change unless content actually changes
  source_dir_hash = sha256(join("", [
    for file in local.sorted_files :
    filesha256("${var.functions_source_path}/${file}")
  ]))

  # Create a stable hash for the functions configuration
  # Use stable_env_vars instead of full functions to exclude volatile env vars
  functions_config_hash = sha256(jsonencode({
    for fn_name in sort(keys(local.functions)) : fn_name => {
      entry_point   = local.functions[fn_name].entry_point
      memory        = lookup(local.functions[fn_name], "memory", "512Mi")
      timeout       = lookup(local.functions[fn_name], "timeout", 60)
      max_instances = lookup(local.functions[fn_name], "max_instances", 3)

      # Stable env vars map (keys sorted)
      stable_env_vars = {
        for env_key in sort(keys(lookup(local.stable_env_vars, fn_name, {}))) :
        env_key => lookup(local.stable_env_vars, fn_name, {})[env_key]
      }

      # Only the key + secret name matter, order them deterministically as well
      secret_env_vars_keys = sort([
        for secret in coalesce(lookup(local.functions[fn_name], "secret_env_vars", []), []) :
        "${secret.key}:${secret.secret}"
      ])
    }
  }))

  # Combine the source hash and config hash for a complete hash
  combined_hash = sha256("${local.source_dir_hash}${local.functions_config_hash}")

  # Create a shorter hash for the object name - using combined hash for better stability
  short_hash = substr(local.combined_hash, 0, 8)

  # Embed the hash in the uploaded object name.  The name only changes when
  # the *content* actually changes, which gives Terraform a deterministic
  # signal to roll a new revision while remaining completely stable across
  # identical plans.
  functions_object_name = "functions-source-${local.short_hash}.zip"
}

# Create ZIP file of the functions source code
data "archive_file" "functions_source" {
  type        = "zip"
  source_dir  = var.functions_source_path
  output_path = var.functions_zip_path

  # Exclude common Python cache files and hidden files
  excludes = [
    "__pycache__",
    "*.pyc",
    ".git",
    ".gitignore",
    ".vscode",
    ".idea",
    "*.log",
    "*.tmp"
  ]
}

# Upload the ZIP file to Cloud Storage
resource "google_storage_bucket_object" "functions_source" {
  name         = local.functions_object_name
  bucket       = var.functions_bucket_name
  source       = data.archive_file.functions_source.output_path
  content_type = "application/zip"

  # Store hashes in metadata to track changes
  metadata = {
    source_hash  = local.source_dir_hash
    config_hash  = local.functions_config_hash
    combined_hash = local.combined_hash
  }

  # Ignore attributes that can change even when content doesn't change
  lifecycle {
    ignore_changes = [
      detect_md5hash
    ]
  }
}

# We're not using a null_resource anymore since we're using the storage bucket object directly

# Deploy each HTTP Cloud Function
resource "google_cloudfunctions2_function" "functions" {
  for_each = local.functions

  name        = each.value.name
  location    = var.region
  description = each.value.description
  project     = var.project

  build_config {
    runtime     = "python310"
    entry_point = each.value.entry_point
    source {
      storage_source {
        bucket = var.functions_bucket_name
        object = google_storage_bucket_object.functions_source.name
      }
    }
  }

  service_config {
    max_instance_count    = lookup(each.value, "max_instances", 3)
    available_memory      = "512Mi" # Consider making this configurable per function if needed
    timeout_seconds       = lookup(each.value, "timeout", 60)
    environment_variables = merge(
      each.value.env_vars,
      # Add Stripe Price ID env vars specifically for functions that need them,
      # or universally if all/most functions might need them.
      # For now, adding them to all functions for simplicity, but this can be refined.
      # The keys here (e.g., STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY) are what the Python code will use.
      (
        # Check if the current function is one of the payment-related functions
        # This is a more targeted approach.
        # Alternatively, to apply to ALL functions, remove this conditional logic and just include the map.
        contains(["relex-backend-create-payment-intent", "relex-backend-get-products", "relex-backend-create-checkout-session", "relex-backend-handle-stripe-webhook", "relex-backend-cancel-subscription"], each.key) ?
        {
         STRIPE_PRICE_ID_INDIVIDUAL_MONTHLY = var.stripe_price_id_individual_monthly
         STRIPE_PRICE_ID_ORG_BASIC_MONTHLY  = var.stripe_price_id_org_basic_monthly
         STRIPE_PRICE_ID_CASE_TIER_1        = var.stripe_price_id_case_tier1
         STRIPE_PRICE_ID_CASE_TIER_2        = var.stripe_price_id_case_tier2
         STRIPE_PRICE_ID_CASE_TIER_3        = var.stripe_price_id_case_tier3
         STRIPE_PRODUCT_ID_RELEX_CASE       = var.stripe_product_id_relex_case
         STRIPE_PRODUCT_ID_INDIVIDUAL_PLAN  = var.stripe_product_id_individual_plan
         STRIPE_PRODUCT_ID_ORG_BASIC_PLAN   = var.stripe_product_id_relex_org_basic_plan
         STRIPE_PRODUCT_ID_ORG_PRO_PLAN     = var.stripe_product_id_relex_org_pro_plan
        } : {}
      )
    )

    dynamic "secret_environment_variables" {
      for_each = coalesce(lookup(each.value, "secret_env_vars", []), [])
      content {
        key        = secret_environment_variables.value.key
        project_id = var.project_id
        secret     = secret_environment_variables.value.secret
        version    = secret_environment_variables.value.version
      }
    }

    # Allow public ingress in non-production environments to enable direct testing (e.g., dev).
    ingress_settings = var.environment == "prod" ? "ALLOW_INTERNAL_AND_GCLB" : "ALLOW_ALL"
    service_account_email  = var.service_account_email
  }

  # Add explicit timeouts to give the API more time to propagate changes
  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
  }

  # We need to be careful about what we ignore here
  # We want to ignore things that change but don't affect functionality
  # But we need to track changes to the source code
  lifecycle {
    ignore_changes = [
      labels
    ]
  }

  # Add explicit dependencies to ensure proper ordering
  depends_on = [
    google_storage_bucket_object.functions_source
  ]
}

# Add IAM policy to allow API Gateway to invoke the Cloud Functions
resource "google_cloud_run_service_iam_member" "invoker" {
  for_each = local.functions

  service  = google_cloudfunctions2_function.functions[each.key].name
  project  = var.project_id
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.api_gateway_sa_email}"

  depends_on = [google_cloudfunctions2_function.functions]
}
