#!/usr/bin/env python3
"""
Relex Backend Test Runner

This script runs tests for the Relex Backend application.
It can be used to run all tests or specific test categories.

Usage:
    python run_tests.py [unit|integration|all]
"""

import os
import sys
import importlib
import unittest
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def discover_tests(test_dir):
    """Discover tests in the given directory."""
    loader = unittest.TestLoader()
    return loader.discover(test_dir, pattern="test_*.py")

def run_tests(test_suite):
    """Run the given test suite."""
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(test_suite)

def main():
    """Main entry point for the test runner."""
    # Ensure we're in the right directory
    if not os.path.exists('unit') or not os.path.exists('integration'):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
    
    # Add parent directory to Python path
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, parent_dir)
    
    # Determine which tests to run
    test_type = 'all'
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    
    # Run the appropriate tests
    if test_type == 'unit' or test_type == 'all':
        logger.info("Running unit tests...")
        unit_tests = discover_tests('unit')
        run_tests(unit_tests)
    
    if test_type == 'integration' or test_type == 'all':
        logger.info("Running integration tests...")
        integration_tests = discover_tests('integration')
        run_tests(integration_tests)
    
    logger.info("Test run complete.")

if __name__ == "__main__":
    main() 