Project Blueprint: Relex Backend (Firebase Functions Python, Terraform)

Objective: Generate the basic project structure for the Relex Backend application using Firebase Functions in Python and Terraform for deployment.

Instructions:

1.  Initialize a Firebase project (if not already done) and set up Firebase Functions.
2.  Create a Python Firebase Functions project structure.
3.  Create the following Python modules (files) in the `functions/src` directory:
    *   `cases.py`: For case management functions.
    *   `chat.py`: For chat functions.
    *   `auth.py`: For authentication functions (placeholder for now).
    *   `payments.py`: For payment functions.
    *   `business.py`: For business account functions.
    *   `main.py`: Main entry point to import and export functions from modules.
4.  In each module (`cases.py`, `chat.py`, etc.), create placeholder functions (e.g., `def create_case(request): pass`) for each function described in the Backend Context.md, and export them in `main.py`.  Just create function stubs for now.
5.  Initialize Terraform in the `relex-backend` root directory.
6.  Create Terraform configuration files (`main.tf`, `variables.tf`, `outputs.tf`) for:
    *   Provisioning Firebase Functions (using `google_cloud_functions_v2_function` resource).
    *   Setting up Firebase Firestore (using `google_firestore_database` resource).
    *   Setting up Firebase Cloud Storage (using `google_storage_bucket` resource).
    *   Configuring IAM roles for Firebase Functions to access Firestore and Cloud Storage (using `google_project_iam_member` or `google_project_iam_policy` resources).
    *   Using `GOOGLE_APPLICATION_CREDENTIALS` for authentication.
7.  Define variables in `variables.tf` for project ID, region, function names, bucket names, etc.
8.  Output function URLs and other relevant information in `outputs.tf`.

Output: Firebase Functions Python project structure, basic Python modules with function stubs, Terraform configuration files for deploying Firebase infrastructure.