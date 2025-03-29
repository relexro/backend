# Filename: terraform/main.tf

terraform {
  required_version = ">= 1.0" # Added for good practice

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.21.0" # Updated to latest version that supports all required attributes
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.21.0" # Keep in sync with google provider version
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.2" # Example constraint
    }
  }

  # Backend is configured in backend.tf
}

# Configure the Google Cloud provider
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Configure Cloudflare provider
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# --- Service Account Definition ---

resource "google_service_account" "relex_functions_sa" {
  project      = var.project_id
  account_id   = "relex-functions-runtime"
  display_name = "Service Account for Relex Cloud Functions Runtime"
}

# Create API Gateway service account
resource "google_service_account" "api_gateway_sa" {
  project      = var.project_id
  account_id   = "api-gateway-sa"
  display_name = "API Gateway Service Account"
}

# --- Secret Definitions ---

resource "google_secret_manager_secret" "stripe_secret_key" {
  secret_id = "stripe-secret-key"
  project   = var.project_number

  replication {
    auto {}
  }

  lifecycle {
    ignore_changes = [
      labels,
      annotations,
      version_aliases,
      replication
    ]
  }
}

resource "google_secret_manager_secret" "stripe_webhook_secret" {
  secret_id = "stripe-webhook-secret"
  project   = var.project_number

  replication {
    auto {}
  }

  lifecycle {
    ignore_changes = [
      labels,
      annotations,
      version_aliases,
      replication
    ]
  }
}

# --- Module Definitions ---

# Enable required APIs
module "apis" {
  source     = "./modules/apis"
  project_id = var.project_id
}

# Configure Firebase
module "firebase" {
  source     = "./modules/firebase"
  project_id = var.project_id

  depends_on = [module.apis]
}

# Create storage buckets (including the one for functions source)
module "storage" {
  source     = "./modules/storage"
  project_id = var.project_id
  region     = var.region

  depends_on = [module.apis]
}

# Deploy Cloud Functions
module "cloud_functions" {
  source = "./modules/cloud_functions"

  project_id                          = var.project_id
  region                              = var.region
  functions_bucket_name               = module.storage.functions_bucket_name
  functions_source_path               = "${path.module}/../functions/src"
  functions_zip_path                  = "${path.module}/functions-source.zip"
  functions_service_account_email     = google_service_account.relex_functions_sa.email
  stripe_secret_key_name             = google_secret_manager_secret.stripe_secret_key.secret_id
  stripe_webhook_secret_name         = google_secret_manager_secret.stripe_webhook_secret.secret_id
  api_gateway_sa_email               = google_service_account.api_gateway_sa.email

  depends_on = [
    module.apis,
    module.storage,
    google_service_account.relex_functions_sa,
    google_service_account.api_gateway_sa,
    google_secret_manager_secret.stripe_secret_key,
    google_secret_manager_secret.stripe_webhook_secret
  ]
}

# Create API Gateway with function URIs
module "api_gateway" {
  source            = "./modules/api_gateway"
  project_id        = var.project_id
  region            = var.region
  openapi_spec_path = "${path.module}/openapi_spec.yaml"
  function_uris     = module.cloud_functions.function_uris
  api_gateway_sa_email = google_service_account.api_gateway_sa.email

  depends_on = [
    module.apis,
    module.cloud_functions,
    google_service_account.api_gateway_sa
  ]
}

# Configure Cloudflare DNS for API Gateway
module "cloudflare" {
  source           = "./modules/cloudflare"
  domain_name      = var.domain_name
  subdomain        = var.api_subdomain
  # Ensure the output name matches what your api_gateway module provides
  gateway_hostname = module.api_gateway.gateway_hostname
  zone_id          = var.cloudflare_zone_id

  depends_on = [module.api_gateway]

  providers = {
    cloudflare = cloudflare
  }
}

# Set up IAM roles and permissions using the IAM module
module "iam" {
  source              = "./modules/iam"
  project_id          = var.project_id
  api_gateway_sa_email = google_service_account.api_gateway_sa.email
  relex_functions_service_account_email = google_service_account.relex_functions_sa.email

  depends_on = [
    google_service_account.api_gateway_sa,
    google_service_account.relex_functions_sa
  ]
}