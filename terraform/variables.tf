variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
  default     = "relexro"
}

variable "region" {
  description = "The region for resources deployment"
  type        = string
  default     = "europe-west3"
}

variable "firestore_location" {
  description = "The location for Firestore database"
  type        = string
  default     = "europe-west3"
}

variable "function_names" {
  description = "Names of the Firebase Functions to deploy"
  type        = list(string)
  default     = ["cases", "chat", "auth", "payments", "business"]
}

variable "bucket_names" {
  description = "Names of the Cloud Storage buckets to create"
  type        = map(string)
  default     = {
    "files"     = "files"
    "functions" = "functions"
  }
} 