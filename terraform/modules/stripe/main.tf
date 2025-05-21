# Stripe Resources for Relex

terraform {
  required_providers {
    stripe = {
      source  = "umisora/stripe"
      version = "~> 1.3.8"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.0"
    }
  }
}

# Verify provider connection
resource "null_resource" "verify_stripe_provider" {
  provisioner "local-exec" {
    command = "echo 'Stripe provider initialized for module'"
  }
}

# Stripe Products
resource "stripe_product" "relex_individual_case" {
  name                  = "Relex Individual Case"
  description           = "Purchase a single Relex AI legal case. Tier determines complexity and features."
  active                = true
  statement_descriptor  = "RELEX CASE"

  lifecycle {
    # Only ignore the ID to prevent recreation, but allow other attributes to be updated
    ignore_changes = [id]

    # Prevent destruction of the resource
    prevent_destroy = true
  }
}

resource "stripe_product" "relex_individual_plan" {
  name                  = "Relex Individual Plan"
  description           = "AI legal assistance for individual users. Includes case quotas and features."
  active                = true
  statement_descriptor  = "RELEX INDIVIDUAL"

  lifecycle {
    # Only ignore the ID to prevent recreation, but allow other attributes to be updated
    ignore_changes = [id]

    # Prevent destruction of the resource
    prevent_destroy = true
  }
}

resource "stripe_product" "relex_org_basic_plan" {
  name                  = "Relex Organization Basic Plan"
  description           = "AI legal assistance for small legal teams. Up to 5 members."
  active                = true
  statement_descriptor  = "RELEX ORG BASIC"

  lifecycle {
    # Only ignore the ID to prevent recreation, but allow other attributes to be updated
    ignore_changes = [id]

    # Prevent destruction of the resource
    prevent_destroy = true
  }
}

resource "stripe_product" "relex_org_pro_plan" {
  name                  = "Relex Organization Pro Plan"
  description           = "Advanced AI legal assistance for larger orgs. Up to 20 members."
  active                = true
  statement_descriptor  = "RELEX ORG PRO"

  lifecycle {
    # Only ignore the ID to prevent recreation, but allow other attributes to be updated
    ignore_changes = [id]

    # Prevent destruction of the resource
    prevent_destroy = true
  }
}

# Stripe Prices

# --- One-Time Case Prices ---
resource "stripe_price" "case_tier1_onetime" {
  product     = stripe_product.relex_individual_case.id
  active      = true
  currency    = "eur"
  unit_amount = 900 # €9.00
  nickname    = "Case Tier 1 Purchase (One-Time)"
  lookup_key  = "price_case_tier1_onetime"

  lifecycle {
    # Only ignore the lookup_key since it can't be changed after creation
    ignore_changes = [lookup_key]
  }
}

resource "stripe_price" "case_tier2_onetime" {
  product     = stripe_product.relex_individual_case.id
  active      = true
  currency    = "eur"
  unit_amount = 2900 # €29.00
  nickname    = "Case Tier 2 Purchase (One-Time)"
  lookup_key  = "price_case_tier2_onetime"

  lifecycle {
    # Only ignore the lookup_key since it can't be changed after creation
    ignore_changes = [lookup_key]
  }
}

resource "stripe_price" "case_tier3_onetime" {
  product     = stripe_product.relex_individual_case.id
  active      = true
  currency    = "eur"
  unit_amount = 9900 # €99.00
  nickname    = "Case Tier 3 Purchase (One-Time)"
  lookup_key  = "price_case_tier3_onetime"

  lifecycle {
    # Only ignore the lookup_key since it can't be changed after creation
    ignore_changes = [lookup_key]
  }
}

# --- Individual Subscription Prices ---
resource "stripe_price" "individual_monthly" {
  product     = stripe_product.relex_individual_plan.id
  active      = true
  currency    = "eur"
  unit_amount = 900 # €9.00
  recurring {
    interval = "month"
  }
  nickname    = "Individual Monthly"
  lookup_key  = "price_individual_monthly"

  lifecycle {
    # Only ignore the lookup_key since it can't be changed after creation
    # This allows you to update nickname, active status, and other attributes
    ignore_changes = [lookup_key]
  }
}

resource "stripe_price" "individual_yearly" {
  product     = stripe_product.relex_individual_plan.id
  active      = true
  currency    = "eur"
  unit_amount = 8640 # €86.40
  recurring {
    interval = "year"
  }
  nickname    = "Individual Annually (20% discount)"
  lookup_key  = "price_individual_yearly"

  lifecycle {
    # Only ignore the lookup_key since it can't be changed after creation
    # This allows you to update nickname, active status, and other attributes
    ignore_changes = [lookup_key]
  }
}

