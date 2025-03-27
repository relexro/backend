# Define all cloud functions
locals {
  # Map of all functions to deploy with their configurations
  functions = {
    # Organization Functions
    "relex-backend-create-organization" = {
      entry_point = "organization_create_organization",
      description = "Create a new organization account",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-get-organization" = {
      entry_point = "organization_get_organization",
      description = "Get an organization account by ID",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-add-organization-user" = {
      entry_point = "organization_add_organization_user",
      description = "Add a user to an organization account",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-set-user-role" = {
      entry_point = "organization_set_user_role",
      description = "Update a user's role in an organization",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-update-organization" = {
      entry_point = "organization_update_organization",
      description = "Update an organization account",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-list-organization-users" = {
      entry_point = "organization_list_organization_users",
      description = "List users in an organization",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-remove-organization-user" = {
      entry_point = "organization_remove_organization_user",
      description = "Remove a user from an organization",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    
    # Organization Membership Functions
    "relex-backend-add-organization-member" = {
      entry_point = "organization_membership_add_organization_member",
      description = "Add a member to an organization",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-set-organization-member-role" = {
      entry_point = "organization_membership_set_organization_member_role",
      description = "Set a member's role in an organization",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-list-organization-members" = {
      entry_point = "organization_membership_list_organization_members",
      description = "List members of an organization",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-remove-organization-member" = {
      entry_point = "organization_membership_remove_organization_member",
      description = "Remove a member from an organization",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-get-user-organization-role" = {
      entry_point = "organization_membership_get_user_organization_role",
      description = "Get a user's role in an organization",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-list-user-organizations" = {
      entry_point = "organization_membership_list_user_organizations",
      description = "List organizations a user belongs to",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    
    # Chat Functions
    "relex-backend-receive-prompt" = {
      entry_point = "chat_receive_prompt",
      description = "Receive a prompt from a user",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-send-to-vertex-ai" = {
      entry_point = "chat_send_to_vertex_ai",
      description = "Send a prompt to Vertex AI",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-store-conversation" = {
      entry_point = "chat_store_conversation",
      description = "Store a conversation",
      max_instances = 10,
      memory = "256Mi", 
      timeout = 60
    },
    "relex-backend-enrich-prompt" = {
      entry_point = "chat_enrich_prompt",
      description = "Enrich a prompt with case context",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    
    # Payments Functions
    "relex-backend-create-payment-intent" = {
      entry_point = "payments_create_payment_intent",
      description = "Create a Stripe payment intent",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60,
      secret_env_vars = [
        {
          key = "STRIPE_SECRET_KEY",
          secret = "stripe-secret-key",
          version = "latest"
        }
      ]
    },
    "relex-backend-create-checkout-session" = {
      entry_point = "payments_create_checkout_session",
      description = "Create a Stripe checkout session",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60,
      secret_env_vars = [
        {
          key = "STRIPE_SECRET_KEY",
          secret = "stripe-secret-key",
          version = "latest"
        }
      ]
    },
    "relex-backend-handle-stripe-webhook" = {
      entry_point = "payments_handle_stripe_webhook",
      description = "Handle Stripe webhook events",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60,
      secret_env_vars = [
        {
          key = "STRIPE_SECRET_KEY",
          secret = "stripe-secret-key",
          version = "latest"
        },
        {
          key = "STRIPE_WEBHOOK_SECRET",
          secret = "stripe-webhook-secret",
          version = "latest"
        }
      ]
    },
    "relex-backend-cancel-subscription" = {
      entry_point = "payments_cancel_subscription",
      description = "Cancel a Stripe subscription",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60,
      secret_env_vars = [
        {
          key = "STRIPE_SECRET_KEY",
          secret = "stripe-secret-key",
          version = "latest"
        }
      ]
    },
    
    # User Functions
    "relex-backend-get-user-profile" = {
      entry_point = "users_get_user_profile",
      description = "Get user profile data for the authenticated user",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-update-user-profile" = {
      entry_point = "users_update_user_profile",
      description = "Update user profile data for the authenticated user",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    }
  }

  # Special case for Firebase Auth trigger function
  auth_trigger_function = {
    "relex-backend-create-user-profile" = {
      entry_point = "create_user_profile",
      description = "Create a user profile in Firestore when a new user signs up",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60,
      trigger = {
        event_type = "google.firebase.auth.user.v1.created",
        retry_policy = "RETRY_POLICY_RETRY"
      }
    }
  }
}

# Cloud Functions deployment using for_each to create multiple functions
resource "google_cloudfunctions2_function" "functions" {
  for_each    = var.functions
  name        = each.key
  location    = var.region
  description = each.value.description

  build_config {
    runtime     = "python310"
    entry_point = each.value.entry_point
    source {
      storage_source {
        bucket = var.functions_bucket_name
        object = "relex-backend-functions-source-fixed.zip"
      }
    }
  }

  service_config {
    max_instance_count             = 10
    available_memory               = "256Mi"
    timeout_seconds                = 120
    ingress_settings               = "ALLOW_INTERNAL_AND_GCLB"
    all_traffic_on_latest_revision = true
    service_account_email          = "relexro@appspot.gserviceaccount.com"
    environment_variables = merge({
      "GOOGLE_CLOUD_PROJECT" = var.project_id
      "GOOGLE_CLOUD_REGION"  = var.region
    }, each.value.env_vars != null ? each.value.env_vars : {})
    
    dynamic "secret_environment_variables" {
      for_each = each.value.secret_env_vars != null ? each.value.secret_env_vars : []
      content {
        key        = secret_environment_variables.value.key
        project_id = var.project_id
        secret     = secret_environment_variables.value.secret
        version    = secret_environment_variables.value.version
      }
    }
  }

  lifecycle {
    ignore_changes = [
      build_config.0.source.0.storage_source.0.generation,
      service_config.0.environment_variables,
      service_config.0.service,
      service_config.0.available_memory,
      service_config.0.timeout_seconds,
      service_config.0.max_instance_count,
      service_config.0.secret_environment_variables
    ]
    create_before_destroy = true
  }
}

# Add IAM policy to allow API Gateway to invoke the Cloud Functions
resource "google_cloud_run_service_iam_member" "invoker" {
  for_each = var.functions

  project  = var.project_id
  location = var.region
  service  = each.key
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.api_gateway_sa_email}"
  
  depends_on = [google_cloudfunctions2_function.functions]
  
  lifecycle {
    ignore_changes = [service]
  }
}

# Output the function URIs
output "function_uris" {
  description = "Map of function names to their URIs"
  value = {
    for name, function in google_cloudfunctions2_function.functions :
    name => function.url
  }
}

# Secret Manager resources for Stripe secrets
resource "google_secret_manager_secret" "stripe_secret_key" {
  secret_id = "stripe-secret-key"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "stripe_secret_key_version" {
  secret      = google_secret_manager_secret.stripe_secret_key.id
  secret_data = var.stripe_secret_key
}

resource "google_secret_manager_secret" "stripe_webhook_secret" {
  secret_id = "stripe-webhook-secret"
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "stripe_webhook_secret_version" {
  secret      = google_secret_manager_secret.stripe_webhook_secret.id
  secret_data = var.stripe_webhook_secret
} 