# Calculate a more stable hash of the source directory
locals {
  # Create a hash of all files in the source directory
  source_dir_files = fileset(var.functions_source_path, "**")
  
  # Sort the files to ensure consistent ordering
  sorted_files = sort(local.source_dir_files)
  
  # Create a stable hash that doesn't change unless content actually changes
  source_dir_hash = sha256(join("", [
    for file in local.sorted_files :
    filesha256("${var.functions_source_path}/${file}")
    if !endswith(file, ".pyc") && !endswith(file, "__pycache__/") && !startswith(file, ".")
  ]))

  # Create a stable hash for the functions configuration
  functions_config_hash = sha256(jsonencode(local.functions))

  # Combine the source hash and config hash for a complete hash
  combined_hash = sha256("${local.source_dir_hash}${local.functions_config_hash}")
  
  # Create a shorter hash for the object name
  short_hash = substr(local.source_dir_hash, 0, 8)
}

# Create ZIP file of the functions source code
data "archive_file" "functions_source" {
  type        = "zip"
  source_dir  = var.functions_source_path
  output_path = "${var.functions_zip_path}-${local.short_hash}"

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
  name   = "functions-source-${local.short_hash}.zip"
  bucket = var.functions_bucket_name
  source = data.archive_file.functions_source.output_path

  # Only update the object if the source code or function configuration has changed
  content_type = "application/zip"
  metadata = {
    source_hash = local.source_dir_hash
    config_hash = local.functions_config_hash
  }
  
  # Try to prevent unnecessary replacements
  lifecycle {
    ignore_changes = [
      detect_md5hash,
      metadata
    ]
  }
}

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
    available_memory      = lookup(each.value, "memory", "256M")
    timeout_seconds      = lookup(each.value, "timeout", 60)
    environment_variables = each.value.env_vars

    dynamic "secret_environment_variables" {
      for_each = coalesce(lookup(each.value, "secret_env_vars", []), [])
      content {
        key        = secret_environment_variables.value.key
        project_id = var.project_id
        secret     = secret_environment_variables.value.secret
        version    = secret_environment_variables.value.version
      }
    }

    ingress_settings       = "ALLOW_INTERNAL_AND_GCLB"
    service_account_email = var.service_account_email
  }
  
  # This will prevent unnecessary updates by ignoring certain attributes that might change
  # but don't affect the actual function deployment
  lifecycle {
    ignore_changes = [
      build_config[0].source[0].storage_source[0].generation,
      build_config[0].source[0].storage_source[0].object,
      labels
    ]
  }
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
