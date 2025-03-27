# This file intentionally left empty as the outputs are defined in main.tf 

output "gateway_hostname" {
  description = "The hostname of the API Gateway"
  value       = google_api_gateway_gateway.gateway.default_hostname
}

output "api_gateway_sa_email" {
  description = "The service account email for the API Gateway"
  value       = google_service_account.api_gateway.email
} 