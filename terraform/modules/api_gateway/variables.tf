variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "The region where resources will be created"
  type        = string
  default     = "europe-west1"
}

variable "openapi_spec_path" {
  description = "Path to the OpenAPI specification file"
  type        = string
}

variable "function_uris" {
  description = "Map of function names to their URIs"
  type        = map(string)
} 