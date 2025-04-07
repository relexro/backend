variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
}

variable "firestore_location" {
  description = "The location for the Firestore database"
  type        = string
  default     = "europe-west1"
}