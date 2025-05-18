"""End-to-end integration tests for user endpoints."""
import os
import pytest
import requests

@pytest.mark.skipif(not os.environ.get("RELEX_TEST_JWT"),
              reason="RELEX_TEST_JWT environment variable is not set")
def test_get_user_me_e2e_deployed_api(api_client):
    """
    Tests the GET /v1/users/me endpoint on the deployed API.

    This is an end-to-end integration test that calls the deployed API Gateway
    endpoint and validates the response structure and data types.
    """
    response = api_client.get("/users/me")
    assert response.status_code == 200, \
        f"Expected 200 OK, but got {response.status_code}. Response: {response.text}"

    data = response.json()

    # Validate based on UserPublicProfile model and user's curl output
    assert "userId" in data
    assert isinstance(data["userId"], str)
    assert len(data["userId"]) > 0  # Basic check for non-empty string

    assert "email" in data
    assert isinstance(data["email"], str)
    assert "@" in data["email"]  # Basic email format check

    assert "displayName" in data  # Value can be string or null
    if data["displayName"] is not None:
        assert isinstance(data["displayName"], str)

    assert "role" in data
    assert isinstance(data["role"], str)
    assert data["role"] in ["user", "admin", "system_agent"]  # Check valid roles

    assert "languagePreference" in data  # Value can be string or null
    if data["languagePreference"] is not None:
        assert isinstance(data["languagePreference"], str)
        assert data["languagePreference"] in ["en", "ro", "fr", "de", "es"]  # Check valid languages

    assert "subscriptionStatus" in data  # Value can be string or null
    if data["subscriptionStatus"] is not None:
        assert isinstance(data["subscriptionStatus"], str)

    assert "createdAt" in data
    assert isinstance(data["createdAt"], str)
    # Basic date format check - should contain date separators
    assert any(sep in data["createdAt"] for sep in [":", "-", "/"])

    assert "updatedAt" in data
    assert isinstance(data["updatedAt"], str)
    # Basic date format check - should contain date separators
    assert any(sep in data["updatedAt"] for sep in [":", "-", "/"])
