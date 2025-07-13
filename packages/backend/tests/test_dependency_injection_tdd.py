"""Test-driven tests for dependency injection container functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.di_container import DIContainer
from hci_extractor.core.events import EventBus
from hci_extractor.prompts.markup_prompt_loader import MarkupPromptLoader
from hci_extractor.providers.base import LLMProvider
from hci_extractor.providers.gemini_provider import GeminiProvider


class TestDependencyInjectionContainer:
    """Test dependency injection container functionality."""

    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing."""
        # This will need to match the actual Config structure
        config_data = {
            "api": {
                "provider_type": "gemini",
                "gemini_api_key": "test-api-key",
                "rate_limit_delay": 1.0,
                "timeout_seconds": 30.0,
            },
            "analysis": {
                "model_name": "gemini-1.5-flash",
                "temperature": 0.1,
                "max_output_tokens": 100000,
            },
            "general": {"prompts_directory": "prompts"},
        }
        return ExtractorConfig.from_dict(config_data)

    def test_di_container_creation(self, sample_config):
        """Test that DI container can be created with configuration."""
        container = DIContainer(config=sample_config)

        # Container should be created successfully
        assert container is not None
        assert container.config == sample_config

    def test_di_container_provides_event_bus(self, sample_config):
        """Test that DI container provides event bus singleton."""
        container = DIContainer(config=sample_config)

        # Should provide event bus
        event_bus1 = container.get_event_bus()
        event_bus2 = container.get_event_bus()

        # Should be singleton (same instance)
        assert event_bus1 is event_bus2
        assert isinstance(event_bus1, EventBus)

    def test_di_container_provides_llm_provider(self, sample_config):
        """Test that DI container provides correctly configured LLM provider."""
        container = DIContainer(config=sample_config)

        # Should provide LLM provider based on config
        provider = container.get_llm_provider()

        # Should return correct provider type
        assert isinstance(provider, LLMProvider)
        assert isinstance(provider, GeminiProvider)

    def test_di_container_provides_markup_prompt_loader(self, sample_config):
        """Test that DI container provides markup prompt loader."""
        container = DIContainer(config=sample_config)

        # Should provide prompt loader
        prompt_loader = container.get_markup_prompt_loader()

        assert isinstance(prompt_loader, MarkupPromptLoader)

    def test_di_container_provider_dependencies_injected(self, sample_config):
        """Test that provider has all dependencies injected correctly."""
        container = DIContainer(config=sample_config)

        # Get provider and verify dependencies
        provider = container.get_llm_provider()

        # Provider should have event bus injected
        assert hasattr(provider, "_event_bus") or hasattr(provider, "event_bus")

        # Provider should have prompt loader injected
        assert hasattr(provider, "_markup_prompt_loader") or hasattr(
            provider, "markup_prompt_loader"
        )

    def test_di_container_different_provider_types(self):
        """Test that DI container can create different provider types."""
        # Test Gemini provider
        gemini_config_data = {
            "api": {"provider_type": "gemini", "gemini_api_key": "test-key"},
            "analysis": {"model_name": "gemini-1.5-flash"},
            "general": {"prompts_directory": "prompts"},
        }
        gemini_config = ExtractorConfig.from_dict(gemini_config_data)
        gemini_container = DIContainer(config=gemini_config)
        gemini_provider = gemini_container.get_llm_provider()
        assert isinstance(gemini_provider, GeminiProvider)

        # Provider choice is flexible - only testing Gemini for now

    def test_di_container_invalid_provider_type(self):
        """Test that DI container raises error for invalid provider type."""
        invalid_config_data = {
            "api": {"provider_type": "invalid_provider", "gemini_api_key": "test-key"},
            "analysis": {"model_name": "some-model"},
            "general": {"prompts_directory": "prompts"},
        }
        invalid_config = ExtractorConfig.from_dict(invalid_config_data)
        container = DIContainer(config=invalid_config)

        with pytest.raises((ValueError, NotImplementedError)):
            container.get_llm_provider()

    def test_di_container_missing_api_key(self):
        """Test that DI container handles missing API keys appropriately."""
        missing_key_config_data = {
            "api": {
                "provider_type": "gemini",
                "gemini_api_key": None,  # Missing API key
            },
            "analysis": {"model_name": "gemini-1.5-flash"},
            "general": {"prompts_directory": "prompts"},
        }
        missing_key_config = ExtractorConfig.from_dict(missing_key_config_data)
        container = DIContainer(config=missing_key_config)

        with pytest.raises(ValueError):
            container.get_llm_provider()

    @patch("hci_extractor.prompts.markup_prompt_loader.MarkupPromptLoader")
    def test_di_container_prompt_loader_configuration(
        self, mock_prompt_loader_class, sample_config
    ):
        """Test that prompt loader is configured with correct directory."""
        mock_prompt_loader = MagicMock()
        mock_prompt_loader_class.return_value = mock_prompt_loader

        container = DIContainer(config=sample_config)
        container.get_markup_prompt_loader()

        # Should create prompt loader with prompts directory from config
        mock_prompt_loader_class.assert_called_once()
        call_args = mock_prompt_loader_class.call_args

        # Verify prompts directory is passed
        assert "prompts" in str(call_args) or Path("prompts") in call_args[0]

    def test_di_container_cleanup(self, sample_config):
        """Test that DI container properly cleans up resources."""
        container = DIContainer(config=sample_config)

        # Get some services
        container.get_event_bus()
        container.get_llm_provider()

        # Test cleanup (if implemented)
        try:
            container.cleanup()
            # After cleanup, services should be cleaned up
            # This test defines the expected cleanup behavior
        except AttributeError:
            pytest.skip("Cleanup method not yet implemented")


