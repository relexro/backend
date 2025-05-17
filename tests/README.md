# Relex Backend Tests

This directory contains tests for the Relex Backend application. The tests are organized as follows:

## Directory Structure

- `unit/`: Unit tests that test individual functions and components in isolation
- `integration/`: Integration tests that test the interaction between components
- `test_data/`: Persistent test data used by tests

## Running Tests

You can run tests using pytest:

```bash
# Run all tests
python -m pytest tests/

# Run only unit tests
python -m pytest tests/unit/

# Run only integration tests
python -m pytest tests/integration/

# Run tests with verbose output
python -m pytest -v tests/

# Run a specific test file
python -m pytest tests/path/to/test_file.py

# Run a specific test function
python -m pytest tests/path/to/test_file.py::test_function_name
```

## Setting Up Test Environment

To set up the test environment, create a virtual environment and install the required dependencies:

```bash
python -m venv test_venv
source test_venv/bin/activate  # On Windows: test_venv\Scripts\activate
pip install -r functions/src/requirements-dev.txt
pip install -r functions/requirements.txt
```

### Authentication for Integration Tests

Integration tests that interact with the deployed API require a Firebase JWT token for authentication. Follow these steps to obtain and use a token:

1. **Obtain a Firebase JWT token**:
   - Navigate to the `tests/` directory
   - Start a local web server: `python3 -m http.server 8080`
   - Open `http://localhost:8080/test-auth.html` in your browser
   - Click "Sign in with Google" and authenticate with your Google account
   - After successful authentication, click "Show/Hide Token" to reveal your JWT token
   - Copy the entire token

2. **Make the token available to tests** (choose one method):
   - **Method 1**: Set the `RELEX_TEST_JWT` environment variable:
     ```bash
     # Linux/macOS
     export RELEX_TEST_JWT="your_token_here"

     # Windows (Command Prompt)
     set RELEX_TEST_JWT=your_token_here

     # Windows (PowerShell)
     $env:RELEX_TEST_JWT="your_token_here"
     ```

   - **Method 2**: Create a file named `tests/temp_api_token.txt` and paste the token into it:
     ```bash
     echo "your_token_here" > tests/temp_api_token.txt
     ```
     Note: This file is gitignored and should not be committed to the repository.

3. **Run integration tests**:
   ```bash
   python -m pytest tests/integration/
   ```

If neither the environment variable nor the token file is available, integration tests that require authentication will be skipped.

## Writing Tests

When writing tests, follow these guidelines:

1. Place unit tests in the `unit/` directory
2. Place integration tests in the `integration/` directory
3. Name test files with the `test_` prefix
4. Name test functions with the `test_` prefix
5. Use the `pytest` framework for writing tests
6. Keep test data in the `test_data/` directory

### Example Test

```python
# Simple test function
def test_something():
    assert 1 + 1 == 2

# Test function with fixture
def test_with_fixture(api_base_url):
    # The API Gateway URL is found in docs/terraform_outputs.log
    assert api_base_url.startswith("https://relex-api-gateway-dev")
```

## API Specification Reference

When writing integration tests, refer to the following resources for API endpoint details:

- `docs/api.md`: High-level, human-readable API documentation
- `terraform/openapi_spec.yaml`: Authoritative OpenAPI v3 specification

These documents define the available endpoints, methods, request/response bodies, and authentication requirements.

### API Gateway URL

The API is accessed via the default Google Cloud API Gateway URL, not the custom domain. To find this URL:

1. Check the `docs/terraform_outputs.log` file after deployment
2. Look for the `api_gateway_url` key (e.g., `relex-api-gateway-dev-mvef5dk.ew.gateway.dev`)
3. Use this URL as the base for all API requests in tests

### Health Checks

When testing API endpoints, you can verify the health of a function by including the `X-Google-Health-Check` header:

```python
response = requests.get(
    f"{api_base_url}/endpoint/path",
    headers={"X-Google-Health-Check": "true"}
)
assert response.status_code == 200
assert response.json()["status"] == "healthy"
```

Note that health checks are implemented using the `X-Google-Health-Check` header rather than specific paths like `/_ah/health`.

Example:
```python
# In conftest.py or similar
@pytest.fixture
def api_base_url():
    # Read from terraform_outputs.log or use environment variable
    return "https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev"
```

Note: The custom domain `api-dev.relex.ro` is not currently the active endpoint for the API Gateway.

## Test Data Management

Integration tests interact with a live (dev) environment and may create, modify, or delete data. Follow these guidelines for test data management:

1. **Clean up after tests**: Tests should clean up any data they create. Use `pytest` fixtures with proper teardown to ensure cleanup.

2. **Isolate test data**: Use unique identifiers (e.g., prefixes like `test_`) for test data to avoid conflicts with real data.

3. **Use helper fixtures**: Common setup/teardown tasks should be implemented as fixtures in `tests/conftest.py` or helper functions in `tests/helpers/`.

4. **Document dependencies**: If a test requires specific pre-existing data, document this clearly in the test docstring.

Example of a test with proper setup and teardown:

```python
@pytest.fixture
def test_organization(api_client):
    """Create a test organization and clean it up after the test."""
    # Setup
    org_data = {
        "name": f"Test Org {uuid.uuid4()}",
        "type": "legal_firm"
    }
    response = api_client.post("/organizations", json=org_data)
    org_id = response.json()["id"]

    yield org_id

    # Teardown
    api_client.delete(f"/organizations/{org_id}")

def test_get_organization(api_client, test_organization):
    """Test getting an organization by ID."""
    org_id = test_organization
    response = api_client.get(f"/organizations/{org_id}")
    assert response.status_code == 200
    assert response.json()["id"] == org_id
```

## Continuous Integration

These tests are run as part of the CI/CD pipeline to ensure code quality and prevent regressions.