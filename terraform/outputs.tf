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

# Stripe outputs
output "stripe_product_ids" {
  description = "IDs of created Stripe products."
  value       = module.stripe.product_ids
}

output "stripe_price_lookup_keys" {
  description = "User-defined lookup keys for created Stripe prices."
  value       = module.stripe.price_lookup_keys
}

output "stripe_price_actual_ids" {
  description = "Actual Stripe-generated Price IDs."
  value       = module.stripe.price_actual_ids
}

output "stripe_test_coupon_id" {
  description = "ID of the test coupon."
  value       = module.stripe.test_coupon_id
}

output "stripe_test_promotion_code_string" {
  description = "The test promotion code string."
  value       = module.stripe.test_promotion_code_string
}

output "stripe_test_promotion_code_id" {
  description = "ID of the test promotion code resource."
  value       = module.stripe.test_promotion_code_id
}

output "stripe_german_vat_tax_rate_id" {
  description = "ID of the German VAT 19% tax rate."
  value       = module.stripe.german_vat_tax_rate_id
}

output "stripe_webhook_endpoint_id" {
  description = "ID of the created Stripe webhook endpoint."
  value       = module.stripe.webhook_endpoint_id
}

output "stripe_webhook_endpoint_secret" {
  description = "Secret for the Stripe webhook endpoint. THIS IS SENSITIVE and needed for webhook validation."
  value       = module.stripe.webhook_endpoint_secret
  sensitive   = true
}

output "stripe_api_key_prefix" {
  description = "First 8 characters of the Stripe API key being used (for verification purposes)"
  value       = substr(var.stripe_secret_key, 0, 8)
}
