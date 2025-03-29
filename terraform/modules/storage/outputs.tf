output "files_bucket_name" {
  description = "Name of the files storage bucket"
  value       = google_storage_bucket.files_bucket.name
}

output "functions_bucket_name" {
  description = "Name of the functions storage bucket"
  value       = google_storage_bucket.functions_bucket.name
}

output "files_bucket_url" {
  description = "URL of the files storage bucket"
  value       = "gs://${google_storage_bucket.files_bucket.name}"
}

output "functions_bucket_url" {
  description = "URL of the functions storage bucket"
  value       = "gs://${google_storage_bucket.functions_bucket.name}"
} 