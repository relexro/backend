variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
  default     = "relexro"
}

variable "region" {
  description = "The region for resources deployment"
  type        = string
  default     = "europe-west3"
}

variable "apig_region" {
  description = "The region for API Gateway deployment"
  type        = string
  default     = "europe-west1"
}

variable "function_names" {
  description = "Names of the Firebase Functions to deploy"
  type        = list(string)
  default     = ["cases", "chat", "auth", "payments", "business"]
}

variable "bucket_names" {
  description = "Names of the Cloud Storage buckets to create"
  type        = map(string)
  default     = {
    "files"     = "files"
    "functions" = "functions"
  }
}

variable "facebook_client_id" {
  description = "Facebook OAuth Client ID"
  type        = string
  default     = ""
}

variable "facebook_client_secret" {
  description = "Facebook OAuth Client Secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "domain_name" {
  description = "The domain name managed by Cloudflare"
  type        = string
  default     = "relex.ro"
}

variable "api_subdomain" {
  description = "The subdomain for the API Gateway"
  type        = string
  default     = "api"
}

variable "cloudflare_api_token" {
  description = "Cloudflare API Token"
  type        = string
  sensitive   = true
  # Will use the CF_RELEX_TOKEN env var
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for the domain"
  type        = string
  # Will use TF_VAR_cloudflare_zone_id environment variable
}

variable "cloudflare_account_id" {
  description = "Cloudflare Account ID"
  type        = string
  # Will use TF_VAR_cloudflare_account_id environment variable
}

variable "stripe_secret_key" {
  description = "Stripe Secret API key"
  type        = string
  sensitive   = true
  # Will use TF_VAR_stripe_secret_key environment variable
}

variable "stripe_webhook_secret" {
  description = "Stripe Webhook Secret for validating webhook events"
  type        = string
  sensitive   = true
  # Will use TF_VAR_stripe_webhook_secret environment variable
}

variable "project_number" {
  description = "The Google Cloud project number"
  type        = string
  default     = "49787884280"
} 