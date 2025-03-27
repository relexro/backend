variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "The region for resources deployment"
  type        = string
}

variable "functions_source_path" {
  description = "Path to the directory containing the Cloud Functions source code"
  type        = string
}

variable "functions_zip_name" {
  description = "Name of the zip file containing the Cloud Functions source code"
  type        = string
  default     = "functions-source.zip"
}

variable "functions_zip_path" {
  description = "Path to the zip file containing the Cloud Functions source code"
  type        = string
} 