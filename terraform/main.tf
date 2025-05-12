# Filename: terraform/main.tf

terraform {
  required_version = ">= 1.0" # Added for good practice

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.21.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.21.0"
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

locals {
  env_suffix = var.environment == "prod" ? "" : "-${var.environment}"

  # Environment-specific resource names
  # function_names has been removed as it's handled by the cloud_functions module

  bucket_names = {
    for k, v in var.bucket_names : k => "${split("-", var.project_id)[0]}-${v}${local.env_suffix}"
  }

  service_account_name = "${var.service_account_name}${local.env_suffix}"

  api_gateway_name = "${split("-", var.project_id)[0]}-api${local.env_suffix}"

  # Environment-specific domain configuration
  api_domain = var.environment == "prod" ? "api.${var.domain_name}" : "api-${var.environment}.${var.domain_name}"

  # Common tags for all resources
  common_labels = {
    environment = var.environment
    managed_by  = "terraform"
    project     = split("-", var.project_id)[0]
  }

  functions_service_account_email = "serviceAccount:${google_service_account.functions.email}"

  # Use only the actual deployed function URIs for the API Gateway
  # This ensures the API Gateway only routes to real, deployed functions
  complete_function_uris = module.cloud_functions.function_uris
}

# --- Service Account Definition ---

# Service Account for Cloud Functions
resource "google_service_account" "functions" {
  account_id   = local.service_account_name
  display_name = "Service Account for Cloud Functions ${var.environment}"
  description  = "Used by Cloud Functions in the ${var.environment} environment"

  # Removed prevent_destroy to allow destruction when needed
  lifecycle {
    ignore_changes = [
      description,
      display_name
    ]
  }
}

# IAM bindings for the service account
resource "google_project_iam_member" "functions_invoker" {
  project = var.project_id
  role    = "roles/cloudfunctions.invoker"
  member  = local.functions_service_account_email

  # Using the more effective lifecycle configuration
  lifecycle {
    create_before_destroy = true
  }
}


# --- Secret Definitions ---
# We're no longer trying to access secrets in Terraform
# The secret environment variables will be configured manually

# --- Module Definitions ---

# Enable required APIs
module "apis" {
  source     = "./modules/apis"
  project_id = var.project_id
}

# Enable Firebase services (Authentication, Firestore)
module "firebase" {
  source             = "./modules/firebase"
  project_id         = var.project_id
  firestore_location = var.region

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

  project_id                      = var.project_id
  region                          = var.region
  environment                     = var.environment
  functions_bucket_name           = module.storage.functions_bucket_name
  functions_source_path           = "${path.module}/../functions/src"
  functions_zip_path              = "${path.module}/functions-source.zip"
  functions_service_account_email = trimprefix(local.functions_service_account_email, "serviceAccount:")
  api_gateway_sa_email            = trimprefix(local.functions_service_account_email, "serviceAccount:")
  project                         = var.project_id
  service_account_email           = trimprefix(local.functions_service_account_email, "serviceAccount:")

  # Ensure consistent naming across environments
  environment_suffix              = local.env_suffix

  depends_on = [
    module.apis,
    module.storage,
    google_service_account.functions
  ]
}

# Create API Gateway with function URIs
module "api_gateway" {
  source               = "./modules/api_gateway"
  project_id           = var.project_id
  region               = var.region
  openapi_spec_path    = "${path.module}/openapi_spec.yaml"
  function_uris        = local.complete_function_uris
  api_gateway_sa_email = trimprefix(local.functions_service_account_email, "serviceAccount:")
  # api_domain           = local.api_domain
  environment          = var.environment

  depends_on = [
    module.apis,
    module.cloud_functions
  ]
}

# Configure Cloudflare DNS for API Gateway
module "cloudflare" {
  source      = "./modules/cloudflare"
  domain_name = var.domain_name
  subdomain   = local.api_domain
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
  source                                = "./modules/iam"
  project_id                            = var.project_id
  api_gateway_sa_email                  = trimprefix(local.functions_service_account_email, "serviceAccount:")
  relex_functions_service_account_email = trimprefix(local.functions_service_account_email, "serviceAccount:")

  depends_on = [
    google_service_account.functions
  ]
}
/*
# Add RAG module after other modules
module "rag_system" {
  source     = "./modules/rag"
  project_id = var.project_id
  # Optional: override default suffixes if needed
  # datastore_id_suffix = "main-rag-datastore"
  # engine_id_suffix    = "main-rag-engine"
  search_add_ons = ["SEARCH_ADD_ON_LLM"]  # Enable LLM add-on for RAG

  depends_on = [
    module.apis  # Ensure required APIs are enabled
  ]
} */

# The following resources are now handled by the cloud_functions module
# and should be commented out to prevent duplicate resource creation

/*
# Storage buckets
resource "google_storage_bucket" "functions_source" {
  name                        = "${local.bucket_names["functions"]}-source"
  location                    = var.region
  uniform_bucket_level_access = true

  labels = local.common_labels

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "files" {
  name                        = local.bucket_names["files"]
  location                    = var.region
  uniform_bucket_level_access = true

  labels = local.common_labels
}

# Cloud Functions source code
resource "google_storage_bucket_object" "function_source" {
  for_each = var.functions

  name   = "${each.key}/function-source-${filemd5("../functions/src/main.py")}.zip"
  bucket = google_storage_bucket.functions_source.name
  source = data.archive_file.function_source.output_path
}

# Zip the function source code
data "archive_file" "function_source" {
  type        = "zip"
  source_dir  = "../functions/src"
  output_path = "/tmp/function-source.zip"
}

# Cloud Functions
resource "google_cloudfunctions2_function" "functions" {
  for_each = var.functions

  name        = local.function_names[each.key]
  location    = var.region
  description = "Cloud Function for ${each.value.name} (${var.environment})"

  build_config {
    runtime     = "python310"
    entry_point = each.value.entry_point
    source {
      storage_source {
        bucket = google_storage_bucket.functions_source.name
        object = google_storage_bucket_object.function_source[each.key].name
      }
    }
  }

  service_config {
    max_instance_count             = each.value.max_instance_count
    min_instance_count            = each.value.min_instance_count
    available_memory              = each.value.available_memory
    available_cpu                 = each.value.available_cpu
    timeout_seconds               = each.value.timeout_seconds
    service_account_email         = google_service_account.functions.email
    ingress_settings             = "ALLOW_ALL"
    all_traffic_on_latest_revision = true

    environment_variables = merge(
      each.value.env_vars,
      {
        ENVIRONMENT = var.environment
      }
    )

    dynamic "secret_environment_variables" {
      for_each = lookup(each.value, "secret_env_vars", [])
      content {
        key        = secret_environment_variables.value.key
        project_id = var.project_id
        secret     = secret_environment_variables.value.secret
        version    = "latest"
      }
    }
  }

  labels = local.common_labels
}

# API Gateway
resource "google_api_gateway_api" "api" {
  provider = google-beta
  api_id   = local.api_gateway_name

  labels = local.common_labels
}

# API Gateway API Config
resource "google_api_gateway_api_config" "api" {
  provider = google-beta
  api      = google_api_gateway_api.api.api_id

  openapi_documents {
    document {
      path     = "openapi.yaml"
      contents = base64encode(templatefile("${path.module}/openapi_spec.yaml", {
        project_id    = var.project_id
        region        = var.region
        environment   = var.environment
        function_urls = {
          for k, v in google_cloudfunctions2_function.functions : k => v.url
        }
      }))
    }
  }

  lifecycle {
    create_before_destroy = true
  }

  labels = local.common_labels
}

# API Gateway Gateway
resource "google_api_gateway_gateway" "gateway" {
  provider   = google-beta
  api_config = google_api_gateway_api_config.api.id
  gateway_id = local.api_gateway_name
  region     = var.region

  labels = local.common_labels
}

# Cloudflare DNS record for API Gateway
resource "cloudflare_record" "api" {
  zone_id = var.cloudflare_zone_id
  name    = split(".", local.api_domain)[0]
  value   = google_api_gateway_gateway.gateway.default_hostname
  type    = "CNAME"
  proxied = true
}
*/