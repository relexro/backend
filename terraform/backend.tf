terraform {
  backend "gcs" {
    bucket = "tf-state-relex"
    prefix = "terraform/state"
  }
}

data "google_project" "current" {} 