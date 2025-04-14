variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "location" {
  description = "Google Cloud region for Discovery Engine resources"
  type        = string
  default     = "global"
}

variable "datastore_id_suffix" {
  description = "Suffix for the Data Store ID"
  type        = string
  default     = "main-rag-datastore"
}

variable "engine_id_suffix" {
  description = "Suffix for the Search Engine ID"
  type        = string
  default     = "main-rag-engine"
}

variable "search_tier" {
  description = "Search tier (SEARCH_TIER_STANDARD or SEARCH_TIER_ENTERPRISE)"
  type        = string
  default     = "SEARCH_TIER_STANDARD"
}

variable "search_add_ons" {
  description = "List of search add-ons (e.g., SEARCH_ADD_ON_LLM)"
  type        = list(string)
  default     = []
} 