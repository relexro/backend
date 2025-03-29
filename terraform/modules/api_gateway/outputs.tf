# This file intentionally left empty as the outputs are defined in main.tf 

output "gateway_hostname" {
  description = "The hostname of the API Gateway"
  value       = google_api_gateway_gateway.gateway.default_hostname
} 