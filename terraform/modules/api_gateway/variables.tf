variable "project_id" {
  description = "The project ID to deploy to"
  type        = string
}

variable "region" {
  description = "The region to deploy to"
  type        = string
}

variable "openapi_spec_path" {
  description = "Path to the OpenAPI specification file"
  type        = string
}

variable "function_uris" {
  description = "Map of function names to their URIs"
  type        = map(string)
}

variable "api_gateway_sa_email" {
  description = "Email of the API Gateway service account"
  type        = string
}

variable "implemented_functions" {
  description = "List of function names that are actually implemented (to distinguish from planned/future functions in the API spec)"
  type        = list(string)
  default     = []
} 