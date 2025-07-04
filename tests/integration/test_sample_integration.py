#!/usr/bin/env python3
"""
Sample Integration Test

This module contains sample integration tests to demonstrate the testing setup.
Integration tests test the interaction between multiple components.
"""

import pytest
import json
import requests
from unittest.mock import Mock, patch

@pytest.fixture
def mock_post():
    """Fixture to mock requests.post."""
    with patch('requests.post') as mock_post:
        # Set up a mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'data': {'test': 'value'}}
        mock_post.return_value = mock_response
        yield mock_post

def test_sample_http_call(mock_post):
    """Test a sample HTTP call with a mock."""
    # Make a request using the mocked requests library
    response = requests.post('https://example.com/api',
                            json={'test': 'payload'})

    # Check the response
    assert response.status_code == 200
    assert response.json() == {'success': True, 'data': {'test': 'value'}}

    # Verify the mock was called with the right arguments
    mock_post.assert_called_once_with('https://example.com/api',
                                      json={'test': 'payload'})

@pytest.mark.skip(reason="This test actually connects to a real API")
def test_real_integration():
    """A real integration test that would connect to an actual service."""
    # This test is skipped by default as it would actually make a real HTTP call
    response = requests.get('https://jsonplaceholder.typicode.com/todos/1')
    assert response.status_code == 200
    data = response.json()
    assert 'userId' in data
    assert 'id' in data
    assert 'title' in data

def test_api_base_url_fixture(api_base_url):
    """Test that the api_base_url fixture is working."""
    assert api_base_url in ["https://api-dev.relex.ro", "https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/v1"], f"Unexpected API base URL: {api_base_url}"