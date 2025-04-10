# Calculate a more stable hash of the source directory
locals {
  # Create a hash of all files in the source directory
  source_dir_files = fileset(var.functions_source_path, "**")
  source_dir_hash = sha256(join("", [
    for file in local.source_dir_files :
    filesha256("${var.functions_source_path}/${file}")
    if !endswith(file, ".pyc") && !endswith(file, "__pycache__/") && !startswith(file, ".")
  ]))

  # Create a stable hash for the functions configuration
  functions_config_hash = sha256(jsonencode(var.functions))

  # Combine the source hash and config hash for a complete hash
  combined_hash = sha256("${local.source_dir_hash}${local.functions_config_hash}")
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
    ".idea"
  ]
}

# Upload the ZIP file to Cloud Storage
resource "google_storage_bucket_object" "functions_source" {
  name   = "functions-source-${local.combined_hash}.zip"
  bucket = var.functions_bucket_name
  source = data.archive_file.functions_source.output_path

  # Only update the object if the source code or function configuration has changed
  content_type = "application/zip"
  metadata = {
    source_hash = local.source_dir_hash
    config_hash = local.functions_config_hash
  }
}

# Deploy each HTTP Cloud Function
resource "google_cloudfunctions2_function" "functions" {
  for_each = local.functions_with_env

  name        = local.function_names[each.key]
  project     = var.project_id
  location    = var.region
  description = each.value.description

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
    service_account_email = var.functions_service_account_email
    max_instance_count    = lookup(each.value, "max_instances", 10)
    available_memory      = lookup(each.value, "memory", "256Mi")
    timeout_seconds       = lookup(each.value, "timeout", 60)

    environment_variables = each.value.env_vars

    dynamic "secret_environment_variables" {
      for_each = coalesce(each.value.secret_env_vars, [])
      content {
        key        = secret_environment_variables.value.key
        project_id = var.project_id
        secret     = secret_environment_variables.value.secret
        version    = secret_environment_variables.value.version
      }
    }

    ingress_settings               = "ALLOW_INTERNAL_AND_GCLB"
    all_traffic_on_latest_revision = true
  }

  depends_on = [google_storage_bucket_object.functions_source]

  lifecycle {
    # Ignore changes to metadata that might change but don't affect functionality
    ignore_changes = [
      labels,
      build_config[0].worker_pool,
      build_config[0].docker_repository,
      service_config[0].service_account_email,
      service_config[0].environment_variables["LOG_EXECUTION_ID"]
    ]

    # Prevent replacement when only the source code changes
    # This ensures that the function is updated in place rather than recreated
    replace_triggered_by = []
  }
}

# Add IAM policy to allow API Gateway to invoke the Cloud Functions
resource "google_cloud_run_service_iam_member" "invoker" {
  for_each = local.functions_with_env

  service  = google_cloudfunctions2_function.functions[each.key].service_config[0].service
  project  = var.project_id
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.api_gateway_sa_email}"

  depends_on = [google_cloudfunctions2_function.functions]
}
