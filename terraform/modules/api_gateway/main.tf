# Create the API Gateway service account
resource "google_service_account" "api_gateway" {
  account_id   = "api-gateway-sa"
  display_name = "API Gateway Service Account"
  
  lifecycle {
    ignore_changes = [
      display_name,
      description
    ]
  }
}

# Create the API resource
resource "google_api_gateway_api" "api" {
  provider = google-beta
  api_id   = "relex-api"
}

# Create the API Config with a minimal OpenAPI spec
resource "google_api_gateway_api_config" "api_config" {
  provider      = google-beta
  api           = google_api_gateway_api.api.api_id
  api_config_id = "relex-api-config-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  display_name  = "Relex API Config"

  openapi_documents {
    document {
      path = "spec.yaml"
      contents = base64encode(<<-EOT
        swagger: '2.0'
        info:
          title: 'Relex API Gateway'
          description: 'API Gateway for Relex backend'
          version: '1.0.0'
        host: 'gateway.example.com'
        basePath: /v1
        schemes:
          - https
        paths:
          /health:
            get:
              summary: Health check endpoint
              operationId: health
              responses:
                '200':
                  description: A successful response
                  schema:
                    type: object
                    properties:
                      status:
                        type: string
              x-google-backend:
                address: 'https://${var.region}-relexro.cloudfunctions.net/relex-backend-get-user-profile'
      EOT
      )
    }
  }

  gateway_config {
    backend_config {
      google_service_account = google_service_account.api_gateway.email
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

# Output the API Gateway URL
output "api_gateway_url" {
  value = google_api_gateway_gateway.gateway.default_hostname
}

# Output the API Gateway service account email
output "api_gateway_sa_email" {
  value = google_service_account.api_gateway.email
} 