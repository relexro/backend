// File: api_gateway.tf
// API Gateway configuration for Relex Backend

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "relexro"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west3"
}

// Create the API resource
resource "google_api_gateway_api" "relex_api" {
  provider     = google-beta
  api_id       = "relex-api"
  display_name = "Relex API"
  project      = var.project_id
}

// Create the API Config that uses the OpenAPI specification
resource "google_api_gateway_api_config" "relex_api_config" {
  provider      = google-beta
  api           = google_api_gateway_api.relex_api.api_id
  api_config_id = "relex-api-config-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  display_name  = "Relex API Config"
  project       = var.project_id

  openapi_documents {
    document {
      path     = "openapi_spec.yaml"
      contents = filebase64("openapi_spec.yaml")
    }
  }

  gateway_config {
    backend_config {
      google_service_account = "relex-api-gateway-sa@${var.project_id}.iam.gserviceaccount.com"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

// Service account for API Gateway
resource "google_service_account" "api_gateway_sa" {
  provider     = google-beta
  account_id   = "relex-api-gateway-sa"
  display_name = "Relex API Gateway Service Account"
  project      = var.project_id
}

// Grant the API Gateway service account permission to invoke Cloud Functions
resource "google_project_iam_member" "invoker_role" {
  provider = google-beta
  project  = var.project_id
  role     = "roles/cloudfunctions.invoker"
  member   = "serviceAccount:${google_service_account.api_gateway_sa.email}"
}

// Deploy the API Gateway
resource "google_api_gateway_gateway" "relex_gateway" {
  provider     = google-beta
  gateway_id   = "relex-gateway"
  display_name = "Relex API Gateway"
  api_config   = google_api_gateway_api_config.relex_api_config.id
  project      = var.project_id
  region       = var.region
}

// Output the API Gateway URL
output "api_gateway_url" {
  value = "https://${google_api_gateway_gateway.relex_gateway.default_hostname}"
} 