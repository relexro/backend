output "api_fqdn" {
  description = "The fully qualified domain name for the API endpoint"
  value       = "${cloudflare_record.api_gateway_cname.name}.${var.domain_name}"
}

output "zone_id" {
  description = "The Cloudflare Zone ID for the domain"
  value       = local.zone_id
} 