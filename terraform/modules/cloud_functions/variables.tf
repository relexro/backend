variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "The region for resources deployment"
  type        = string
}

variable "functions_bucket_name" {
  description = "Name of the bucket for function source code"
  type        = string
}

variable "functions_source_path" {
  description = "Path to the directory containing the Cloud Functions source code"
  type        = string
}

variable "functions_zip_path" {
  description = "Path to the zip file containing the Cloud Functions source code"
  type        = string
}

variable "functions_zip_name" {
  description = "Name of the zip file containing the Cloud Functions source code"
  type        = string
}

variable "api_gateway_sa_email" {
  description = "Email of the API Gateway service account"
  type        = string
}

variable "functions" {
  description = "Map of Cloud Functions configurations"
  type = map(object({
    description = string
    entry_point = string
    env_vars    = map(string)
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
      env_vars    = {
        "STRIPE_SECRET_KEY" = "sk_test_51KGx9ySBqRYQv8xZY0PQnQkmQ2AwZsEZyHcLgjE8gMmL8GQbQYhIwzqnTCwGQ1zqOVlOZBHFGpPx"
      }
    },
    "relex-backend-create-checkout-session" = {
      description = "Create a Stripe checkout session"
      entry_point = "payments_create_checkout_session"
      env_vars    = {
        "STRIPE_SECRET_KEY" = "sk_test_51KGx9ySBqRYQv8xZY0PQnQkmQ2AwZsEZyHcLgjE8gMmL8GQbQYhIwzqnTCwGQ1zqOVlOZBHFGpPx"
      }
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
    }
  }
}

variable "stripe_secret_key" {
  description = "Stripe Secret API key"
  type        = string
  sensitive   = true
}

variable "stripe_webhook_secret" {
  description = "Stripe Webhook Secret for validating webhook events"
  type        = string
  sensitive   = true
} 