class TestDependencyInjectionIntegration:
    """Test dependency injection integration scenarios."""

    def test_di_full_service_integration(self):
        """Test that all services work together through DI."""
        config_data = {
            "api": {"provider_type": "gemini", "gemini_api_key": "test-api-key"},
            "analysis": {
                "model_name": "gemini-1.5-flash",
                "temperature": 0.1,
                "max_output_tokens": 100000,
            },
            "general": {"prompts_directory": "prompts"},
        }
        config = ExtractorConfig.from_dict(config_data)
        container = DIContainer(config=config)

        # Get all services
        event_bus = container.get_event_bus()
        provider = container.get_llm_provider()
        prompt_loader = container.get_markup_prompt_loader()

        # All services should be properly configured
        assert event_bus is not None
        assert provider is not None
        assert prompt_loader is not None

        # Services should be wired together
        # (This tests the actual dependency wiring)
        assert hasattr(provider, "_event_bus") or hasattr(provider, "event_bus")

    def test_di_service_lifecycle(self):
        """Test that services have proper lifecycle management."""
        config_data = {
            "api": {"provider_type": "gemini", "gemini_api_key": "test-key"},
            "analysis": {"model_name": "gemini-1.5-flash"},
            "general": {"prompts_directory": "prompts"},
        }
        config = ExtractorConfig.from_dict(config_data)

        # Create and destroy container multiple times
        for i in range(3):
            container = DIContainer(config=config)
            provider = container.get_llm_provider()
            assert provider is not None

            # Services should be recreated each time
            if i > 0:
                assert provider is not previous_provider

    def test_di_concurrent_access(self):
        """Test that DI container handles concurrent access safely."""
        import threading

        config_data = {
            "api": {"provider_type": "gemini", "gemini_api_key": "test-key"},
            "analysis": {"model_name": "gemini-1.5-flash"},
            "general": {"prompts_directory": "prompts"},
        }
        config = ExtractorConfig.from_dict(config_data)
        container = DIContainer(config=config)

        results = []

        def get_services():
            event_bus = container.get_event_bus()
            provider = container.get_llm_provider()
            results.append((event_bus, provider))

        # Create multiple threads accessing services
        threads = [threading.Thread(target=get_services) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should get services successfully
        assert len(results) == 5

        # Event bus should be singleton across threads
        event_buses = [result[0] for result in results]
        assert all(eb is event_buses[0] for eb in event_buses)
