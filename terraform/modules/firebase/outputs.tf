output "firebase_web_app_name" {
  value = google_firebase_web_app.default.name
}

output "firebase_web_app_id" {
  value = google_firebase_web_app.default.app_id
  sensitive = true
}

output "firestore_security_rules" {
  value = google_firebaserules_ruleset.rules.id
  description = "ID of the deployed Firestore security rules"
}

# We no longer use google_firebaserules_release.firestore resource
# Instead, we use the null_resource.apply_firestore_rules to apply rules directly

output "default_firestore_database" {
  value = local.default_database_name
  description = "Name of the default Firestore database (managed manually, not by Terraform)"
}

output "default_firestore_rules_applied" {
  value       = null_resource.apply_firestore_rules.id
  description = "ID of the null_resource that applied Firestore rules to the default database"
}