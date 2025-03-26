# Test Data Directory

This directory contains persistent test data files that are created and used by the tests. These files help maintain consistency between test runs.

## Files

- `test_org_id.txt`: Contains the ID of a test organization created for testing organization membership functionality.

## Purpose

These files are automatically created when running tests that need them. They allow tests to refer to the same resources (like organizations or users) across multiple test runs, which is useful for integration tests that depend on existing data.

## Notes

- Files in this directory should not be committed to version control unless they contain non-sensitive, static test data.
- When using CI/CD, this directory is typically recreated for each pipeline run.
- Test data may be periodically cleaned up to avoid accumulation of test resources. 