variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "The Google Cloud region for resources."
  type        = string
}

variable "functions_source_path" {
  description = "The local path to the directory containing Cloud Functions source code."
  type        = string
  default     = "../functions/src" # Default relative path
}

variable "functions_zip_path" {
  description = "The temporary local path where the functions source code ZIP file will be created."
  type        = string
  default     = "/tmp/functions-source.zip"
}

variable "functions_bucket_name" {
  description = "The name of the GCS bucket used to store the functions source code ZIP."
  type        = string
}

variable "functions_service_account_email" {
  description = "The email address of the dedicated service account to run the functions as."
  type        = string
}

variable "api_gateway_sa_email" {
  description = "The email address of the service account used by API Gateway."
  type        = string
}


variable "environment" {
  description = "The target environment (dev, stage, prod)"
  type        = string
  default     = "dev"
}

variable "functions" {
  description = "Map of Cloud Functions configurations"
  type = map(object({
    description = string
    entry_point = string
    env_vars    = map(string)
    secret_env_vars = optional(list(object({
      key     = string
      secret  = string
      version = string
    })))
    timeout = optional(number)
    memory  = optional(string)
    max_instances = optional(number)
  }))
  default = {
    # Organization Functions
    "relex-backend-create-organization" = {
      description = "Create a new organization account"
      entry_point = "relex_backend_create_organization" # Corrected
      env_vars    = {}
    },
    "relex-backend-get-organization" = {
      description = "Get an organization account by ID"
      entry_point = "relex_backend_get_organization" # Corrected
      env_vars    = {}
    },
    "relex-backend-update-organization" = {
      description = "Update an organization account"
      entry_point = "relex_backend_update_organization" # Corrected
      env_vars    = {}
    },
    "relex-backend-delete-organization" = {
      description = "Delete an organization account"
      entry_point = "relex_backend_delete_organization" # Corrected
      env_vars    = {}
    },
    "relex-backend-add-organization-member" = {
      description = "Add a member to an organization account"
      entry_point = "relex_backend_add_organization_member" # Updated to use member naming
      env_vars    = {}
    },
    "relex-backend-remove-organization-member" = {
      description = "Remove a member from an organization"
      entry_point = "relex_backend_remove_organization_member" # Updated to use member naming
      env_vars    = {}
    },
    "relex-backend-list-organization-members" = {
      description = "List members in an organization"
      entry_point = "relex_backend_list_organization_members" # Updated to use member naming
      env_vars    = {}
    },
    "relex-backend-set-organization-member-role" = {
      description = "Update a member's role in an organization"
      entry_point = "relex_backend_set_organization_member_role" # Updated to use member naming
      env_vars    = {}
    },

    # User Profile Functions
    "relex-backend-get-user-profile" = {
      description = "Get user profile data for the authenticated user"
      entry_point = "relex_backend_get_user_profile" # Corrected
      env_vars    = {}
    },
    "relex-backend-update-user-profile" = {
      description = "Update user profile data for the authenticated user"
      entry_point = "relex_backend_update_user_profile" # Corrected
      env_vars    = {}
    },

    # Payment Functions
    "relex-backend-create-payment-intent" = {
      description = "Create a Stripe payment intent"
      entry_point = "relex_backend_create_payment_intent" # Matched main.py
      env_vars    = {}
      secret_env_vars = [
        {
          key     = "STRIPE_SECRET_KEY"
          secret  = "stripe-secret-key"
          version = "latest"
        }
      ]
    },
    "relex-backend-get-products" = {
      description = "Get active products and prices from Stripe"
      entry_point = "relex_backend_get_products"
      env_vars    = {}
      secret_env_vars = [
        {
          key     = "STRIPE_SECRET_KEY"
          secret  = "stripe-secret-key"
          version = "latest"
        }
      ]
    },
    "relex-backend-create-checkout-session" = {
      description = "Create a Stripe checkout session"
      entry_point = "relex_backend_create_checkout_session" # Matched main.py
      env_vars    = {}
      secret_env_vars = [
        {
          key     = "STRIPE_SECRET_KEY"
          secret  = "stripe-secret-key"
          version = "latest"
        }
      ]
    },
    "relex-backend-handle-stripe-webhook" = {
      description = "Handle Stripe webhook events"
      entry_point = "relex_backend_handle_stripe_webhook" # Matched main.py
      env_vars    = {}
      secret_env_vars = [
        {
          key     = "STRIPE_WEBHOOK_SECRET"
          secret  = "stripe-webhook-secret"
          version = "latest"
        }
      ]
    },
    "relex-backend-cancel-subscription" = {
      description = "Cancel a Stripe subscription"
      entry_point = "relex_backend_cancel_subscription" # Matched main.py
      env_vars    = {}
      secret_env_vars = [
        {
          key     = "STRIPE_SECRET_KEY"
          secret  = "stripe-secret-key"
          version = "latest"
        }
      ]
    },

    # Organization Membership Functions
    "relex-backend-get-user-organization-role" = {
      description = "Get a user's role in an organization"
      entry_point = "relex_backend_get_user_organization_role" # Corrected
      env_vars    = {}
    },
    "relex-backend-list-user-organizations" = {
      description = "List organizations a user belongs to"
      entry_point = "relex_backend_list_user_organizations" # Corrected
      env_vars    = {}
    },

    # Case Functions
    "relex-backend-create-case" = {
      description = "Create a new case"
      entry_point = "relex_backend_create_case" # Corrected
      env_vars    = {}
    },
    "relex-backend-get-case" = {
      description = "Get a case by ID"
      entry_point = "relex_backend_get_case" # Corrected
      env_vars    = {}
    },
    "relex-backend-list-cases" = {
      description = "List cases"
      entry_point = "relex_backend_list_cases" # Corrected
      env_vars    = {}
    },
    "relex-backend-archive-case" = {
      description = "Archive a case"
      entry_point = "relex_backend_archive_case" # Corrected
      env_vars    = {}
    },
    "relex-backend-delete-case" = {
      description = "Delete a case"
      entry_point = "relex_backend_delete_case" # Corrected
      env_vars    = {}
    },
    "relex-backend-upload-file" = {
      description = "Upload a file to a case"
      entry_point = "relex_backend_upload_file" # Corrected
      env_vars    = {}
    },
    "relex-backend-download-file" = {
      description = "Download a file from a case"
      entry_point = "relex_backend_download_file" # Corrected
      env_vars    = {}
    },
    "relex-backend-attach-party" = {
      description = "Attach a party to a case"
      entry_point = "relex_backend_attach_party" # Corrected
      env_vars    = {}
    },
    "relex-backend-detach-party" = {
      description = "Detach a party from a case"
      entry_point = "relex_backend_detach_party" # Corrected
      env_vars    = {}
    },

    # Auth Functions (Mapped to existing Python functions)
    "relex-backend-validate-user" = {
      description = "Validate a user's token"
      entry_point = "relex_backend_validate_user" # Corrected
      env_vars    = {}
    },
    "relex-backend-check-permissions" = {
      description = "Check permissions for a user"
      entry_point = "relex_backend_check_permissions" # Corrected
      env_vars    = {}
    },
    "relex-backend-get-user-role" = { # Note: Might conflict with org membership role? Check usage.
      description = "Get a user's role" # Simplified description
      entry_point = "relex_backend_get_user_role" # Corrected
      env_vars    = {}
    },

    # Party Functions
    "relex-backend-create-party" = {
      description = "Create a new party"
      entry_point = "relex_backend_create_party" # Corrected
      env_vars    = {}
    },
    "relex-backend-get-party" = {
      description = "Get a party by ID"
      entry_point = "relex_backend_get_party" # Corrected
      env_vars    = {}
    },
    "relex-backend-update-party" = {
      description = "Update a party"
      entry_point = "relex_backend_update_party" # Corrected
      env_vars    = {}
    },
    "relex-backend-delete-party" = {
      description = "Delete a party"
      entry_point = "relex_backend_delete_party" # Corrected
      env_vars    = {}
    },
    "relex-backend-list-parties" = {
      description = "List parties"
      entry_point = "relex_backend_list_parties" # Corrected
      env_vars    = {}
    },

    # List Organization Cases Function
     "relex-backend-list-organization-cases" = {
       description = "List organization cases"
       entry_point = "relex_backend_list_organization_cases" # Matched main.py
       env_vars    = {}
     },

    # Planned Functions (not yet implemented in main.py)
    "relex-backend-redeem-voucher" = {
      description = "Redeem a voucher code (planned)"
      entry_point = "relex_backend_redeem_voucher" # Will be implemented in future
      env_vars    = {}
    },
    "relex-backend-assign-case" = {
      description = "Assign a case to a staff member (planned)"
      entry_point = "relex_backend_assign_case" # Will be implemented in future
      env_vars    = {}
    },
    "relex-backend-agent-handler" = {
      description = "Lawyer AI Agent handler"
      entry_point = "relex_backend_agent_handler"
      env_vars = {
        VERTEX_AI_LOCATION = "global"
      }
      secret_env_vars = [
        {
          key     = "GEMINI_API_KEY"
          secret  = "gemini-api-key"
          version = "latest"
        },
        {
          key     = "GROK_API_KEY"
          secret  = "grok-api-key"
          version = "latest"
        }
      ]
      timeout = 300  # 5 minutes
      memory  = "512Mi"
      max_instances = 10
    }


  }
}
