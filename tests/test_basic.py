"""Basic tests for the CLI foundation."""

import subprocess
import sys
from pathlib import Path


def test_cli_version():
    """Test that the CLI version command works."""
    result = subprocess.run(
        [sys.executable, "-m", "hci_extractor", "--version"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_cli_help():
    """Test that the CLI help command works."""
    result = subprocess.run(
        [sys.executable, "-m", "hci_extractor", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0
    assert "HCI Paper Extractor" in result.stdout
    assert "version" in result.stdout


def test_import_package():
    """Test that the package can be imported."""
    import hci_extractor

    assert hci_extractor.__version__ == "0.1.0"