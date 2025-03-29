output "firebase_web_app_name" {
  value = google_firebase_web_app.default.name
}

output "firebase_web_app_id" {
  value = google_firebase_web_app.default.app_id
  sensitive = true
}

output "firestore_security_rules" {
  value = google_firestore_security_rule.rules.id
  description = "ID of the deployed Firestore security rules"
} 