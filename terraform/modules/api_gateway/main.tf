# Create the API Gateway service account
# resource "google_service_account" "api_gateway" {
#   account_id   = "api-gateway-sa"
#   display_name = "API Gateway Service Account"
#
#   lifecycle {
#     ignore_changes = [
#       display_name,
#       description
#     ]
#   }
# }

locals {
  # Create a stable hash based on the OpenAPI spec and function URIs
  # This ensures the API config only changes when the spec or functions change
  openapi_content = templatefile(var.openapi_spec_path, {
    project_id    = var.project_id
    api_domain    = var.api_domain
    region        = var.region
    function_uris = var.function_uris
  })

  # Create a hash of the OpenAPI content
  openapi_hash = substr(sha256(local.openapi_content), 0, 8)
}

# Create the API resource
resource "google_api_gateway_api" "api" {
  provider     = google-beta
  api_id       = "relex-api"
  display_name = "Relex API"
  project      = var.project_id
}

# Create the API Config with the OpenAPI spec from file
resource "google_api_gateway_api_config" "api_config" {
  provider      = google-beta
  api           = google_api_gateway_api.api.api_id
  api_config_id = "relex-api-config-${local.openapi_hash}"
  display_name  = "Relex API Config"
  project       = var.project_id

  openapi_documents {
    document {
      path = "spec.yaml"
      contents = base64encode(local.openapi_content)
    }
  }

  lifecycle {
    create_before_destroy = true

    # Prevent recreation when only metadata changes
    ignore_changes = [
      labels,
      display_name
    ]
  }

  gateway_config {
    backend_config {
      google_service_account = var.api_gateway_sa_email
    }
  }
}

# Deploy the API Gateway
resource "google_api_gateway_gateway" "gateway" {
  provider     = google-beta
  api_config   = google_api_gateway_api_config.api_config.id
  gateway_id   = "relex-api-gateway-${local.openapi_hash}"
  display_name = "Relex API Gateway"
  project      = var.project_id

  depends_on = [google_api_gateway_api_config.api_config]

  lifecycle {
    # Prevent recreation of the gateway when only metadata changes
    ignore_changes = [
      labels,
      display_name
    ]
  }
}