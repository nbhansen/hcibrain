"""Test CLI configuration integration."""

import argparse
import os
from unittest.mock import patch

import pytest

from hci_extractor.cli.config_builder import (
    ConfigurationBuilder,
    merge_configurations,
    validate_configuration,
)
from hci_extractor.cli.config_options import (
    CLI_CONFIG_MAPPING,
    get_config_path_value,
    get_high_priority_options,
    set_config_path_value,
    validate_cli_value,
)
from hci_extractor.core.config import AnalysisConfig, ExtractorConfig, RetryConfig


class TestConfigurationBuilder:
    """Test configuration builder functionality."""

    def test_builder_immutability(self):
        """Test that builder maintains immutability."""
        base_config = ExtractorConfig.for_testing()
        builder1 = ConfigurationBuilder(base_config)

        # Creating a new builder with overrides should not modify the original
        builder2 = builder1.with_override("analysis.chunk_size", 5000)

        config1 = builder1.build()
        config2 = builder2.build()

        # Original should be unchanged
        assert config1.analysis.chunk_size != 5000
        # New config should have override
        assert config2.analysis.chunk_size == 5000

    def test_cli_args_integration(self):
        """Test integration with CLI arguments."""
        base_config = ExtractorConfig.for_testing()

        # Simulate CLI arguments
        args = argparse.Namespace()
        args.chunk_size = 8000
        args.timeout = 45.0
        args.max_retries = 5
        args.temperature = 0.2

        builder = ConfigurationBuilder(base_config)
        builder = builder.with_cli_args(args)
        config = builder.build()

        # CLI arguments should override defaults
        assert config.analysis.chunk_size == 8000
        assert config.analysis.section_timeout_seconds == 45.0
        assert config.retry.max_attempts == 5
        assert config.analysis.temperature == 0.2

    def test_env_vars_integration(self):
        """Test integration with environment variables."""
        base_config = ExtractorConfig.for_testing()

        env_vars = {
            "HCI_ANALYSIS_CHUNK_SIZE": "7000",
            "HCI_RETRY_MAX_ATTEMPTS": "4",
            "HCI_ANALYSIS_TEMPERATURE": "0.3",
            "HCI_LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars):
            builder = ConfigurationBuilder(base_config)
            builder = builder.with_env_vars("HCI_")
            config = builder.build()

            assert config.analysis.chunk_size == 7000
            assert config.retry.max_attempts == 4
            assert config.analysis.temperature == 0.3
            assert config.log_level == "DEBUG"

    def test_precedence_order(self):
        """Test that CLI args take precedence over environment variables."""
        base_config = ExtractorConfig.for_testing()

        # Set environment variable
        env_vars = {"HCI_ANALYSIS_CHUNK_SIZE": "6000"}

        # Set CLI argument (should override env var)
        args = argparse.Namespace()
        args.chunk_size = 9000

        with patch.dict(os.environ, env_vars):
            config = merge_configurations(cli_args=args, base_config=base_config)

            # CLI argument should win
            assert config.analysis.chunk_size == 9000

    def test_validation_with_invalid_values(self):
        """Test configuration validation with invalid values."""
        # Create config with invalid values
        invalid_config = ExtractorConfig.for_testing(
            analysis=AnalysisConfig(
                chunk_size=-100,  # Invalid: negative
                chunk_overlap=15000,  # Invalid: larger than chunk_size
                temperature=5.0,  # Invalid: > 2.0
            ),
            retry=RetryConfig(
                max_attempts=0,  # Invalid: must be positive
                initial_delay_seconds=-1.0,  # Invalid: negative
            ),
        )

        with pytest.raises(ValueError) as exc_info:
            validate_configuration(invalid_config)

        error_message = str(exc_info.value)
        assert "chunk_size must be at least 100" in error_message
        assert "chunk_overlap must be less than chunk_size" in error_message
        assert "temperature must be between 0.0 and 2.0" in error_message
        assert "max_attempts must be positive" in error_message
        assert "initial_delay_seconds cannot be negative" in error_message


class TestConfigOptions:
    """Test CLI configuration options."""

    def test_high_priority_options(self):
        """Test that high priority options are correctly defined."""
        high_priority = get_high_priority_options()

        # Should include core operational settings
        assert "chunk_size" in high_priority
        assert "timeout" in high_priority
        assert "max_retries" in high_priority
        assert "retry_delay" in high_priority
        assert "max_concurrent" in high_priority

        # All should be high priority
        for option in high_priority.values():
            assert option.priority == "high"

    def test_cli_option_validation(self):
        """Test CLI option validation."""
        chunk_size_option = CLI_CONFIG_MAPPING["chunk_size"]

        # Valid value should pass through
        assert validate_cli_value(chunk_size_option, 5000) == 5000

        # Invalid value should be clamped
        validated = validate_cli_value(chunk_size_option, 100000)  # Too large
        assert validated <= 50000  # Should be clamped to max

        validated = validate_cli_value(chunk_size_option, 500)  # Too small
        assert validated >= 1000  # Should be clamped to min

    def test_config_path_operations(self):
        """Test configuration path get/set operations."""
        config = ExtractorConfig.for_testing()

        # Test getting nested values
        chunk_size = get_config_path_value(config, "analysis.chunk_size")
        assert chunk_size == config.analysis.chunk_size

        # Test setting nested values in dictionary
        config_dict = {}
        set_config_path_value(config_dict, "analysis.chunk_size", 8000)
        set_config_path_value(config_dict, "retry.max_attempts", 5)

        assert config_dict["analysis"]["chunk_size"] == 8000
        assert config_dict["retry"]["max_attempts"] == 5


class TestConfigurationIntegration:
    """Test end-to-end configuration integration."""

    def test_extract_command_config(self):
        """Test configuration for extract command."""
        # Simulate extract command arguments
        args = argparse.Namespace()
        args.chunk_size = 12000
        args.timeout = 90.0
        args.max_retries = 4
        args.temperature = 0.15
        args.max_tokens = 5000

        config = merge_configurations(cli_args=args)

        assert config.analysis.chunk_size == 12000
        assert config.analysis.section_timeout_seconds == 90.0
        assert config.retry.max_attempts == 4
        assert config.analysis.temperature == 0.15
        assert config.analysis.max_output_tokens == 5000

    def test_batch_command_config(self):
        """Test configuration for batch command."""
        # Simulate batch command arguments
        args = argparse.Namespace()
        args.chunk_size = 8000
        args.timeout = 120.0
        args.max_retries = 6
        args.chunk_overlap = 800
        args.min_section_length = 100

        config = merge_configurations(cli_args=args)

        assert config.analysis.chunk_size == 8000
        assert config.analysis.section_timeout_seconds == 120.0
        assert config.retry.max_attempts == 6
        assert config.analysis.chunk_overlap == 800
        assert config.analysis.min_section_length == 100

    def test_export_command_config(self):
        """Test configuration for export command."""
        # Simulate export command arguments
        args = argparse.Namespace()
        args.log_level = "DEBUG"

        config = merge_configurations(cli_args=args)

        assert config.log_level == "DEBUG"

    def test_validate_command_config(self):
        """Test configuration for validate command."""
        # Simulate validate command arguments
        args = argparse.Namespace()
        args.extraction_timeout = 15.0
        args.max_file_size = 100
        args.normalize_text = True

        config = merge_configurations(cli_args=args)

        assert config.extraction.timeout_seconds == 15.0
        assert config.extraction.max_file_size_mb == 100
        assert config.extraction.normalize_text

    def test_environment_variable_mapping(self):
        """Test environment variable to config path mapping."""
        env_vars = {
            "HCI_ANALYSIS_CHUNK_SIZE": "15000",
            "HCI_ANALYSIS_MAX_CONCURRENT": "5",
            "HCI_RETRY_INITIAL_DELAY": "3.0",
            "HCI_EXTRACTION_NORMALIZE_TEXT": "false",
            "HCI_LOG_LEVEL": "WARNING",
        }

        with patch.dict(os.environ, env_vars):
            config = merge_configurations()

            assert config.analysis.chunk_size == 15000
            assert config.analysis.max_concurrent_sections == 5
            assert config.retry.initial_delay_seconds == 3.0
            assert not config.extraction.normalize_text
            assert config.log_level == "WARNING"

    def test_configuration_help_text(self):
        """Test that configuration options have helpful descriptions."""
        for option_name, option in CLI_CONFIG_MAPPING.items():
            # All options should have helpful descriptions
            assert len(option.help_text) > 20  # Reasonable minimum length
            assert option.default_description  # Should have default description
            assert option.cli_name.startswith("--")  # Should be proper CLI format
            # Most options should have nested paths, except top-level ones like log_level
            if option_name != "log_level":
                assert "." in option.config_path  # Should have nested path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
