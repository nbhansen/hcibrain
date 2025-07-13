"""Test-driven tests for configuration loading functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.infrastructure.configuration_service import ConfigurationService


class TestConfigurationLoading:
    """Test configuration loading from YAML files."""

    @pytest.fixture
    def sample_config_dict(self):
        """Sample configuration data."""
        return {
            "api": {
                "provider_type": "gemini",
                "gemini_api_key": "test-api-key",
                "openai_api_key": None,
                "anthropic_api_key": None,
                "rate_limit_delay": 1.0,
                "timeout_seconds": 30.0,
            },
            "extraction": {
                "max_file_size_mb": 50,
                "timeout_seconds": 30.0,
                "normalize_text": True,
                "extract_positions": True,
            },
            "analysis": {
                "chunk_size": 10000,
                "chunk_overlap": 500,
                "max_concurrent_sections": 3,
                "section_timeout_seconds": 60.0,
                "min_section_length": 50,
                "model_name": "gemini-2.5-pro",
                "temperature": 0.1,
                "max_output_tokens": 100000,
            },
            "retry": {
                "max_attempts": 3,
                "initial_delay_seconds": 2.0,
                "backoff_multiplier": 2.0,
                "max_delay_seconds": 30.0,
            },
            "cache": {
                "enabled": False,
                "directory": None,
                "ttl_seconds": 3600,
                "max_size_mb": 1000,
            },
            "export": {
                "include_metadata": True,
                "include_confidence": True,
                "min_confidence_threshold": 0.0,
                "timestamp_format": "%Y-%m-%d %H:%M:%S",
            },
            "general": {"prompts_directory": "prompts", "log_level": "INFO"},
        }

    @pytest.fixture
    def temp_config_file(self, sample_config_dict):
        """Create temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(sample_config_dict, f)
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink(missing_ok=True)

    def test_load_config_from_file_success(self, temp_config_file):
        """Test successful configuration loading from YAML file."""
        config_service = ConfigurationService()

        # Test loading configuration
        config = config_service.load_config(temp_config_file)

        # Verify config is loaded correctly
        assert isinstance(config, ExtractorConfig)
        assert config.api.provider_type == "gemini"
        assert config.api.gemini_api_key == "test-api-key"
        assert config.extraction.max_file_size_mb == 50
        assert config.analysis.chunk_size == 10000

    def test_load_config_file_not_found(self):
        """Test configuration loading with non-existent file."""
        config_service = ConfigurationService()
        non_existent_path = Path("/non/existent/config.yaml")

        with pytest.raises(FileNotFoundError):
            config_service.load_config(non_existent_path)

    def test_load_config_invalid_yaml(self):
        """Test configuration loading with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            config_service = ConfigurationService()
            with pytest.raises(yaml.YAMLError):
                config_service.load_config(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_config_validation_required_fields(self, sample_config_dict):
        """Test that configuration validates required fields."""
        # Remove required field
        del sample_config_dict["api"]["provider_type"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(sample_config_dict, f)
            temp_path = Path(f.name)

        try:
            config_service = ConfigurationService()
            with pytest.raises((KeyError, ValueError)):
                config_service.load_config(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_config_immutability(self, temp_config_file):
        """Test that loaded configuration objects are immutable."""
        config_service = ConfigurationService()
        config = config_service.load_config(temp_config_file)

        # ExtractorConfig should be frozen (immutable)
        with pytest.raises(AttributeError):
            config.api.provider_type = "different_provider"

    @patch.dict("os.environ", {"GEMINI_API_KEY": "env-api-key"})
    def test_environment_variable_override(self, sample_config_dict):
        """Test that environment variables can override config values."""
        # Remove API key from config
        sample_config_dict["api"]["gemini_api_key"] = None

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(sample_config_dict, f)
            temp_path = Path(f.name)

        try:
            config_service = ConfigurationService()
            config = config_service.load_config(temp_path)

            # Should use environment variable
            assert config.api.gemini_api_key == "env-api-key"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_config_default_values(self):
        """Test that configuration has sensible defaults."""
        # Minimal config
        minimal_config = {
            "api": {"provider_type": "gemini", "gemini_api_key": "test-key"}
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(minimal_config, f)
            temp_path = Path(f.name)

        try:
            config_service = ConfigurationService()
            config = config_service.load_config(temp_path)

            # Should have defaults for missing sections
            assert hasattr(config, "extraction")
            assert hasattr(config, "analysis")
            assert hasattr(config, "retry")

            # Default values should be reasonable
            assert config.extraction.max_file_size_mb > 0
            assert config.analysis.chunk_size > 0
            assert config.retry.max_attempts > 0
        finally:
            temp_path.unlink(missing_ok=True)

    def test_config_type_conversion(self, sample_config_dict):
        """Test that configuration values are converted to correct types."""
        # Set string values that should be converted
        sample_config_dict["extraction"]["max_file_size_mb"] = "50"
        sample_config_dict["analysis"]["temperature"] = "0.1"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(sample_config_dict, f)
            temp_path = Path(f.name)

        try:
            config_service = ConfigurationService()
            config = config_service.load_config(temp_path)

            # Values should be converted to correct types
            assert isinstance(config.extraction.max_file_size_mb, int)
            assert isinstance(config.analysis.temperature, float)
        finally:
            temp_path.unlink(missing_ok=True)


class TestConfigurationValidation:
    """Test configuration validation rules."""

    def test_api_key_validation(self):
        """Test that API key validation works correctly."""
        config_dict = {
            "api": {
                "provider_type": "gemini",
                "gemini_api_key": "",  # Empty key should be invalid
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_dict, f)
            temp_path = Path(f.name)

        try:
            config_service = ConfigurationService()
            with pytest.raises(ValueError):
                config_service.load_config(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_numerical_range_validation(self):
        """Test that numerical values are within valid ranges."""
        config_dict = {
            "api": {"provider_type": "gemini", "gemini_api_key": "valid-key"},
            "analysis": {
                "temperature": 2.0  # Should be between 0 and 1
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_dict, f)
            temp_path = Path(f.name)

        try:
            config_service = ConfigurationService()
            with pytest.raises(ValueError):
                config_service.load_config(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_provider_type_validation(self):
        """Test that provider type is validated."""
        config_dict = {
            "api": {"provider_type": "invalid_provider", "gemini_api_key": "test-key"}
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_dict, f)
            temp_path = Path(f.name)

        try:
            config_service = ConfigurationService()
            with pytest.raises(ValueError):
                config_service.load_config(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)
