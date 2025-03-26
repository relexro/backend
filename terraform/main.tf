terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.80.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.80.0"
    }
  }
  backend "local" {
    path = "terraform.tfstate"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "firebase" {
  project = var.project_id
  service = "firebase.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firestore" {
  project = var.project_id
  service = "firestore.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage" {
  project = var.project_id
  service = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudfunctions" {
  project = var.project_id
  service = "cloudfunctions.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "run" {
  project = var.project_id
  service = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# IAM - Grant Firebase Functions service account access to Firestore
resource "google_project_iam_member" "functions_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
  
  depends_on = [google_project_service.firebase]
}

# IAM - Grant Firebase Functions service account access to Storage
resource "google_project_iam_member" "functions_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
  
  depends_on = [google_project_service.firebase]
}

# Storage bucket for files
resource "google_storage_bucket" "files_bucket" {
  name     = "${var.project_id}-files"
  location = var.region
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  depends_on = [google_project_service.storage]
}

# Storage bucket for function source code
resource "google_storage_bucket" "functions_bucket" {
  name     = "${var.project_id}-functions"
  location = var.region
  uniform_bucket_level_access = true
  
  depends_on = [google_project_service.storage]
}

# Create a ZIP archive of the functions source code
data "archive_file" "functions_source" {
  type        = "zip"
  source_dir  = "${path.module}/../functions/src"
  output_path = "${path.module}/functions-source.zip"
}

# Upload function source code to Cloud Storage
resource "google_storage_bucket_object" "functions_source_zip" {
  name   = "relex-backend-functions-source-${data.archive_file.functions_source.output_md5}.zip"
  bucket = google_storage_bucket.functions_bucket.name
  source = data.archive_file.functions_source.output_path
}

# Cloud Function for create_case
resource "google_cloudfunctions2_function" "create_case_function" {
  name        = "relex-backend-create-case"
  description = "Create a new case"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "cases_create_case"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the function
resource "google_cloud_run_service_iam_member" "create_case_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.create_case_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for get_case
resource "google_cloudfunctions2_function" "get_case_function" {
  name        = "relex-backend-get-case"
  description = "Get a case by ID"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "cases_get_case"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the get_case function
resource "google_cloud_run_service_iam_member" "get_case_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.get_case_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for list_cases
resource "google_cloudfunctions2_function" "list_cases_function" {
  name        = "relex-backend-list-cases"
  description = "List cases with optional filtering"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "cases_list_cases"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the list_cases function
resource "google_cloud_run_service_iam_member" "list_cases_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.list_cases_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for test_function
resource "google_cloudfunctions2_function" "test_function" {
  name        = "relex-backend-test-function"
  description = "Test function to verify deployment"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "test_function"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the test function
resource "google_cloud_run_service_iam_member" "test_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.test_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for archive_case
resource "google_cloudfunctions2_function" "archive_case_function" {
  name        = "relex-backend-archive-case"
  description = "Archive a case by ID"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "cases_archive_case"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the archive_case function
resource "google_cloud_run_service_iam_member" "archive_case_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.archive_case_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for delete_case
resource "google_cloudfunctions2_function" "delete_case_function" {
  name        = "relex-backend-delete-case"
  description = "Mark a case as deleted"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "cases_delete_case"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the delete_case function
resource "google_cloud_run_service_iam_member" "delete_case_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.delete_case_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for upload_file
resource "google_cloudfunctions2_function" "upload_file_function" {
  name        = "relex-backend-upload-file"
  description = "Upload a file to a case"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "cases_upload_file"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the upload_file function
resource "google_cloud_run_service_iam_member" "upload_file_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.upload_file_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for download_file
resource "google_cloudfunctions2_function" "download_file_function" {
  name        = "relex-backend-download-file"
  description = "Generate signed URL for downloading a file"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "cases_download_file"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the download_file function
resource "google_cloud_run_service_iam_member" "download_file_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.download_file_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Auth Functions

# Cloud Function for validate_user
resource "google_cloudfunctions2_function" "validate_user_function" {
  name        = "relex-backend-validate-user"
  description = "Validate a user's authentication token"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "auth_validate_user"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the validate_user function
resource "google_cloud_run_service_iam_member" "validate_user_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.validate_user_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for check_permissions
resource "google_cloudfunctions2_function" "check_permissions_function" {
  name        = "relex-backend-check-permissions"
  description = "Check a user's permissions for a resource"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "auth_check_permissions"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the check_permissions function
resource "google_cloud_run_service_iam_member" "check_permissions_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.check_permissions_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for get_user_role
resource "google_cloudfunctions2_function" "get_user_role_function" {
  name        = "relex-backend-get-user-role"
  description = "Retrieve a user's role in a business"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "auth_get_user_role"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the get_user_role function
resource "google_cloud_run_service_iam_member" "get_user_role_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.get_user_role_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Business Functions

# Create Organization Function (renamed from create_business_function)
resource "google_cloudfunctions2_function" "create_organization_function" {
  name        = "relex-backend-create-organization"
  description = "Create a new organization account"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_create_organization"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the create_organization function
resource "google_cloud_run_service_iam_member" "create_organization_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.create_organization_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Get Organization Function (renamed from get_business_function)
resource "google_cloudfunctions2_function" "get_organization_function" {
  name        = "relex-backend-get-organization"
  description = "Get an organization account by ID"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_get_organization"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the get_organization function
resource "google_cloud_run_service_iam_member" "get_organization_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.get_organization_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Add Organization User Function (renamed from add_business_user_function)
resource "google_cloudfunctions2_function" "add_organization_user_function" {
  name        = "relex-backend-add-organization-user"
  description = "Add a user to an organization account"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_add_organization_user"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the add_organization_user function
resource "google_cloud_run_service_iam_member" "add_organization_user_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.add_organization_user_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Set User Role Function (renamed from set_user_role_function)
resource "google_cloudfunctions2_function" "set_user_role_function" {
  name        = "relex-backend-set-user-role"
  description = "Update a user's role in an organization"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_set_user_role"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the set_user_role function
resource "google_cloud_run_service_iam_member" "set_user_role_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.set_user_role_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Update Organization Function (renamed from update_business_function)
resource "google_cloudfunctions2_function" "update_organization_function" {
  name        = "relex-backend-update-organization"
  description = "Update an organization account"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_update_organization"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the update_organization function
resource "google_cloud_run_service_iam_member" "update_organization_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.update_organization_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# List Organization Users Function (renamed from list_business_users_function)
resource "google_cloudfunctions2_function" "list_organization_users_function" {
  name        = "relex-backend-list-organization-users"
  description = "List users in an organization"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_list_organization_users"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the list_organization_users function
resource "google_cloud_run_service_iam_member" "list_organization_users_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.list_organization_users_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Remove Organization User Function (renamed from remove_business_user_function)
resource "google_cloudfunctions2_function" "remove_organization_user_function" {
  name        = "relex-backend-remove-organization-user"
  description = "Remove a user from an organization"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_remove_organization_user"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the remove_organization_user function
resource "google_cloud_run_service_iam_member" "remove_organization_user_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.remove_organization_user_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Chat Functions

# Cloud Function for receive_prompt
resource "google_cloudfunctions2_function" "receive_prompt_function" {
  name        = "relex-backend-receive-prompt"
  description = "Receive a prompt from a user"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "chat_receive_prompt"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the receive_prompt function
resource "google_cloud_run_service_iam_member" "receive_prompt_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.receive_prompt_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for send_to_vertex_ai
resource "google_cloudfunctions2_function" "send_to_vertex_ai_function" {
  name        = "relex-backend-send-to-vertex-ai"
  description = "Send a prompt to Vertex AI"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "chat_send_to_vertex_ai"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the send_to_vertex_ai function
resource "google_cloud_run_service_iam_member" "send_to_vertex_ai_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.send_to_vertex_ai_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for store_conversation
resource "google_cloudfunctions2_function" "store_conversation_function" {
  name        = "relex-backend-store-conversation"
  description = "Store a conversation"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "chat_store_conversation"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the store_conversation function
resource "google_cloud_run_service_iam_member" "store_conversation_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.store_conversation_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for enrich_prompt
resource "google_cloudfunctions2_function" "enrich_prompt_function" {
  name        = "relex-backend-enrich-prompt"
  description = "Enrich a prompt with case context"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "chat_enrich_prompt"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the enrich_prompt function
resource "google_cloud_run_service_iam_member" "enrich_prompt_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.enrich_prompt_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for create_payment_intent
resource "google_cloudfunctions2_function" "create_payment_intent_function" {
  name        = "relex-backend-create-payment-intent"
  description = "Create a Stripe payment intent"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "payments_create_payment_intent"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      STRIPE_SECRET_KEY = "sk_test_51KGx9ySBqRYQv8xZY0PQnQkmQ2AwZsEZyHcLgjE8gMmL8GQbQYhIwzqnTCwGQ1zqOVlOZBHFGpPx"
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the create_payment_intent function
resource "google_cloud_run_service_iam_member" "create_payment_intent_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.create_payment_intent_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Function for create_checkout_session
resource "google_cloudfunctions2_function" "create_checkout_session_function" {
  name        = "relex-backend-create-checkout-session"
  description = "Create a Stripe checkout session"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "payments_create_checkout_session"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      STRIPE_SECRET_KEY = "sk_test_51KGx9ySBqRYQv8xZY0PQnQkmQ2AwZsEZyHcLgjE8gMmL8GQbQYhIwzqnTCwGQ1zqOVlOZBHFGpPx"
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the create_checkout_session function
resource "google_cloud_run_service_iam_member" "create_checkout_session_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.create_checkout_session_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Firebase Authentication Configuration
resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id
  depends_on = [google_project_service.firebase]
}

resource "google_firebase_web_app" "default" {
  provider     = google-beta
  project      = var.project_id
  display_name = "Relex Web App"
  depends_on   = [google_firebase_project.default]
}

# Enable Identity Platform API
resource "google_project_service" "identity_platform" {
  project = var.project_id
  service = "identitytoolkit.googleapis.com"
  disable_on_destroy = false
}

# Configure authentication methods in the console
# We can't fully automate the OAuth setup with Terraform
# Instructions are documented in status.md

# Output variables to access deployed resources are in outputs.tf

# Organization Membership Functions
resource "google_cloudfunctions2_function" "add_organization_member_function" {
  name        = "relex-backend-add-organization-member"
  description = "Add a member to an organization"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_membership_add_organization_member"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the add_organization_member function
resource "google_cloud_run_service_iam_member" "add_organization_member_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.add_organization_member_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloudfunctions2_function" "set_organization_member_role_function" {
  name        = "relex-backend-set-organization-member-role"
  description = "Set a member's role in an organization"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_membership_set_organization_member_role"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the set_organization_member_role function
resource "google_cloud_run_service_iam_member" "set_organization_member_role_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.set_organization_member_role_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloudfunctions2_function" "list_organization_members_function" {
  name        = "relex-backend-list-organization-members"
  description = "List members of an organization"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_membership_list_organization_members"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the list_organization_members function
resource "google_cloud_run_service_iam_member" "list_organization_members_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.list_organization_members_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloudfunctions2_function" "remove_organization_member_function" {
  name        = "relex-backend-remove-organization-member"
  description = "Remove a member from an organization"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_membership_remove_organization_member"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the remove_organization_member function
resource "google_cloud_run_service_iam_member" "remove_organization_member_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.remove_organization_member_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloudfunctions2_function" "get_user_organization_role_function" {
  name        = "relex-backend-get-user-organization-role"
  description = "Get a user's role in an organization"
  location    = var.region
  
  build_config {
    runtime     = "python310"
    entry_point = "organization_membership_get_user_organization_role"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.functions_source_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count = 10
    available_memory   = "256Mi"
    timeout_seconds    = 60
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
    # Use default service account
    service_account_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.run,
    google_project_service.artifactregistry
  ]
}

# Allow unauthenticated invocation of the get_user_organization_role function
resource "google_cloud_run_service_iam_member" "get_user_organization_role_function_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.get_user_organization_role_function.name
  role     = "roles/run.invoker"
  member   = "allUsers"
} 