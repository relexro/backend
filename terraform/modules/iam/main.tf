# IAM - Grant Firebase Functions service account access to Firestore
resource "google_project_iam_member" "functions_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
}

# IAM - Grant Firebase Functions service account access to Storage
resource "google_project_iam_member" "functions_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
}

# Grant the API Gateway service account permission to invoke Cloud Functions
resource "google_project_iam_member" "invoker_role" {
  project = var.project_id
  role    = "roles/cloudfunctions.invoker"
  member  = "serviceAccount:${var.api_gateway_sa_email}"
} 