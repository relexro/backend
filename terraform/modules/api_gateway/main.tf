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

# Create the API resource
resource "google_api_gateway_api" "api" {
  provider = google-beta
  api_id   = "relex-api"
}

# Create the API Config with the OpenAPI spec from file
resource "google_api_gateway_api_config" "api_config" {
  provider      = google-beta
  api           = google_api_gateway_api.api.api_id
  api_config_id = "relex-api-config-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  display_name  = "Relex API Config"

  openapi_documents {
    document {
      path = "spec.yaml"
      contents = base64encode(templatefile(var.openapi_spec_path, {
        project_id = var.project_id
        region = var.region
        function_uris = var.function_uris
        api_domain = var.api_domain
      }))
    }
  }

  gateway_config {
    backend_config {
      google_service_account = var.api_gateway_sa_email
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Deploy the API Gateway
resource "google_api_gateway_gateway" "gateway" {
  provider     = google-beta
  region       = var.region
  api_config   = google_api_gateway_api_config.api_config.id
  gateway_id   = "relex-api-gateway"
  display_name = "Relex API Gateway"

  depends_on = [google_api_gateway_api_config.api_config]
} 