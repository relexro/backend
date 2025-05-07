# This file contains the outputs from the cloud functions module

output "function_uris" {
  description = "Map of function names to their HTTPS URIs"
  value = {
    for name, function in google_cloudfunctions2_function.functions :
    name => function.service_config[0].uri
  }
  sensitive = false
}

output "function_names" {
  description = "Map of original function names to their environment-specific deployed names"
  value       = {
    for name, function in local.functions :
    name => function.name
  }
  sensitive   = false
}

output "source_hash" {
  description = "Hash of the source directory, used for detecting changes"
  value       = local.source_dir_hash
  sensitive   = false
}

output "config_hash" {
  description = "Hash of the functions configuration, used for detecting changes"
  value       = local.functions_config_hash
  sensitive   = false
}

output "combined_hash" {
  description = "Combined hash used for the deployment"
  value       = local.combined_hash
  sensitive   = false
} 