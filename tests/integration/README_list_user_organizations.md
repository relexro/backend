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

2. Update the auth token in `test_list_user_organizations.py`:
   - Open the test file and replace the token in the `get_auth_token()` function with a fresh token
   - You can obtain a fresh token by using the `test-auth.html` utility

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

If you see an "Unauthorized" response, your token might have expired. Get a new token from the `test-auth.html` utility and update the `get_auth_token()` function.

### Missing Organizations

If the test fails to find the created organization, check:
1. The Firestore database to ensure the organization was created correctly
2. The role assigned to the user in the organization
3. That you're using the correct user ID in the test

### API Endpoint Not Accessible

If the endpoint cannot be reached, verify:
1. The function has been deployed correctly
2. The URL in the test script is correct
3. Your network connection can reach the Google Cloud Functions endpoint 