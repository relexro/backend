terraform {
  backend "gcs" {
    bucket = "tf-state-relex"
    prefix = "backend"
  }
}
