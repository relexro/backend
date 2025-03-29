
variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
}

variable "relex_functions_service_account_email" {
  description = "The email address of the dedicated service account for Relex Cloud Functions."
  type        = string
}

variable "api_gateway_sa_email" {
  description = "The email address of the service account used by API Gateway."
  type        = string
}