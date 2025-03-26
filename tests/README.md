# Relex Backend Tests

This directory contains tests for the Relex Backend application. The tests are organized as follows:

## Directory Structure

- `unit/`: Unit tests that test individual functions and components in isolation
- `integration/`: Integration tests that test the interaction between components
- `test_data/`: Persistent test data used by tests
- `run_tests.py`: Script to run tests

## Running Tests

You can run tests using the `run_tests.py` script:

```bash
# Run all tests
python tests/run_tests.py

# Run only unit tests
python tests/run_tests.py unit

# Run only integration tests
python tests/run_tests.py integration
```

## Setting Up Test Environment

To set up the test environment, create a virtual environment and install the required dependencies:

```bash
python -m venv test_venv
source test_venv/bin/activate  # On Windows: test_venv\Scripts\activate
pip install -r tests/requirements-test.txt
pip install -r functions/requirements.txt
```

## Writing Tests

When writing tests, follow these guidelines:

1. Place unit tests in the `unit/` directory
2. Place integration tests in the `integration/` directory
3. Name test files with the `test_` prefix
4. Name test functions with the `test_` prefix
5. Use the `unittest` framework for writing tests
6. Keep test data in the `test_data/` directory

## Continuous Integration

These tests are run as part of the CI/CD pipeline to ensure code quality and prevent regressions.