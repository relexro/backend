variable "domain_name" {
  description = "The domain name managed by Cloudflare (e.g., relex.ro)"
  type        = string
}

variable "subdomain" {
  description = "The subdomain to create for the API Gateway (e.g., api)"
  type        = string
}

variable "gateway_hostname" {
  description = "The hostname of the API Gateway to point the CNAME record to"
  type        = string
}

variable "zone_id" {
  description = "Cloudflare Zone ID (if provided, will skip zone lookup)"
  type        = string
} 