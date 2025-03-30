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
  timestamp = formatdate("YYYYMMDDhhmmss", timestamp())
  # Random 6 character string for unique naming
  random_suffix = substr(sha256(local.timestamp), 0, 6)
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
  name         = "cloud.firestore-${local.random_suffix}"
  ruleset_name = google_firebaserules_ruleset.rules.name
  depends_on   = [google_firebaserules_ruleset.rules]
  
  lifecycle {
    create_before_destroy = true
  }
} 