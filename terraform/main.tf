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

# Create storage buckets and upload function source
module "storage" {
  source              = "./modules/storage"
  project_id          = var.project_id
  region              = var.region
  functions_source_path = "../functions/src"
  functions_zip_path  = "functions-source.zip"

  depends_on = [module.apis]
}

# Deploy Cloud Functions first (API Gateway needs the function URIs)
module "cloud_functions" {
  source              = "./modules/cloud_functions"
  project_id          = var.project_id
  region              = var.region
  functions_bucket_name = module.storage.functions_bucket_name
  functions_source_path = "../functions/src"
  functions_zip_path    = "functions-source.zip"
  functions_zip_name    = module.storage.functions_source_zip_name
  api_gateway_sa_email = "api-gateway-sa@${var.project_id}.iam.gserviceaccount.com"

  depends_on = [module.apis, module.storage]
}

# Create API Gateway and service account
module "api_gateway" {
  source           = "./modules/api_gateway"
  project_id       = var.project_id
  region           = var.apig_region
  openapi_spec_path = "openapi_spec.yaml"
  function_uris    = {
    for name, uri in module.cloud_functions.function_uris : name => format("https://%s-%s.cloudfunctions.net/%s",
      var.region,
      var.project_id,
      name
    )
  }

  depends_on = [module.apis, module.cloud_functions]
}

# Set up IAM roles and permissions
module "iam" {
  source              = "./modules/iam"
  project_id          = var.project_id
  api_gateway_sa_email = module.api_gateway.api_gateway_sa_email

  depends_on = [module.api_gateway]
} 