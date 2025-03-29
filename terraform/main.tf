# Configure the Google Cloud provider
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Configure Cloudflare provider using CF_RELEX_TOKEN environment variable
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Provider configuration for modules
terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

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

# Create storage buckets
module "storage" {
  source     = "./modules/storage"
  project_id = var.project_id
  region     = var.region

  depends_on = [module.apis]
}

# Deploy Cloud Functions
module "cloud_functions" {
  source                = "./modules/cloud_functions"
  project_id           = var.project_id
  region              = var.region
  functions_bucket_name = module.storage.functions_bucket_name
  functions_source_path = "${path.root}/../functions/src"
  functions_zip_path    = "${path.root}/functions-source.zip"
  api_gateway_sa_email = "api-gateway-sa@${var.project_id}.iam.gserviceaccount.com"
  stripe_secret_key    = var.stripe_secret_key
  stripe_webhook_secret = var.stripe_webhook_secret

  depends_on = [module.apis, module.storage]
}

# Create API Gateway with function URIs
module "api_gateway" {
  source           = "./modules/api_gateway"
  project_id       = var.project_id
  region           = var.apig_region
  openapi_spec_path = "${path.root}/openapi_spec.yaml"
  function_uris    = {
    for name in var.function_names : name => format("https://%s-%s.cloudfunctions.net/%s",
      var.region,
      var.project_id,
      name
    )
  }

  depends_on = [module.apis, module.cloud_functions]
}

# Configure Cloudflare DNS for API Gateway
module "cloudflare" {
  source           = "./modules/cloudflare"
  domain_name      = var.domain_name
  subdomain        = var.api_subdomain
  gateway_hostname = module.api_gateway.gateway_hostname
  zone_id          = var.cloudflare_zone_id

  depends_on = [module.api_gateway]
  
  providers = {
    cloudflare = cloudflare
  }
}

# Set up IAM roles and permissions
module "iam" {
  source              = "./modules/iam"
  project_id          = var.project_id
  api_gateway_sa_email = module.api_gateway.api_gateway_sa_email

  depends_on = [module.api_gateway]
} 