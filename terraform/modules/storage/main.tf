# Create a zip file from the function source code
data "archive_file" "functions_source" {
  type        = "zip"
  source_dir  = var.functions_source_path
  output_path = var.functions_zip_path
}

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

# Upload the Cloud Functions source code to the bucket
resource "google_storage_bucket_object" "functions_source_zip" {
  name   = "relex-backend-functions-source-fixed.zip"
  bucket = google_storage_bucket.functions_bucket.name
  source = var.functions_zip_path

  # Define dependencies
  depends_on = [
    google_storage_bucket.functions_bucket
  ]
} 