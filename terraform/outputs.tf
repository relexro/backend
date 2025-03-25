output "files_bucket_url" {
  description = "The URL of the files storage bucket"
  value       = google_storage_bucket.files_bucket.url
}

output "functions_bucket_url" {
  description = "The URL of the functions storage bucket"
  value       = google_storage_bucket.functions_bucket.url
}

output "create_case_function_url" {
  description = "The URL of the create_case Cloud Function"
  value       = google_cloudfunctions2_function.create_case_function.service_config[0].uri
}

output "get_case_function_url" {
  description = "The URL of the get_case Cloud Function"
  value       = google_cloudfunctions2_function.get_case_function.service_config[0].uri
}

output "list_cases_function_url" {
  description = "The URL of the list_cases Cloud Function"
  value       = google_cloudfunctions2_function.list_cases_function.service_config[0].uri
}

# Additional function URLs would be output similarly 