"""Test setup file that modifies Python path and imports for testing."""
import sys
import os
from unittest.mock import MagicMock

# Add the mock_setup directory to sys.path before any other imports
mock_setup_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'functions', 'src', 'mock_setup'))
sys.path.insert(0, mock_setup_path)

# Mock essential modules
sys.modules['auth'] = __import__('auth') 