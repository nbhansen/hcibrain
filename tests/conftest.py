"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path

@pytest.fixture
def sample_data_dir():
    """Path to sample test data."""
    return Path(__file__).parent / "fixtures"