# --- Organization Basic Subscription Prices ---
resource "stripe_price" "org_basic_monthly" {
  product     = stripe_product.relex_org_basic_plan.id
  active      = true
  currency    = "eur"
  unit_amount = 20000 # €200.00
  recurring {
    interval = "month"
  }
  nickname    = "Organization Basic Monthly"
  lookup_key  = "price_org_basic_monthly"

  lifecycle {
    # Only ignore the lookup_key since it can't be changed after creation
    # This allows you to update nickname, active status, and other attributes
    ignore_changes = [lookup_key]
  }
}

resource "stripe_price" "org_basic_yearly" {
  product     = stripe_product.relex_org_basic_plan.id
  active      = true
  currency    = "eur"
  unit_amount = 192000 # €1920.00
  recurring {
    interval = "year"
  }
  nickname    = "Organization Basic Annually (20% discount)"
  lookup_key  = "price_org_basic_yearly"

  lifecycle {
    # Only ignore the lookup_key since it can't be changed after creation
    # This allows you to update nickname, active status, and other attributes
    ignore_changes = [lookup_key]
  }
}

# --- Organization Pro Subscription Prices ---
resource "stripe_price" "org_pro_monthly" {
  product     = stripe_product.relex_org_pro_plan.id
  active      = true
  currency    = "eur"
  unit_amount = 50000 # €500.00
  recurring {
    interval = "month"
  }
  nickname    = "Organization Pro Monthly"
  lookup_key  = "price_org_pro_monthly"

  lifecycle {
    # Only ignore the lookup_key since it can't be changed after creation
    # This allows you to update nickname, active status, and other attributes
    ignore_changes = [lookup_key]
  }
}

resource "stripe_price" "org_pro_yearly" {
  product     = stripe_product.relex_org_pro_plan.id
  active      = true
  currency    = "eur"
  unit_amount = 480000 # €4800.00
  recurring {
    interval = "year"
  }
  nickname    = "Organization Pro Annually (20% discount)"
  lookup_key  = "price_org_pro_yearly"

  lifecycle {
    # Only ignore the lookup_key since it can't be changed after creation
    # This allows you to update nickname, active status, and other attributes
    ignore_changes = [lookup_key]
  }
}

# Stripe Coupon & Promotion Code for Testing
resource "stripe_coupon" "test_coupon_25_off" {
  name        = "Test Coupon 25% Off First Month"
  percent_off = 25.0 # Stripe API expects float for percent_off
  duration    = "once"

  lifecycle {
    # Only ignore the ID to prevent recreation, but allow other attributes to be updated
    # This allows you to update name and other attributes
    ignore_changes = [id]
  }
}

resource "stripe_promotion_code" "test_promo_relex25" {
  coupon  = stripe_coupon.test_coupon_25_off.id
  code    = "RELEXTEST25"
  active  = true

  lifecycle {
    # Only ignore the code since it can't be changed after creation
    # This allows you to update active status and other attributes
    ignore_changes = [code]
  }
}

# Stripe Tax Rate for German VAT
resource "stripe_tax_rate" "german_vat_19" {
  display_name  = "VAT Germany 19%"
  description   = "Germany Value Added Tax - VAT ID DE368757784"
  jurisdiction  = "DE"
  percentage    = 19.0 # Stripe API expects float
  inclusive     = false
  active        = true

  lifecycle {
    # Only ignore the ID to prevent recreation, but allow other attributes to be updated
    # This allows you to update description, display_name, and active status
    ignore_changes = [id]
  }
}

# Stripe Webhook Endpoint
resource "stripe_webhook_endpoint" "relex_app_webhook" {
  url            = var.webhook_url
  enabled_events = [
    "checkout.session.completed",
    "invoice.payment_succeeded",
    "invoice.paid",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "payment_intent.canceled"
  ]
  description    = "Relex Application Webhook (${var.environment})"

  lifecycle {
    # Only ignore the ID and secret to prevent recreation, but allow other attributes to be updated
    # This allows you to update enabled_events and description
    ignore_changes = [id, secret]
  }
}

# Add a null resource to track webhook changes and force recreation when needed
resource "null_resource" "webhook_recreate_trigger" {
  # This will only be used when you want to force recreation of the webhook
  # To use it, change the value of this trigger
  triggers = {
    force_recreate = "1" # Change to "2", "3", etc. when you need to recreate
  }

  # Make this dependent on the webhook
  depends_on = [stripe_webhook_endpoint.relex_app_webhook]
}
