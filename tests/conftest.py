"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_data_dir():
    """Path to sample test data."""
    return Path(__file__).parent / "fixtures"
