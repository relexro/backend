variable "environment" {
  description = "The target environment (dev, stage, prod)"
  type        = string
}

variable "webhook_url" {
  description = "The URL for the Stripe webhook endpoint"
  type        = string
}
