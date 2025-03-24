# Relex Backend

Backend for Relex, an AI-powered legal chat application built using Firebase Functions in Python and Terraform for infrastructure management.

## Project Structure

- `functions/src/`: Contains Python modules for Firebase Functions
  - `cases.py`: Case management functions
  - `chat.py`: Chat and AI interaction functions
  - `auth.py`: Authentication functions
  - `payments.py`: Payment processing functions
  - `business.py`: Business account management functions
  - `main.py`: Main entry point that imports and exports all functions

- `terraform/`: Contains Terraform configuration files
  - `main.tf`: Main Terraform configuration
  - `variables.tf`: Variable definitions
  - `outputs.tf`: Output definitions
  - `terraform.tfvars.example`: Example variable values

## Setup Instructions

### Prerequisites

- Firebase CLI
- Terraform
- Python 3.10 or higher
- Google Cloud SDK

### Configuration

1. Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars` and update the values.
2. Set up Google Cloud authentication:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
   ```

### Deployment

1. Initialize Terraform:
   ```bash
   cd terraform
   terraform init
   ```

2. Deploy the infrastructure:
   ```bash
   terraform apply
   ```

## Development

To run functions locally:

```bash
cd functions
pip install -r requirements.txt
functions-framework --target=cases_create_case
```

## Testing

Tests will be added in future updates. 