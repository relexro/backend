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

output "function_urls" {
  description = "Map of Cloud Function URLs by function name"
  value       = module.cloud_functions.function_uris
}

# These outputs reference existing resources
output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = module.api_gateway.gateway_hostname
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

output "service_account_email" {
  description = "Email of the service account used by Cloud Functions"
  value       = trimprefix(local.functions_service_account_email, "serviceAccount:")
}

output "storage_buckets" {
  description = "Map of storage bucket names"
  value = {
    files     = module.storage.files_bucket_name
    functions = module.storage.functions_bucket_name
  }
}

output "environment" {
  description = "Current environment"
  value       = var.environment
}
