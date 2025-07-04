import pytest
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
import flask
import os
import json
from unittest.mock import MagicMock
import sys
import re
import stripe, uuid, time
from tests.helpers import stripe_test_helpers
import logging
from tests.helpers.create_test_user import ensure_firebase_user

# Add functions/src to the Python path if not already there
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../functions/src')))

# Check if FIRESTORE_EMULATOR_HOST is set, which indicates we're running against an emulator
def is_using_emulator():
    return os.environ.get("FIRESTORE_EMULATOR_HOST") is not None

@pytest.fixture(scope="session")
def initialize_firebase_for_tests():
    """Session-scoped fixture to initialize Firebase for tests.

    If FIRESTORE_EMULATOR_HOST environment variable is set, this fixture
    initializes Firebase Admin SDK with anonymous credentials to connect
    to the Firestore emulator.
    """
    try:
        # Check if Firebase Admin SDK is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Use anonymous credentials when connecting to the emulator
        if is_using_emulator():
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'projectId': 'demo-test',
            })
            print(f"Firebase initialized with emulator at {os.environ.get('FIRESTORE_EMULATOR_HOST')}")
        else:
            # Use application default credentials
            firebase_admin.initialize_app()
            print("Firebase initialized with application default credentials")

    yield

    # Cleanup code if needed at end of test session
    # Note: For emulator, we typically don't need to do cleanup since emulator data is ephemeral

@pytest.fixture
def firestore_emulator_client(initialize_firebase_for_tests):
    """Function-scoped fixture to provide a Firestore client connected to the emulator.

    This fixture also handles cleanup of known collections after each test.
    """
    # Ensure we're using the emulator
    if not is_using_emulator():
        pytest.skip("These tests require the Firestore emulator. Please set FIRESTORE_EMULATOR_HOST.")

    # Get a Firestore client
    db = firestore.client()
    yield db

    # Clean up the database after the test
    cleanup_collections(db)

def cleanup_collections(db):
    """Clean up known collections in the Firestore emulator."""
    collections_to_clean = [
        "users",
        "cases",
        "organizations",
        "organization_memberships",
        "documents",
        "payment_intents",
        "checkout_sessions"
    ]

    for collection_name in collections_to_clean:
        delete_collection(db, collection_name)

def delete_collection(db, collection_name, batch_size=50):
    """Delete all documents in a collection."""
    collection = db.collection(collection_name)
    docs = collection.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(db, collection_name, batch_size)

@pytest.fixture
def mock_request():
    """Create a mock Flask request object for testing.

    Returns:
        function: A function that creates a mock request with the specified parameters.
    """
    def _create_mock_request(headers=None, json_data=None, query_args=None, path=None):
        """Create a mock Flask request.

        Args:
            headers (dict, optional): Request headers. Defaults to None.
            json_data (dict, optional): JSON body data. Defaults to None.
            query_args (dict, optional): Query parameters. Defaults to None.
            path (str, optional): Request path. Defaults to None.

        Returns:
            MagicMock: A mock Flask request object.
        """
        mock_request = MagicMock(spec=flask.Request)

        # Set headers
        mock_request.headers = headers or {}

        # Set JSON data
        if json_data:
            mock_request.get_json = MagicMock(return_value=json_data)
        else:
            mock_request.get_json = MagicMock(return_value=None)

        # Set query args
        mock_request.args = query_args or {}

        # Set path
        mock_request.path = path or ''

        return mock_request

    return _create_mock_request

@pytest.fixture(scope="session")
def api_base_url():
    terraform_outputs_path = "docs/terraform_outputs.log"
    api_gateway_hostname = None
    base_url_to_return = None

    try:
        # Attempt to read from terraform_outputs.log
        if os.path.exists(terraform_outputs_path):
            with open(terraform_outputs_path, 'r') as f:
                for line in f:
                    if line.strip().startswith("api_gateway_url ="):
                        # Regex to capture the value within quotes
                        match = re.search(r'api_gateway_url\s*=\s*"([^"]+)"', line)
                        if match:
                            api_gateway_hostname = match.group(1)
                            break
            
            if api_gateway_hostname:
                base_url_to_return = f"https://{api_gateway_hostname}/v1"
                # This constructs the URL like: [https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/v1](https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/v1)
                # No rstrip('/') needed here as it's constructed without a trailing slash.
    except Exception as e:
        # Log error reading file but proceed to fallback
        print(f"\nWarning: Could not read API Gateway URL from {terraform_outputs_path}: {e}")
        # Ensure pytest prints this warning if it captures stdout/stderr.
        # Alternatively, use pytest.warn or similar if a more formal warning is desired.

    if base_url_to_return:
        return base_url_to_return

    # Fallback to environment variable if not found in file or file reading failed
    base_url_env = os.environ.get("RELEX_API_BASE_URL")
    if base_url_env:
        return base_url_env.rstrip('/') # Strip trailing slash if present from env var
    
    # If neither method yields a URL, skip the tests
    pytest.skip(
        f"API base URL could not be determined. "
        f"Checked '{terraform_outputs_path}' (or it was unreadable/key missing) "
        f"and the RELEX_API_BASE_URL environment variable is not set. "
        "Skipping integration tests."
    )

