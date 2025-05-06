#!/usr/bin/env python
"""
Test script for the relex_backend_agent_handler function
"""
import json
import logging
from flask import Flask, Request
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

# Add the functions/src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'functions/src'))

# Now we can import from functions/src
from main import relex_backend_agent_handler

# Create a simple mock request
class MockRequest:
    def __init__(self, json_data, path):
        self.json_data = json_data
        self.path = path
        # Add attributes set by the authentication middleware
        self.user_id = "test_user_123"
        self.user_email = "test@example.com"
    
    def get_json(self, silent=False):
        return self.json_data

# Test the agent handler
def test_agent_handler():
    # Create a mock request with a simple message
    mock_request = MockRequest(
        json_data={"message": "Test message for the agent"},
        path="/cases/test_case_123/agent/messages"
    )
    
    try:
        # Call the agent handler
        logging.info("Calling relex_backend_agent_handler...")
        result = relex_backend_agent_handler(mock_request)
        logging.info(f"Agent handler result: {result}")
        return result
    except Exception as e:
        logging.error(f"Error calling agent handler: {str(e)}", exc_info=True)
        return {"error": str(e)}

if __name__ == "__main__":
    print("Testing the relex_backend_agent_handler function...")
    result = test_agent_handler()
    print(f"Test result: {json.dumps(result, indent=2)}") 