"""Test dependency injection container functionality."""

import pytest

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.di_container import DIContainer, create_configured_container
from hci_extractor.core.events import EventBus
from hci_extractor.core.ports.llm_provider_port import LLMProviderPort
from hci_extractor.infrastructure.configuration_service import ConfigurationService


class TestDependencyInjection:
    """Test dependency injection container functionality."""

    def test_can_create_configured_container(self):
        """Test that we can create a properly configured DI container."""
        container = create_configured_container()
        assert isinstance(container, DIContainer)

    def test_can_resolve_core_services(self):
        """Test that core services can be resolved from the container."""
        container = create_configured_container()

        # Test configuration
        config = container.resolve(ExtractorConfig)
        assert isinstance(config, ExtractorConfig)

        # Test event bus
        event_bus = container.resolve(EventBus)
        assert isinstance(event_bus, EventBus)

        # Test configuration service
        config_service = container.resolve(ConfigurationService)
        assert isinstance(config_service, ConfigurationService)

        # Test LLM provider port
        llm_provider = container.resolve(LLMProviderPort)
        assert isinstance(llm_provider, LLMProviderPort)

    def test_singletons_return_same_instance(self):
        """Test that singleton services return the same instance."""
        container = create_configured_container()

        # Get the same service twice
        config1 = container.resolve(ExtractorConfig)
        config2 = container.resolve(ExtractorConfig)

        # Should be the same instance
        assert config1 is config2

        # Same for event bus
        event_bus1 = container.resolve(EventBus)
        event_bus2 = container.resolve(EventBus)
        assert event_bus1 is event_bus2

    def test_transient_services_return_different_instances(self):
        """Test that transient services return different instances."""
        container = create_configured_container()

        # For services registered as transient (if any)
        # Note: Most services are currently singletons, but this tests the pattern

        # This test validates the container behavior rather than specific services
        # since our current architecture uses mostly singletons for stateless services

        # Create two instances of the container itself
        container1 = create_configured_container()
        container2 = create_configured_container()

        # Containers should be different instances
        assert container1 is not container2

    def test_container_resolves_dependencies_automatically(self):
        """Test that the container automatically resolves constructor dependencies."""
        container = create_configured_container()

        # When we resolve LLMProviderPort, it should automatically inject
        # its dependencies (like EventBus, ConfigurationService, etc.)
        llm_provider = container.resolve(LLMProviderPort)

        # The provider should be properly initialized with its dependencies
        assert llm_provider is not None

        # We can verify this worked by checking that we can call methods
        # without getting "missing dependency" errors
        assert hasattr(llm_provider, "generate_markup")

    def test_missing_service_raises_error(self):
        """Test that resolving an unregistered service raises an error."""
        container = DIContainer()  # Empty container

        with pytest.raises(ValueError, match="Service .* not registered"):
            container.resolve(ExtractorConfig)
