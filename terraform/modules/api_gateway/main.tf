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
  timestamp    = formatdate("YYYYMMDDhhmmss", timestamp())
  random_suffix = substr(sha256(local.timestamp), 0, 6)
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
  api_config_id = "relex-api-config-${local.timestamp}-${local.random_suffix}"
  display_name  = "Relex API Config"
  project       = var.project_id
  
  openapi_documents {
    document {
      path = "spec.yaml"
      contents = base64encode(
  templatefile(var.openapi_spec_path, { # Path to your openapi_spec.yaml (passed from root)
    # Variables needed by the template file:
    project_id    = var.project_id     # Pass project_id input variable
    api_domain    = var.api_domain     # Pass api_domain input variable
    region        = var.region         # Pass region input variable
    function_uris = var.function_uris  # <-- Pass the function_uris map received as input DIRECTLY
  })
)
    }
  }

  lifecycle {
    create_before_destroy = true
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
  gateway_id   = "relex-api-gateway-${local.timestamp}-${local.random_suffix}"
  display_name = "Relex API Gateway"
  project      = var.project_id
  
  depends_on = [google_api_gateway_api_config.api_config]
} 