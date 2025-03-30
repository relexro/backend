output "files_bucket_name" {
  description = "The name of the storage bucket for files"
  value       = module.storage.files_bucket_name
}

output "files_bucket_url" {
  description = "The URL of the storage bucket for files"
  value       = module.storage.files_bucket_url
}

output "functions_bucket_name" {
  description = "The name of the storage bucket for Cloud Functions source code"
  value       = module.storage.functions_bucket_name
}

output "functions_bucket_url" {
  description = "The URL of the storage bucket for Cloud Functions source code"
  value       = module.storage.functions_bucket_url
}

output "function_uris" {
  description = "Map of function names to their URIs for API Gateway configuration"
  value       = module.cloud_functions.function_uris
}

# These outputs reference existing resources
output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = google_api_gateway_gateway.gateway.default_hostname
}

output "api_domain" {
  description = "Custom domain for the API"
  value       = local.api_domain
}

output "firebase_web_app_name" {
  description = "The name of the Firebase Web App"
  value       = "Relex Web App"
}

output "firebase_web_app_id" {
  description = "The ID of the Firebase Web App"
  value       = "relexro"
  sensitive   = true
}

output "function_urls" {
  description = "Map of Cloud Function URLs by function name"
  value = {
    for k, v in google_cloudfunctions2_function.functions : k => v.url
  }
}

output "service_account_email" {
  description = "Email of the service account used by Cloud Functions"
  value       = google_service_account.functions.email
}

output "storage_buckets" {
  description = "Map of storage bucket names"
  value = {
    files     = google_storage_bucket.files.name
    functions = google_storage_bucket.functions_source.name
  }
}

output "environment" {
  description = "Current environment"
  value       = var.environment
}
