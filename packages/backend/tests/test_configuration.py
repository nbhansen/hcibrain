"""Test configuration loading and immutability."""

import pytest

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.di_container import create_configured_container
from hci_extractor.infrastructure.configuration_service import ConfigurationService


class TestConfiguration:
    """Test configuration loading and management."""

    def test_configuration_is_immutable(self):
        """Test that configuration objects are immutable."""
        container = create_configured_container()
        config = container.resolve(ExtractorConfig)

        # Verify frozen dataclass
        assert hasattr(config, "__dataclass_fields__")
        assert config.__dataclass_params__.frozen

        # Try to modify - should raise AttributeError
        with pytest.raises(AttributeError):
            config.log_level = "DEBUG"  # type: ignore

    def test_can_load_configuration_from_yaml(self):
        """Test that configuration can be loaded from YAML."""
        container = create_configured_container()
        config = container.resolve(ExtractorConfig)

        # Basic structure verification
        assert hasattr(config, "extraction")
        assert hasattr(config, "analysis")
        assert hasattr(config, "api")
        assert hasattr(config, "retry")
        assert hasattr(config, "cache")
        assert hasattr(config, "export")

        # Verify some expected values
        assert isinstance(config.analysis.chunk_size, int)
        assert config.analysis.chunk_size > 0
        assert isinstance(config.extraction.max_file_size_mb, int)

    def test_configuration_service_centralizes_environment_access(self):
        """Test that ConfigurationService centralizes environment variable access."""
        config_service = ConfigurationService()

        # Should be able to get environment variables through the service
        test_var = config_service.get_environment_variable("PATH")
        assert test_var is not None  # PATH should exist on all systems

        # Should handle missing variables gracefully
        missing_var = config_service.get_environment_variable(
            "NON_EXISTENT_VARIABLE_12345"
        )
        assert missing_var is None

    def test_configuration_nested_objects_are_immutable(self):
        """Test that nested configuration objects are also immutable."""
        container = create_configured_container()
        config = container.resolve(ExtractorConfig)

        # Test nested objects are frozen
        with pytest.raises(AttributeError):
            config.analysis.chunk_size = 9999  # type: ignore

        with pytest.raises(AttributeError):
            config.extraction.max_file_size_mb = 9999  # type: ignore
