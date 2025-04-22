# Firebase Authentication Configuration
resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id

  lifecycle {
    # Prevent recreation of this core resource
    prevent_destroy = true
  }
}

resource "google_firebase_web_app" "default" {
  provider     = google-beta
  project      = var.project_id
  display_name = "Relex Web App"
  depends_on   = [google_firebase_project.default]

  lifecycle {
    # Prevent recreation of this core resource
    prevent_destroy = true
    # Ignore changes to non-critical fields
    ignore_changes = [
      display_name
    ]
  }
}

locals {
  firestore_rules = file("${path.module}/rules/firestore.rules")
  # Use current timestamp for uniqueness in resources
  timestamp = formatdate("YYYYMMDDhhmmss", timestamp())
  # Random suffix for unique naming
  random_suffix = substr(sha256(local.timestamp), 0, 6)
  # Create a stable hash based on the rules content
  rules_hash = substr(sha256(local.firestore_rules), 0, 8)
}

# Firestore Security Rules Deployment - with unique identifier in source comment
# This ensures a new ruleset is created whenever the rules content changes
resource "google_firebaserules_ruleset" "rules" {
  provider = google-beta
  project  = var.project_id
  source {
    files {
      # Add a unique content identifier comment to force a new resource
      # when the rules change, but use the same actual rules content
      content = <<-EOT
        // Generated ruleset version: ${local.rules_hash}
        ${local.firestore_rules}
      EOT
      name    = "firestore.rules"
    }
  }
  depends_on = [google_firebase_project.default]

  # Use create_before_destroy to ensure the new ruleset is created before
  # the release is updated to point to it
  lifecycle {
    create_before_destroy = true
  }
}

# Release the ruleset for Firestore
resource "google_firebaserules_release" "firestore" {
  provider     = google-beta
  project      = var.project_id
  name         = "cloud.firestore"
  ruleset_name = google_firebaserules_ruleset.rules.name
  depends_on   = [google_firebaserules_ruleset.rules]

  lifecycle {
    create_before_destroy = true
    # Ignore ruleset_name changes to prevent recreation when ruleset is updated
    ignore_changes = [
      ruleset_name,
    ]
  }
}

# Create the Firestore database with proper configuration
resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = "europe-west1"
  type        = "FIRESTORE_NATIVE"

  # Enable point-in-time recovery
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"

  # Enable automated backups
  app_engine_integration_mode = "ENABLED"

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_firebase_project.default]
}

# Apply the ruleset to the default Firestore database
resource "google_firebaserules_release" "default_firestore" {
  provider     = google-beta
  project      = var.project_id
  name         = "cloud.firestore/(default)"
  ruleset_name = google_firebaserules_ruleset.rules.name

  lifecycle {
    create_before_destroy = true
    # Ignore ruleset_name changes to prevent recreation when ruleset is updated
    ignore_changes = [
      ruleset_name,
    ]
  }

  depends_on = [google_firebase_project.default, google_firebaserules_ruleset.rules, google_firestore_database.default]
}