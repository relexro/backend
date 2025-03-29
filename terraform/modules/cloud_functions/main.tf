# Create ZIP file of the functions source code
data "archive_file" "functions_source" {
  type        = "zip"
  source_dir  = var.functions_source_path
  output_path = var.functions_zip_path
}

# Upload the ZIP file to Cloud Storage
resource "google_storage_bucket_object" "functions_source" {
  name   = "functions-source-${data.archive_file.functions_source.output_md5}.zip"
  bucket = var.functions_bucket_name
  source = data.archive_file.functions_source.output_path
}

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
    },
    
    # Case Management Functions
    "relex-backend-create-case" = {
      entry_point = "cases_create_case",
      description = "Create a new case",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-get-case" = {
      entry_point = "cases_get_case",
      description = "Get a case by ID",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-list-cases" = {
      entry_point = "cases_list_cases",
      description = "List cases",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-archive-case" = {
      entry_point = "cases_archive_case",
      description = "Archive a case",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-delete-case" = {
      entry_point = "cases_delete_case",
      description = "Delete a case",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-upload-file" = {
      entry_point = "cases_upload_file",
      description = "Upload a file to a case",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-download-file" = {
      entry_point = "cases_download_file",
      description = "Download a file from a case",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-attach-party" = {
      entry_point = "cases_attach_party",
      description = "Attach a party to a case",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-detach-party" = {
      entry_point = "cases_detach_party",
      description = "Detach a party from a case",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    
    # Authentication Functions
    "relex-backend-validate-user" = {
      entry_point = "auth_validate_user",
      description = "Validate a user's token",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-check-permissions" = {
      entry_point = "auth_check_permissions",
      description = "Check permissions for a user",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-get-user-role" = {
      entry_point = "auth_get_user_role",
      description = "Get a user's role in an organization",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    
    # Party Management Functions
    "relex-backend-create-party" = {
      entry_point = "party_create_party",
      description = "Create a new party",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-get-party" = {
      entry_point = "party_get_party",
      description = "Get a party by ID",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-update-party" = {
      entry_point = "party_update_party",
      description = "Update a party",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-delete-party" = {
      entry_point = "party_delete_party",
      description = "Delete a party",
      max_instances = 10,
      memory = "256Mi",
      timeout = 60
    },
    "relex-backend-list-parties" = {
      entry_point = "party_list_parties",
      description = "List parties",
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

# Deploy each Cloud Function
resource "google_cloudfunctions2_function" "functions" {
  for_each = local.functions
  
  name        = each.key
  location    = var.region
  description = each.value.description

  build_config {
    runtime     = "python310"
    entry_point = each.value.entry_point
    source {
      storage_source {
        bucket = var.functions_bucket_name
        object = google_storage_bucket_object.functions_source.name
      }
    }
  }

  service_config {
    max_instance_count = lookup(each.value, "max_instances", 10)
    available_memory   = lookup(each.value, "memory", "256Mi")
    timeout_seconds    = lookup(each.value, "timeout", 60)
    
    environment_variables = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION = var.region
    }

    dynamic "secret_environment_variables" {
      for_each = lookup(each.value, "secret_env_vars", [])
      content {
        key        = secret_environment_variables.value.key
        project_id = var.project_id
        secret    = secret_environment_variables.value.secret
        version   = secret_environment_variables.value.version
      }
    }
  }

  depends_on = [google_storage_bucket_object.functions_source]
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
    create_before_destroy = true
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
  secret_data_wo = var.stripe_secret_key
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
  secret_data_wo = var.stripe_webhook_secret
} 