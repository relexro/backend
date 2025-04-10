# Create a bucket for storing Cloud Functions source code
resource "google_storage_bucket" "functions_bucket" {
  name                        = "${var.project_id}-functions"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  force_destroy              = true

  versioning {
    enabled = true
  }
  
  lifecycle {
    prevent_destroy = true
    # Prevent recreation when only metadata changes
    ignore_changes = [
      labels
    ]
  }
}

# Create a bucket for storing uploaded files
resource "google_storage_bucket" "files_bucket" {
  name                        = "${var.project_id}-files"
  location                    = var.region
  project                     = var.project_id
  uniform_bucket_level_access = true
  force_destroy              = true

  versioning {
    enabled = true
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  lifecycle {
    prevent_destroy = true
    # Prevent recreation when only metadata changes
    ignore_changes = [
      labels
    ]
  }
} 