#!/usr/bin/env python3
"""
Sample Unit Test

This module contains sample unit tests to demonstrate the testing setup.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import the code
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, parent_dir)

class SampleUnitTest(unittest.TestCase):
    """Sample unit tests to demonstrate the testing framework."""
    
    def setUp(self):
        """Set up test fixtures, if any."""
        pass
        
    def tearDown(self):
        """Tear down test fixtures, if any."""
        pass
    
    def test_sample(self):
        """Sample test case."""
        self.assertEqual(1 + 1, 2)
    
    def test_sample_fail(self):
        """A test case that will be skipped to demonstrate failure handling."""
        self.skipTest("This test is skipped to demonstrate skipping functionality")
        self.assertEqual(1 + 1, 3)  # This would fail if not skipped

if __name__ == '__main__':
    unittest.main() 