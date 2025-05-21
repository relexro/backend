variable "environment" {
  description = "The target environment (dev, stage, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "stage", "prod"], var.environment)
    error_message = "Environment must be one of: dev, stage, prod"
  }
}

variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
  default     = "relexro"
}

variable "region" {
  description = "The region for resources deployment"
  type        = string
  default     = "europe-west1"
}

variable "service_account_name" {
  description = "Name of the service account for Cloud Functions"
  type        = string
  default     = "relex-functions"
}

variable "bucket_names" {
  description = "Names of the Cloud Storage buckets to create"
  type        = map(string)
  default = {
    "files"     = "files"
    "functions" = "functions"
  }
}

variable "domain_name" {
  description = "The domain name managed by Cloudflare"
  type        = string
  default     = "relex.ro"
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token for DNS validation"
  type        = string
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for the domain"
  type        = string
}

variable "cloudflare_account_id" {
  description = "Cloudflare Account ID"
  type        = string
}

variable "project_number" {
  description = "The Google Cloud project number"
  type        = string
  default     = "49787884280"
}

variable "stripe_secret_key" {
  description = "Stripe API Secret Key (Test Mode). This will be populated by the TF_VAR_stripe_secret_key environment variable."
  type        = string
  sensitive   = true
}
