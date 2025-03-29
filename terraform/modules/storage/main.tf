# Storage bucket for files
resource "google_storage_bucket" "files_bucket" {
  name          = "${var.project_id}-files"
  location      = upper(var.region)
  storage_class = "STANDARD"
  force_destroy = false

  uniform_bucket_level_access = true

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  lifecycle {
    ignore_changes  = [name, cors, location]
  }
}

# Storage bucket for Cloud Functions source code
resource "google_storage_bucket" "functions_bucket" {
  name          = "${var.project_id}-functions"
  location      = upper(var.region)
  storage_class = "STANDARD"
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle {
    ignore_changes  = [name, location]
  }
} 