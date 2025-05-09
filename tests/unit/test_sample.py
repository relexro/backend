#!/usr/bin/env python3
"""
Sample Unit Test

This module contains sample unit tests to demonstrate the testing setup.
"""

import pytest

def test_sample():
    """Sample test case."""
    assert 1 + 1 == 2

@pytest.mark.skip(reason="This test is skipped to demonstrate skipping functionality")
def test_sample_fail():
    """A test case that will be skipped to demonstrate failure handling."""
    assert 1 + 1 == 3  # This would fail if not skipped