@pytest.fixture(scope="session")
def auth_token():
    """Get the standard authentication token for API requests.

    This fixture gets the token from the RELEX_TEST_JWT environment variable.
    If it's not available, it skips tests that require authentication.
    This token is for a regular user without organization membership.

    Returns:
        str: The authentication token.
    """
    token = os.environ.get("RELEX_TEST_JWT")
    if not token:
        pytest.skip("RELEX_TEST_JWT environment variable is not set. Skipping integration tests that require auth.")
    return token

@pytest.fixture(scope="session")
def org_admin_token():
    """Get the organization admin authentication token for API requests.

    This fixture gets the token from the RELEX_ORG_ADMIN_TEST_JWT environment variable.
    If it's not available, it skips tests that require organization admin authentication.
    This token is for a user with administrator role in an organization.

    Returns:
        str: The organization admin authentication token.
    """
    token = os.environ.get("RELEX_ORG_ADMIN_TEST_JWT")
    if not token:
        pytest.skip("RELEX_ORG_ADMIN_TEST_JWT environment variable is not set. Skipping integration tests that require org admin auth.")
    return token

@pytest.fixture(scope="session")
def org_user_token():
    """Get the organization user authentication token for API requests.

    This fixture gets the token from the RELEX_ORG_USER_TEST_JWT environment variable.
    If it's not available, it skips tests that require organization user authentication.
    This token is for a user with staff role in an organization.

    Returns:
        str: The organization user authentication token.
    """
    token = os.environ.get("RELEX_ORG_USER_TEST_JWT")
    if not token:
        pytest.skip("RELEX_ORG_USER_TEST_JWT environment variable is not set. Skipping integration tests that require org user auth.")
    return token

def create_api_client(api_base_url, token):
    """Create an API client for making HTTP requests to the API.

    This function creates a wrapper around requests.Session that:
    1. Sets the Authorization header with the provided token
    2. Provides convenience methods for making requests to the API
    3. Handles URL construction with the base URL
    4. Disables SSL verification for development environments

    Args:
        api_base_url: The base URL for the API.
        token: The authentication token.

    Returns:
        APIClient: A client for making HTTP requests to the API.
    """
    import requests
    import urllib3

    # Configure SSL verification
    # For tests, we'll use verify=True with a custom environment variable to override if needed
    verify_ssl = os.environ.get("RELEX_TEST_VERIFY_SSL", "true").lower() != "false"

    if not verify_ssl:
        # Only disable warnings if we're explicitly disabling verification
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})
    session.verify = verify_ssl

    class APIClient:
        def __init__(self, session, base_url):
            self.session = session
            self.base_url = base_url.rstrip('/') # Ensure no trailing slash on base_url

        def get(self, endpoint, **kwargs):
            """Make a GET request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users".
                **kwargs: Additional arguments to pass to requests.get.

            Returns:
                Response: The HTTP response.
            """
            # Ensure endpoint starts with a slash if not already present
            request_url = f"{self.base_url}/{endpoint.lstrip('/')}"
            return self.session.get(request_url, **kwargs)

        def post(self, endpoint, **kwargs):
            """Make a POST request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users".
                **kwargs: Additional arguments to pass to requests.post.

            Returns:
                Response: The HTTP response.
            """
            request_url = f"{self.base_url}/{endpoint.lstrip('/')}"
            return self.session.post(request_url, **kwargs)

        def put(self, endpoint, **kwargs):
            """Make a PUT request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users/123".
                **kwargs: Additional arguments to pass to requests.put.

            Returns:
                Response: The HTTP response.
            """
            request_url = f"{self.base_url}/{endpoint.lstrip('/')}"
            return self.session.put(request_url, **kwargs)

        def delete(self, endpoint, **kwargs):
            """Make a DELETE request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users/123".
                **kwargs: Additional arguments to pass to requests.delete.

            Returns:
                Response: The HTTP response.
            """
            request_url = f"{self.base_url}/{endpoint.lstrip('/')}"
            return self.session.delete(request_url, **kwargs)

        def patch(self, endpoint, **kwargs):
            """Make a PATCH request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users/123".
                **kwargs: Additional arguments to pass to requests.patch.

            Returns:
                Response: The HTTP response.
            """
            request_url = f"{self.base_url}/{endpoint.lstrip('/')}"
            return self.session.patch(request_url, **kwargs)

        def request(self, method, endpoint, **kwargs):
            """Make a request to the API with the specified method.

            Args:
                method: The HTTP method to use.
                endpoint: The endpoint to request.
                **kwargs: Additional arguments to pass to requests.request.

            Returns:
                Response: The HTTP response.
            """
            request_url = f"{self.base_url}/{endpoint.lstrip('/')}"
            return self.session.request(method, request_url, **kwargs)

    return APIClient(session, api_base_url)

