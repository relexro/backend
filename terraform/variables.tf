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
  default     = "europe-west3"
}

variable "apig_region" {
  description = "The region for API Gateway deployment"
  type        = string
  default     = "europe-west1"
}

variable "functions" {
  description = "Map of Cloud Functions configurations"
  type = map(object({
    name                = string
    entry_point         = string
    memory             = optional(string, "256M")
    timeout_seconds     = optional(number, 60)
    min_instance_count  = optional(number, 0)
    max_instance_count  = optional(number, 100)
    available_memory    = optional(string, "256M")
    available_cpu       = optional(string, "0.1666")
    env_vars           = optional(map(string), {})
    secret_env_vars    = optional(map(string), {})
  }))
  default = {
    "create-organization" = {
      name        = "relex-backend-create-organization"
      entry_point = "relex_backend_create_organization"
    }
    "delete-organization" = {
      name        = "relex-backend-delete-organization"
      entry_point = "relex_backend_delete_organization"
    }
    "create-case" = {
      name        = "relex-backend-create-case"
      entry_point = "relex_backend_create_case"
    }
    "get-case" = {
      name        = "relex-backend-get-case"
      entry_point = "relex_backend_get_case"
    }
    "list-cases" = {
      name        = "relex-backend-list-cases"
      entry_point = "relex_backend_list_cases"
    }
    "update-case" = {
      name        = "relex-backend-update-case"
      entry_point = "relex_backend_update_case"
    }
    "archive-case" = {
      name        = "relex-backend-archive-case"
      entry_point = "relex_backend_archive_case"
    }
    "delete-case" = {
      name        = "relex-backend-delete-case"
      entry_point = "relex_backend_delete_case"
    }
    "create-payment-intent" = {
      name        = "relex-backend-create-payment-intent"
      entry_point = "relex_backend_create_payment_intent"
      secret_env_vars = {
        STRIPE_SECRET_KEY = "stripe_secret_key"
      }
    }
    "create-checkout-session" = {
      name        = "relex-backend-create-checkout-session"
      entry_point = "relex_backend_create_checkout_session"
      secret_env_vars = {
        STRIPE_SECRET_KEY = "stripe_secret_key"
      }
    }
    "handle-stripe-webhook" = {
      name        = "relex-backend-handle-stripe-webhook"
      entry_point = "relex_backend_handle_stripe_webhook"
      secret_env_vars = {
        STRIPE_SECRET_KEY     = "stripe_secret_key"
        STRIPE_WEBHOOK_SECRET = "stripe_webhook_secret"
      }
    }
    "cancel-subscription" = {
      name        = "relex-backend-cancel-subscription"
      entry_point = "relex_backend_cancel_subscription"
      secret_env_vars = {
        STRIPE_SECRET_KEY = "stripe_secret_key"
      }
    }
  }
}

variable "service_account_name" {
  description = "Name of the service account for Cloud Functions"
  type        = string
  default     = "relex-functions"
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
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for the domain"
  type        = string
}

variable "cloudflare_account_id" {
  description = "Cloudflare Account ID"
  type        = string
}

variable "stripe_secret_key_name" {
  description = "Name of the Secret Manager secret containing the Stripe secret key"
  type        = string
  default     = "stripe-secret-key"
}

variable "stripe_webhook_secret_name" {
  description = "Name of the Secret Manager secret containing the Stripe webhook secret"
  type        = string
  default     = "stripe-webhook-secret"
}

variable "project_number" {
  description = "The Google Cloud project number"
  type        = string
  default     = "49787884280"
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

locals {
  env_suffix = var.environment == "prod" ? "" : "-${var.environment}"
  
  # Environment-specific resource names
  function_names = {
    for k, v in var.functions : k => "${v.name}${local.env_suffix}"
  }
  
  bucket_names = {
    for k, v in var.bucket_names : k => "${v}${local.env_suffix}"
  }
  
  service_account_name = "${var.service_account_name}${local.env_suffix}"
  
  api_gateway_name = "relex-api${local.env_suffix}"
  
  # Environment-specific domain configuration
  api_domain = var.environment == "prod" ? "api.${var.domain_name}" : "api-${var.environment}.${var.domain_name}"
  
  # Common tags for all resources
  common_labels = {
    environment = var.environment
    managed_by  = "terraform"
    project     = "relex"
  }
} 