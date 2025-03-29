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
resource "random_id" "ruleset_suffix" {
  byte_length = 4
  keepers = {
    # Generate a new ID when the rules file changes
    rules_hash = filemd5("${path.module}/rules/firestore.rules")
  }
}

resource "google_firebaserules_ruleset" "rules" {
  provider = google-beta
  project  = var.project_id
  
  source {
    files {
      # Use consistent naming without any suffix or variables
      name    = "firestore.rules" 
      content = file("${path.module}/rules/firestore.rules")
    }
  }
  
  # Ensure Firebase is fully initialized
  depends_on = [google_firebase_project.default]
  
  # Add lifecycle to prevent recreation unless content changes
  lifecycle {
    create_before_destroy = true
  }
}

# Release the ruleset for Firestore
resource "google_firebaserules_release" "firestore" {
  provider     = google-beta
  project      = var.project_id
  name         = "cloud.firestore"  # Must be cloud.firestore for Firestore rules
  ruleset_name = google_firebaserules_ruleset.rules.name
  depends_on   = [google_firebaserules_ruleset.rules]
  
  lifecycle {
    create_before_destroy = true
  }
} 