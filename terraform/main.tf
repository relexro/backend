terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
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

# Additional functions for chat, auth, payments, and business would be defined similarly 