"""Minimal CLI functionality test."""

import pytest
from click.testing import CliRunner

from hci_extractor.cli.commands import cli


class TestCLIBasic:
    """Test basic CLI functionality."""

    def test_cli_main_command_exists(self):
        """Test that the main CLI command exists and is accessible."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        # Should show help without errors
        assert result.exit_code == 0
        assert "HCI Paper Extractor" in result.output

    def test_cli_shows_available_commands(self):
        """Test that CLI shows available commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        # Should list main commands
        assert "extract" in result.output
        assert "config" in result.output

    def test_cli_config_command_works(self):
        """Test that the config command works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config"])

        # Config command should run without errors
        assert result.exit_code == 0
        assert "Configuration Options" in result.output

    def test_cli_diagnose_command_works(self):
        """Test that the diagnose command works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["diagnose"])

        # Diagnose should run and show system checks
        assert result.exit_code == 0
        assert "System Diagnostic" in result.output

    def test_cli_extract_command_requires_file(self):
        """Test that extract command requires a file argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["extract"])

        # Should fail with missing argument error
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_cli_version_command_works(self):
        """Test that version command works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])

        # Should show version info
        assert result.exit_code == 0
        assert "HCI Paper Extractor" in result.output
        assert "Python" in result.output
