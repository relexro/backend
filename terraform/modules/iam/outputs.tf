# No outputs for this module 

output "api_gateway_sa_email" {
  description = "The email of the API Gateway service account"
  value       = "api-gateway-sa@${var.project_id}.iam.gserviceaccount.com"
} 