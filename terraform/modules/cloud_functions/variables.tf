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

variable "stripe_secret_key_name" {
  description = "The name (secret_id) of the Stripe secret key in Secret Manager."
  type        = string
}

variable "stripe_webhook_secret_name" {
  description = "The name (secret_id) of the Stripe webhook secret in Secret Manager."
  type        = string
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
  }))
  default = {
    "relex-backend-create-organization" = {
      description = "Create a new organization account"
      entry_point = "organization_create_organization"
      env_vars    = {}
    },
    "relex-backend-get-organization" = {
      description = "Get an organization account by ID"
      entry_point = "organization_get_organization"
      env_vars    = {}
    },
    "relex-backend-update-organization" = {
      description = "Update an organization account"
      entry_point = "organization_update_organization"
      env_vars    = {}
    },
    "relex-backend-add-organization-user" = {
      description = "Add a user to an organization account"
      entry_point = "organization_add_organization_user"
      env_vars    = {}
    },
    "relex-backend-remove-organization-user" = {
      description = "Remove a user from an organization"
      entry_point = "organization_remove_organization_user"
      env_vars    = {}
    },
    "relex-backend-list-organization-users" = {
      description = "List users in an organization"
      entry_point = "organization_list_organization_users"
      env_vars    = {}
    },
    "relex-backend-set-user-role" = {
      description = "Update a user's role in an organization"
      entry_point = "organization_set_user_role"
      env_vars    = {}
    },
    "relex-backend-get-user-profile" = {
      description = "Get user profile data for the authenticated user"
      entry_point = "users_get_user_profile"
      env_vars    = {}
    },
    "relex-backend-update-user-profile" = {
      description = "Update user profile data for the authenticated user"
      entry_point = "users_update_user_profile"
      env_vars    = {}
    },
    "relex-backend-receive-prompt" = {
      description = "Receive a prompt from a user"
      entry_point = "chat_receive_prompt"
      env_vars    = {}
    },
    "relex-backend-send-to-vertex-ai" = {
      description = "Send a prompt to Vertex AI"
      entry_point = "chat_send_to_vertex_ai"
      env_vars    = {}
    },
    "relex-backend-store-conversation" = {
      description = "Store a conversation"
      entry_point = "chat_store_conversation"
      env_vars    = {}
    },
    "relex-backend-enrich-prompt" = {
      description = "Enrich a prompt with case context"
      entry_point = "chat_enrich_prompt"
      env_vars    = {}
    },
    "relex-backend-create-payment-intent" = {
      description = "Create a Stripe payment intent"
      entry_point = "payments_create_payment_intent"
      env_vars    = {}
    },
    "relex-backend-create-checkout-session" = {
      description = "Create a Stripe checkout session"
      entry_point = "payments_create_checkout_session"
      env_vars    = {}
    },
    "relex-backend-add-organization-member" = {
      description = "Add a member to an organization"
      entry_point = "organization_membership_add_organization_member"
      env_vars    = {}
    },
    "relex-backend-remove-organization-member" = {
      description = "Remove a member from an organization"
      entry_point = "organization_membership_remove_organization_member"
      env_vars    = {}
    },
    "relex-backend-list-organization-members" = {
      description = "List members of an organization"
      entry_point = "organization_membership_list_organization_members"
      env_vars    = {}
    },
    "relex-backend-set-organization-member-role" = {
      description = "Set a member's role in an organization"
      entry_point = "organization_membership_set_organization_member_role"
      env_vars    = {}
    },
    "relex-backend-get-user-organization-role" = {
      description = "Get a user's role in an organization"
      entry_point = "organization_membership_get_user_organization_role"
      env_vars    = {}
    },
    "relex-backend-list-user-organizations" = {
      description = "List organizations a user belongs to"
      entry_point = "organization_membership_list_user_organizations"
      env_vars    = {}
    },
    "relex-backend-handle-stripe-webhook" = {
      description = "Handle Stripe webhook events"
      entry_point = "payments_handle_stripe_webhook"
      env_vars    = {}
    },
    "relex-backend-cancel-subscription" = {
      description = "Cancel a Stripe subscription"
      entry_point = "payments_cancel_subscription"
      env_vars    = {}
    },
    "relex-backend-create-case" = {
      description = "Create a new case"
      entry_point = "cases_create_case"
      env_vars    = {}
    },
    "relex-backend-get-case" = {
      description = "Get a case by ID"
      entry_point = "cases_get_case"
      env_vars    = {}
    },
    "relex-backend-list-cases" = {
      description = "List cases"
      entry_point = "cases_list_cases"
      env_vars    = {}
    },
    "relex-backend-archive-case" = {
      description = "Archive a case"
      entry_point = "cases_archive_case"
      env_vars    = {}
    },
    "relex-backend-delete-case" = {
      description = "Delete a case"
      entry_point = "cases_delete_case"
      env_vars    = {}
    },
    "relex-backend-upload-file" = {
      description = "Upload a file to a case"
      entry_point = "cases_upload_file"
      env_vars    = {}
    },
    "relex-backend-download-file" = {
      description = "Download a file from a case"
      entry_point = "cases_download_file"
      env_vars    = {}
    },
    "relex-backend-attach-party" = {
      description = "Attach a party to a case"
      entry_point = "cases_attach_party"
      env_vars    = {}
    },
    "relex-backend-detach-party" = {
      description = "Detach a party from a case"
      entry_point = "cases_detach_party"
      env_vars    = {}
    },
    "relex-backend-validate-user" = {
      description = "Validate a user's token"
      entry_point = "auth_validate_user"
      env_vars    = {}
    },
    "relex-backend-check-permissions" = {
      description = "Check permissions for a user"
      entry_point = "auth_check_permissions"
      env_vars    = {}
    },
    "relex-backend-get-user-role" = {
      description = "Get a user's role in an organization"
      entry_point = "auth_get_user_role"
      env_vars    = {}
    },
    "relex-backend-create-party" = {
      description = "Create a new party"
      entry_point = "party_create_party"
      env_vars    = {}
    },
    "relex-backend-get-party" = {
      description = "Get a party by ID"
      entry_point = "party_get_party"
      env_vars    = {}
    },
    "relex-backend-update-party" = {
      description = "Update a party"
      entry_point = "party_update_party"
      env_vars    = {}
    },
    "relex-backend-delete-party" = {
      description = "Delete a party"
      entry_point = "party_delete_party"
      env_vars    = {}
    },
    "relex-backend-list-parties" = {
      description = "List parties"
      entry_point = "party_list_parties"
      env_vars    = {}
    }
  }
} 