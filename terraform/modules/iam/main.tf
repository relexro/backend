# Description: Manages essential IAM bindings for the Relex application components.


# --- Dedicated Service Account Permissions for Relex Functions ---

# Grant the dedicated functions SA access to Firestore
resource "google_project_iam_member" "relex_functions_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user" # Allows reading/writing Firestore data
  member  = "serviceAccount:${var.relex_functions_service_account_email}"
}

# Grant the dedicated functions SA access to Cloud Storage (for file uploads/downloads)
resource "google_project_iam_member" "relex_functions_storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin" # Allows managing objects in buckets
  member  = "serviceAccount:${var.relex_functions_service_account_email}"
}

# Grant the dedicated functions SA access to Secret Manager (for Stripe keys, etc.)
resource "google_project_iam_member" "relex_functions_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor" # Allows reading secret values
  member  = "serviceAccount:${var.relex_functions_service_account_email}"
}

# Grant the dedicated functions SA access to Secret Manager (for Stripe keys, etc.)
resource "google_project_iam_member" "relex_functions_secret_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${var.relex_functions_service_account_email}"
}

# Grant the dedicated functions SA permission to write logs
resource "google_project_iam_member" "relex_functions_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${var.relex_functions_service_account_email}"
}

# Grant the dedicated functions SA permission to publish Pub/Sub topics (if needed, e.g., for async tasks)
# resource "google_project_iam_member" "relex_functions_pubsub_publisher" {
#   project = var.project_id
#   role    = "roles/pubsub.publisher"
#   member  = "serviceAccount:${var.relex_functions_service_account_email}"
# }

# Grant the dedicated functions SA permission to call Vertex AI (if needed)
# resource "google_project_iam_member" "relex_functions_vertex_ai_user" {
#   project = var.project_id
#   role    = "roles/aiplatform.user"
#   member  = "serviceAccount:${var.relex_functions_service_account_email}"
# }


# --- API Gateway Permissions ---

# Grant the API Gateway service account permission to invoke Cloud Functions
resource "google_project_iam_member" "invoker_role_for_api_gateway" {
  project = var.project_id
  role    = "roles/cloudfunctions.invoker"
  member  = "serviceAccount:${var.api_gateway_sa_email}"
}

# Grant the API Gateway service account permission to write logs
resource "google_project_iam_member" "api_gateway_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${var.api_gateway_sa_email}"
}


# --- REMOVED: Old permissions targeting default SAs (if they existed here) ---
# Remove any blocks that granted roles to:
# - serviceAccount:49787884280-compute@developer.gserviceaccount.com
# - serviceAccount:${var.project_id}@appspot.gserviceaccount.com 
# (Unless the App Engine SA is explicitly needed for something else)