# Testing the list_user_organizations Function

This document provides instructions for testing the `list_user_organizations` function, which retrieves a list of organizations that a user belongs to.

## Test Description

The `test_list_user_organizations.py` script tests the `list_user_organizations` endpoint by:

1. Testing the response when a user doesn't belong to any organizations
2. Creating a test organization, adding the user as an administrator, and verifying that the organization appears in the response

## Prerequisites

Before running the tests, ensure you have:

1. Python 3.7+ installed
2. The following Python packages installed:
   - `firebase-admin`
   - `requests`
   - Access to the Firebase project (service account credentials set up)

## Setup

1. Install the required packages:
   ```bash
   cd tests
   pip install -r requirements-test.txt
   ```

2. Update the auth tokens:
   - Obtain fresh tokens using the `test-auth.html` utility:
     ```bash
     cd tests
     python3 -m http.server 8080
     # Open http://localhost:8080/test-auth.html in your browser
     # Sign in with the appropriate user accounts and copy the tokens
     ```
   - Set the environment variables:
     ```bash
     # For regular user tests
     export RELEX_TEST_JWT="your_regular_user_token_here"

     # For organization admin tests
     export RELEX_ORG_ADMIN_TEST_JWT="your_org_admin_token_here"

     # For organization user tests
     export RELEX_ORG_USER_TEST_JWT="your_org_user_token_here"
     ```

## Running the Test

Run the test with the following command:

```bash
cd tests
python -m integration.test_list_user_organizations
```

## Test Results

The test will output logs showing:
1. Whether it successfully connected to the endpoint
2. The response from the endpoint
3. Whether the response matches the expected output

A successful test will show "All tests passed successfully!" at the end.

## Troubleshooting

### Authentication Token Expired

If you see an "Unauthorized" response, your token might have expired. Get a new token from the `test-auth.html` utility and update the appropriate environment variable (`RELEX_TEST_JWT`, `RELEX_ORG_ADMIN_TEST_JWT`, or `RELEX_ORG_USER_TEST_JWT`) depending on which user role you're testing with.

### API Gateway URL

Make sure you're using the correct API Gateway URL. This URL can be found in `docs/terraform_outputs.log` under the `api_gateway_url` key. The custom domain `api-dev.relex.ro` is not currently the active endpoint for the API Gateway.

### Missing Organizations

If the test fails to find the created organization, check:
1. The Firestore database to ensure the organization was created correctly
2. The role assigned to the user in the organization
3. That you're using the correct user ID in the test

### API Endpoint Not Accessible

If the endpoint cannot be reached, verify:
1. The function has been deployed correctly
2. You're using the correct API Gateway URL from `docs/terraform_outputs.log`
3. Your network connection can reach the Google Cloud API Gateway endpoint
4. The authentication token is valid and properly set in the `RELEX_TEST_JWT` environment variable