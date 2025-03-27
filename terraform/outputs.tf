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
  description = "The URL of the deployed API Gateway"
  value       = "relex-api-gateway-xxxxxxxxx.ew.gateway.dev"  # Replace this with your actual gateway URL
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
