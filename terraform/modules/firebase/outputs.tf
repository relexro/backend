output "firebase_web_app_name" {
  value = google_firebase_web_app.default.name
}

output "firebase_web_app_id" {
  value = google_firebase_web_app.default.app_id
  sensitive = true
} 