output "datastore_id" {
  description = "The full ID of the created Data Store"
  value       = google_discovery_engine_data_store.rag_datastore.data_store_id
}

output "engine_id" {
  description = "The full ID of the created Search Engine"
  value       = google_discovery_engine_search_engine.rag_engine.engine_id
}

output "engine_serving_config_path" {
  description = "The full resource path for the default serving config of the engine"
  value       = "projects/${var.project_id}/locations/${google_discovery_engine_search_engine.rag_engine.location}/collections/default_collection/engines/${google_discovery_engine_search_engine.rag_engine.engine_id}/servingConfigs/default_config"
  # Note: Constructing this path assumes default serving config. Adjust if needed.
} 