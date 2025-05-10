terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

# Get the zone ID for the domain - only used if zone_id is not provided
data "cloudflare_zone" "domain" {
  count = var.zone_id == "" ? 1 : 0
  name  = var.domain_name
}

locals {
  zone_id = var.zone_id != "" ? var.zone_id : try(data.cloudflare_zone.domain[0].id, "")
}

# Create CNAME record for API Gateway
resource "cloudflare_record" "api_gateway_cname" {
  zone_id = local.zone_id
  name    = var.subdomain
  content = var.gateway_hostname
  type    = "CNAME"
  proxied = true
  ttl     = 1  # Auto TTL for proxied record
}