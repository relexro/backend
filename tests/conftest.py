import pytest
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
import flask
import os
import json
from unittest.mock import MagicMock
import sys

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

@pytest.fixture
def mock_auth(mocker):
    """Mock the auth.get_authenticated_user function.

    Args:
        mocker: The pytest-mock fixture.

    Returns:
        function: A function that configures the mock to return the specified user.
    """
    def _mock_auth(user_id=None, email=None, status_code=200, error_message=None):
        """Configure the mock to return the specified user.

        Args:
            user_id (str, optional): User ID. If None, simulates unauthenticated.
            email (str, optional): User email.
            status_code (int, optional): Status code to return. Defaults to 200.
            error_message (str, optional): Error message to return. Defaults to None.

        Returns:
            MagicMock: The configured mock.
        """
        from functions.src import auth

        if user_id:
            user_data = {"userId": user_id}
            if email:
                user_data["email"] = email
            mock_return_value = (user_data, status_code, error_message)
        else:
            mock_return_value = (None, status_code or 401, error_message or "Unauthorized")

        mock_auth = mocker.patch('functions.src.auth.get_authenticated_user')
        mock_auth.return_value = mock_return_value
        return mock_auth

    return _mock_auth

@pytest.fixture
def mock_auth_module(mocker):
    """Create a mock auth module for testing.

    This fixture creates a mock for the local auth module that's imported
    directly in various source files using 'import auth' or 'from auth import ...'

    Args:
        mocker: The pytest-mock fixture.

    Returns:
        MagicMock: A mock of the auth module with key functions mocked.
    """
    # Create a mock for the entire auth module
    mock_module = MagicMock()

    # Mock get_authenticated_user function
    mock_get_authenticated_user = MagicMock()
    mock_get_authenticated_user.return_value = ({"userId": "test_user_id"}, 200, None)
    mock_module.get_authenticated_user = mock_get_authenticated_user

    # Mock check_permissions function
    mock_check_permissions = MagicMock()
    mock_check_permissions.return_value = ({"allowed": True}, 200)
    mock_module.check_permissions = mock_check_permissions

    # Apply the mock to all places that import the auth module
    if hasattr(sys, 'modules'):
        sys.modules['auth'] = mock_module

    # Add a patch for the auth module in functions.src
    mocker.patch('functions.src.auth', mock_module)
    mocker.patch('functions.src.cases.auth', mock_module)
    mocker.patch('functions.src.user.auth', mock_module)
    mocker.patch('functions.src.organization_membership.auth', mock_module)
    mocker.patch('functions.src.payments.auth', mock_module)

    # Also patch the direct imports
    mocker.patch('functions.src.cases.get_authenticated_user', mock_get_authenticated_user)
    mocker.patch('functions.src.user.auth.get_authenticated_user', mock_get_authenticated_user)
    mocker.patch('functions.src.organization_membership.auth.get_authenticated_user', mock_get_authenticated_user)
    mocker.patch('functions.src.payments.auth.get_authenticated_user', mock_get_authenticated_user)

    # Return the mock for further customization in tests if needed
    return mock_module

@pytest.fixture(scope="session")
def api_base_url():
    """Return the base URL for the API.

    This URL is derived from docs/terraform_outputs.log and is used for integration tests.
    Uses the API Gateway URL with the /v1 base path as specified in the OpenAPI specification.

    Returns:
        str: The base URL for the API.
    """
    # The API is deployed as a set of Cloud Run services behind an API Gateway
    # The API Gateway URL is in the format: https://{api_gateway_url}/v1
    return "https://relex-api-gateway-mvef5dk.ew.gateway.dev/v1"

@pytest.fixture(scope="session")
def auth_token():
    """Get the authentication token for API requests.

    This fixture tries to get the token from:
    1. The API_AUTH_TOKEN environment variable
    2. The tests/temp_api_token.txt file

    If neither is available, it skips tests that require authentication.

    Returns:
        str: The authentication token.
    """
    token = os.environ.get("API_AUTH_TOKEN")
    if not token:
        # Fallback for local testing: try to read from a file
        try:
            with open("tests/temp_api_token.txt", "r") as f:
                token = f.read().strip()
        except FileNotFoundError:
            pytest.skip("API_AUTH_TOKEN environment variable not set or tests/temp_api_token.txt not found. Skipping integration tests that require auth.")
    return token

@pytest.fixture(scope="session")
def api_client(api_base_url, auth_token):
    """Create an API client for making HTTP requests to the API.

    This fixture creates a wrapper around requests.Session that:
    1. Sets the Authorization header with the auth token
    2. Provides convenience methods for making requests to the API
    3. Handles URL construction with the base URL
    4. Disables SSL verification for development environments

    Args:
        api_base_url: The base URL for the API.
        auth_token: The authentication token.

    Returns:
        APIClient: A client for making HTTP requests to the API.
    """
    import requests
    import urllib3

    # Disable SSL verification warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {auth_token}"})
    # Disable SSL verification for development environments
    session.verify = False

    class APIClient:
        def __init__(self, session, base_url):
            self.session = session
            self.base_url = base_url

        def get(self, endpoint, **kwargs):
            """Make a GET request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users".
                **kwargs: Additional arguments to pass to requests.get.

            Returns:
                Response: The HTTP response.
            """
            return self.session.get(f"{self.base_url}{endpoint}", **kwargs)

        def post(self, endpoint, **kwargs):
            """Make a POST request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users".
                **kwargs: Additional arguments to pass to requests.post.

            Returns:
                Response: The HTTP response.
            """
            return self.session.post(f"{self.base_url}{endpoint}", **kwargs)

        def put(self, endpoint, **kwargs):
            """Make a PUT request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users/123".
                **kwargs: Additional arguments to pass to requests.put.

            Returns:
                Response: The HTTP response.
            """
            return self.session.put(f"{self.base_url}{endpoint}", **kwargs)

        def delete(self, endpoint, **kwargs):
            """Make a DELETE request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users/123".
                **kwargs: Additional arguments to pass to requests.delete.

            Returns:
                Response: The HTTP response.
            """
            return self.session.delete(f"{self.base_url}{endpoint}", **kwargs)

        def patch(self, endpoint, **kwargs):
            """Make a PATCH request to the API.

            Args:
                endpoint: The endpoint to request, e.g., "/users/123".
                **kwargs: Additional arguments to pass to requests.patch.

            Returns:
                Response: The HTTP response.
            """
            return self.session.patch(f"{self.base_url}{endpoint}", **kwargs)

        def request(self, method, endpoint, **kwargs):
            """Make a request to the API with the specified method.

            Args:
                method: The HTTP method to use.
                endpoint: The endpoint to request.
                **kwargs: Additional arguments to pass to requests.request.

            Returns:
                Response: The HTTP response.
            """
            return self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)

    return APIClient(session, api_base_url)