# Firebase Authentication Configuration
resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id
}

resource "google_firebase_web_app" "default" {
  provider     = google-beta
  project      = var.project_id
  display_name = "Relex Web App"
  depends_on   = [google_firebase_project.default]
}

# Firestore Security Rules Deployment
resource "google_firestore_security_rule" "rules" {
  provider    = google-beta
  project     = var.project_id
  database    = "(default)"
  rules_file  = "${path.module}/rules/firestore.rules"
  depends_on  = [google_firebase_project.default]
} 