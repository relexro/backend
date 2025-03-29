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

locals {
  firestore_rules = file("${path.module}/rules/firestore.rules")
}

# Firestore Security Rules Deployment
resource "google_firebaserules_ruleset" "rules" {
  provider = google-beta
  project  = var.project_id
  source {
    files {
      content = local.firestore_rules
      name    = "firestore.rules"
    }
  }
  depends_on = [google_firebase_project.default]
}

# Release the ruleset for Firestore
resource "google_firebaserules_release" "firestore" {
  provider     = google-beta
  project      = var.project_id
  name         = "cloud.firestore"
  ruleset_name = google_firebaserules_ruleset.rules.name
  depends_on   = [google_firebaserules_ruleset.rules]
} 