@pytest.fixture(scope="session")
def api_client(api_base_url, auth_token):
    """Create an API client for making HTTP requests to the API using the standard user token.

    This fixture creates a client authenticated with the regular user token (RELEX_TEST_JWT).

    Args:
        api_base_url: The base URL for the API.
        auth_token: The standard authentication token.

    Returns:
        APIClient: A client for making HTTP requests to the API.
    """
    return create_api_client(api_base_url, auth_token)

@pytest.fixture(scope="session")
def org_admin_api_client(api_base_url, org_admin_token):
    """Create an API client for making HTTP requests to the API using the organization admin token.

    This fixture creates a client authenticated with the organization admin token (RELEX_ORG_ADMIN_TEST_JWT).

    Args:
        api_base_url: The base URL for the API.
        org_admin_token: The organization admin authentication token.

    Returns:
        APIClient: A client for making HTTP requests to the API.
    """
    return create_api_client(api_base_url, org_admin_token)

@pytest.fixture(scope="session")
def org_user_api_client(api_base_url, org_user_token):
    """Create an API client for making HTTP requests to the API using the organization user token.

    This fixture creates a client authenticated with the organization user token (RELEX_ORG_USER_TEST_JWT).

    Args:
        api_base_url: The base URL for the API.
        org_user_token: The organization user authentication token.

    Returns:
        APIClient: A client for making HTTP requests to the API.
    """
    return create_api_client(api_base_url, org_user_token)

# -------------------- Stripe Test Clock Fixtures --------------------
@pytest.fixture(scope="session")
def stripe_test_clock():
    """Session-scoped Stripe Test Clock.

    Requires STRIPE_API_KEY env var to be set; otherwise skips Stripe-dependent tests.
    """
    stripe_api_key = os.getenv("STRIPE_API_KEY")
    if not stripe_api_key:
        pytest.skip("STRIPE_API_KEY environment variable not set. Skipping Stripe Test Clock dependent tests.")
    stripe.api_key = stripe_api_key  # Ensure global API key is configured

    clock = stripe_test_helpers.create_test_clock()
    yield clock

    # Teardown – delete the test clock to keep Stripe dashboard clean
    try:
        stripe_test_helpers.delete_test_clock(clock.id)
    except Exception:
        pass


@pytest.fixture
def stripe_test_customer(stripe_test_clock):
    """Create a Stripe test customer attached to the session's test clock."""
    customer = stripe.Customer.create(
        description="Relex integration-test customer",
        email=f"it_{uuid.uuid4()}@example.com",
        test_clock=stripe_test_clock.id,
    )
    yield customer
    # Cleanup – delete customer
    try:
        stripe.Customer.delete(customer.id)
    except Exception:
        pass

# Path to the test organization ID file
TEST_ORG_ID_FILE = os.path.join(os.path.dirname(__file__), 'test_data/test_org_id.txt')

@pytest.fixture
def test_organization(api_client):
    """Create a test organization and clean it up after the test."""
    org_data = {
        "name": f"Test Organization {uuid.uuid4()}",
        "type": "legal_firm",
        "address": "123 Test Street, Test City",
        "phone": "123-456-7890",
        "email": "test@example.com"
    }
    response = api_client.post("/organizations", json=org_data)
    assert response.status_code == 201, f"Failed to create test organization: {response.text}"
    org_id = response.json()["organizationId"]
    logging.info(f"Created test organization with ID: {org_id}")
    os.makedirs(os.path.dirname(TEST_ORG_ID_FILE), exist_ok=True)
    with open(TEST_ORG_ID_FILE, "w") as f:
        f.write(org_id)
    yield org_id
    try:
        response = api_client.delete(f"/organizations/{org_id}")
        if response.status_code == 200:
            logging.info(f"Deleted test organization with ID: {org_id}")
        else:
            logging.warning(f"Failed to delete test organization: {response.text}")
    except Exception as e:
        logging.error(f"Error deleting test organization: {str(e)}")

@pytest.fixture
def test_user_id():
    """Ensure a test user exists in Firebase and return its UID."""
    uid = f"test-user-{uuid.uuid4()}"
    ensure_firebase_user(uid)
    return uid
