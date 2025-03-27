output "files_bucket_name" {
  description = "Name of the files storage bucket"
  value       = google_storage_bucket.files_bucket.name
}

output "functions_bucket_name" {
  description = "Name of the functions storage bucket"
  value       = google_storage_bucket.functions_bucket.name
}

output "functions_source_zip_name" {
  description = "Name of the uploaded functions source ZIP file"
  value       = google_storage_bucket_object.functions_source_zip.name
}

output "files_bucket_url" {
  description = "URL of the files storage bucket"
  value       = "gs://${google_storage_bucket.files_bucket.name}"
}

output "functions_bucket_url" {
  description = "URL of the functions storage bucket"
  value       = "gs://${google_storage_bucket.functions_bucket.name}"
} 