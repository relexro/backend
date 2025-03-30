# Create ZIP file of the functions source code
data "archive_file" "functions_source" {
  type        = "zip"
  source_dir  = var.functions_source_path
  output_path = var.functions_zip_path
}

# Upload the ZIP file to Cloud Storage
resource "google_storage_bucket_object" "functions_source" {
  name   = "functions-source-${data.archive_file.functions_source.output_md5}.zip"
  bucket = var.functions_bucket_name
  source = data.archive_file.functions_source.output_path
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
    
    ingress_settings               = "ALLOW_ALL"
    all_traffic_on_latest_revision = true
  }

  depends_on = [google_storage_bucket_object.functions_source]
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

# Output the function URIs
output "function_uris" {
  description = "Map of function names to their HTTPS URIs"
  value = {
    for name, function in google_cloudfunctions2_function.functions :
    name => function.service_config[0].uri
  }
  sensitive = false
}
