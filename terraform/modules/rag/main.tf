# --- Vertex AI Search Data Store ---
resource "google_discovery_engine_data_store" "rag_datastore" {
  provider           = google-beta
  project           = var.project_id
  location          = var.location
  data_store_id     = "${split("-", var.project_id)[0]}-${var.datastore_id_suffix}"
  display_name      = "${title(split("-", var.project_id)[0])} Main RAG DataStore (Legislation/Jurisprudence - TXT)"
  industry_vertical = "GENERIC"
  solution_types    = ["SOLUTION_TYPE_SEARCH"]
  content_config    = "NO_CONTENT" # Ingesting unstructured TXT
  create_advanced_site_search = false
}

# --- Vertex AI Search Engine ---
resource "google_discovery_engine_search_engine" "rag_engine" {
  provider           = google-beta
  project           = var.project_id
  location          = google_discovery_engine_data_store.rag_datastore.location
  engine_id         = "${split("-", var.project_id)[0]}-${var.engine_id_suffix}"
  collection_id     = "default_collection"
  data_store_ids    = [google_discovery_engine_data_store.rag_datastore.data_store_id]
  display_name      = "${title(split("-", var.project_id)[0])} Main RAG Search Engine"

  common_config {
    company_name = title(split("-", var.project_id)[0])
  }
  search_engine_config {
    search_tier    = var.search_tier
    search_add_ons = var.search_add_ons
  }
}

# IMPORTANT: Data import into the datastore must be done manually via gcloud
# after these resources are created by Terraform. 