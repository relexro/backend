#!/usr/bin/env python3
"""
Sample Integration Test

This module contains sample integration tests to demonstrate the testing setup.
Integration tests test the interaction between multiple components.
"""

import unittest
import sys
import os
import json
import requests
import unittest.mock as mock

# Add the parent directory to the path so we can import the code
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, parent_dir)

class SampleIntegrationTest(unittest.TestCase):
    """Sample integration tests to demonstrate the testing framework."""
    
    def setUp(self):
        """Set up test fixtures, if any."""
        # Mock the requests library for testing HTTP calls
        self.patcher = mock.patch('requests.post')
        self.mock_post = self.patcher.start()
        
        # Set up a mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'data': {'test': 'value'}}
        self.mock_post.return_value = mock_response
        
    def tearDown(self):
        """Tear down test fixtures, if any."""
        self.patcher.stop()
    
    def test_sample_http_call(self):
        """Test a sample HTTP call with a mock."""
        # Make a request using the mocked requests library
        response = requests.post('https://example.com/api', 
                                json={'test': 'payload'})
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True, 'data': {'test': 'value'}})
        
        # Verify the mock was called with the right arguments
        self.mock_post.assert_called_once_with('https://example.com/api', 
                                              json={'test': 'payload'})
    
    @unittest.skip("This test actually connects to a real API")
    def test_real_integration(self):
        """A real integration test that would connect to an actual service."""
        # This test is skipped by default as it would actually make a real HTTP call
        response = requests.get('https://jsonplaceholder.typicode.com/todos/1')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('userId', data)
        self.assertIn('id', data)
        self.assertIn('title', data)

if __name__ == '__main__':
    unittest.main() 