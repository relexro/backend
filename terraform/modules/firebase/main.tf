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

# NOTE: We no longer use google_firebaserules_release.firestore resource
# Instead, we use the null_resource.apply_firestore_rules to apply rules directly
# This avoids issues with Terraform trying to manage Firestore releases

# We don't have permission to manage the default Firestore database through Terraform
# Instead, we'll just reference it by name for the rules
# Note: Point-in-time recovery and backups need to be configured manually

# Note: Automated backups need to be configured manually or through a different approach
# The current Terraform provider version doesn't support the backup schedule resource

# Define a local variable for the default database name
# We don't try to manage the default database, only reference it by name
locals {
  default_database_name = "(default)"
}

# Apply Firestore rules to the default database using gcloud CLI
# This avoids issues with Terraform trying to manage the default database directly
resource "null_resource" "apply_firestore_rules" {
  # Trigger the provisioner whenever the ruleset changes
  triggers = {
    ruleset_id = google_firebaserules_ruleset.rules.id
  }

  # Use local-exec provisioner to apply the rules directly
  provisioner "local-exec" {
    command = <<-EOT
      echo "Applying Firestore rules to the default database..."
      # Create a temporary firebase.json file
      TEMP_DIR=$(mktemp -d)
      RULES_FILE="$(pwd)/modules/firebase/rules/firestore.rules"
      TEMP_FIREBASE_JSON="$TEMP_DIR/firebase.json"

      cat > "$TEMP_FIREBASE_JSON" << EOF
      {
        "firestore": {
          "rules": "$RULES_FILE"
        }
      }
      EOF

      # Apply the rules using Firebase CLI
      firebase deploy --only firestore:rules --project ${var.project_id} --config "$TEMP_FIREBASE_JSON"

      # Clean up temporary files
      rm -rf "$TEMP_DIR"
    EOT
  }

  depends_on = [
    google_firebase_project.default,
    google_firebaserules_ruleset.rules
  ]
}