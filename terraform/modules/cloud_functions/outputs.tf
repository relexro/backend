# This file intentionally left empty as the outputs are defined in main.tf 

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