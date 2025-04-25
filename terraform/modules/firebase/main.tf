# We don't manage Firebase resources through Terraform anymore
# Instead, we just apply Firestore rules to the default database using Firebase CLI

locals {
  firestore_rules = file("${path.module}/rules/firestore.rules")
}

# Apply Firestore rules to the default database using Firebase CLI
resource "null_resource" "apply_firestore_rules" {
  # Trigger the provisioner whenever the rules file changes
  triggers = {
    # Use the hash of the rules file to detect changes
    rules_hash = sha256(local.firestore_rules)
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
}