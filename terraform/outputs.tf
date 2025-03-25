output "files_bucket_url" {
  description = "The URL of the files storage bucket"
  value       = "gs://${google_storage_bucket.files_bucket.name}"
}

output "functions_bucket_url" {
  description = "The URL of the functions storage bucket"
  value       = "gs://${google_storage_bucket.functions_bucket.name}"
}

output "create_case_function_url" {
  description = "The URL of the create_case Cloud Function"
  value       = google_cloudfunctions2_function.create_case_function.url
}

output "get_case_function_url" {
  description = "The URL of the get_case Cloud Function"
  value       = google_cloudfunctions2_function.get_case_function.url
}

output "list_cases_function_url" {
  description = "The URL of the list_cases Cloud Function"
  value       = google_cloudfunctions2_function.list_cases_function.url
}

output "archive_case_function_url" {
  value = google_cloudfunctions2_function.archive_case_function.url
}

output "delete_case_function_url" {
  value = google_cloudfunctions2_function.delete_case_function.url
}

output "upload_file_function_url" {
  value = google_cloudfunctions2_function.upload_file_function.url
}

output "download_file_function_url" {
  value = google_cloudfunctions2_function.download_file_function.url
}

# Auth Functions URLs
output "validate_user_function_url" {
  value = google_cloudfunctions2_function.validate_user_function.url
}

output "check_permissions_function_url" {
  value = google_cloudfunctions2_function.check_permissions_function.url
}

output "get_user_role_function_url" {
  value = google_cloudfunctions2_function.get_user_role_function.url
}

# Business Functions URLs
output "create_business_function_url" {
  value = google_cloudfunctions2_function.create_business_function.url
}

output "get_business_function_url" {
  value = google_cloudfunctions2_function.get_business_function.url
}

output "add_business_user_function_url" {
  value = google_cloudfunctions2_function.add_business_user_function.url
}

output "set_user_role_function_url" {
  value = google_cloudfunctions2_function.set_user_role_function.url
}

# Chat Functions URLs
output "receive_prompt_function_url" {
  value = google_cloudfunctions2_function.receive_prompt_function.url
}

output "send_to_vertex_ai_function_url" {
  value = google_cloudfunctions2_function.send_to_vertex_ai_function.url
}

output "store_conversation_function_url" {
  value = google_cloudfunctions2_function.store_conversation_function.url
}

# Additional function URLs would be output similarly 