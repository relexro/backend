output "product_ids" {
  description = "IDs of created Stripe products."
  value = {
    relex_individual_case = stripe_product.relex_individual_case.id
    relex_individual_plan = stripe_product.relex_individual_plan.id
    relex_org_basic_plan  = stripe_product.relex_org_basic_plan.id
    relex_org_pro_plan    = stripe_product.relex_org_pro_plan.id
  }
}

output "price_lookup_keys" {
  description = "User-defined lookup keys for created Stripe prices."
  value = {
    case_tier1_onetime   = stripe_price.case_tier1_onetime.lookup_key
    case_tier2_onetime   = stripe_price.case_tier2_onetime.lookup_key
    case_tier3_onetime   = stripe_price.case_tier3_onetime.lookup_key
    individual_monthly   = stripe_price.individual_monthly.lookup_key
    individual_yearly    = stripe_price.individual_yearly.lookup_key
    org_basic_monthly    = stripe_price.org_basic_monthly.lookup_key
    org_basic_yearly     = stripe_price.org_basic_yearly.lookup_key
    org_pro_monthly      = stripe_price.org_pro_monthly.lookup_key
    org_pro_yearly       = stripe_price.org_pro_yearly.lookup_key
  }
}

output "price_actual_ids" {
  description = "Actual Stripe-generated Price IDs."
  value = {
    case_tier1_onetime   = stripe_price.case_tier1_onetime.id
    case_tier2_onetime   = stripe_price.case_tier2_onetime.id
    case_tier3_onetime   = stripe_price.case_tier3_onetime.id
    individual_monthly   = stripe_price.individual_monthly.id
    individual_yearly    = stripe_price.individual_yearly.id
    org_basic_monthly    = stripe_price.org_basic_monthly.id
    org_basic_yearly     = stripe_price.org_basic_yearly.id
    org_pro_monthly      = stripe_price.org_pro_monthly.id
    org_pro_yearly       = stripe_price.org_pro_yearly.id
  }
}

output "test_coupon_id" {
  description = "ID of the test coupon."
  value       = stripe_coupon.test_coupon_25_off.id
}

output "test_promotion_code_string" {
  description = "The test promotion code string."
  value       = stripe_promotion_code.test_promo_relex25.code
}

output "test_promotion_code_id" {
  description = "ID of the test promotion code resource."
  value       = stripe_promotion_code.test_promo_relex25.id
}

output "german_vat_tax_rate_id" {
  description = "ID of the German VAT 19% tax rate."
  value       = stripe_tax_rate.german_vat_19.id
}

output "webhook_endpoint_id" {
  description = "ID of the created Stripe webhook endpoint."
  value       = stripe_webhook_endpoint.relex_app_webhook.id
}

output "webhook_endpoint_secret" {
  description = "Secret for the Stripe webhook endpoint. THIS IS SENSITIVE and needed for webhook validation."
  value       = stripe_webhook_endpoint.relex_app_webhook.secret
  sensitive   = true
}
