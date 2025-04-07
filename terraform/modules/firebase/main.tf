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

# We don't have permission to manage the default Firestore database through Terraform
# Instead, we'll just reference it by name for the rules
# Note: Point-in-time recovery and backups need to be configured manually

# Note: Automated backups need to be configured manually or through a different approach
# The current Terraform provider version doesn't support the backup schedule resource

# Apply the ruleset to the default Firestore database
resource "google_firebaserules_release" "default_firestore" {
  provider     = google-beta
  project      = var.project_id
  name         = "cloud.firestore/(default)"
  ruleset_name = google_firebaserules_ruleset.rules.name

  lifecycle {
    create_before_destroy = true
    # Prevent Terraform from failing if the resource already exists
    ignore_changes = all
  }

  depends_on = [google_firebase_project.default, google_firebaserules_ruleset.rules]
}