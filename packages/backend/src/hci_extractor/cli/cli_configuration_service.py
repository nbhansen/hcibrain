"""CLI Configuration Service following hexagonal architecture principles."""

from typing import Optional

import click

from hci_extractor.cli.config_builder import create_config_from_click_context
from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.di_container import DIContainer, create_configured_container
from hci_extractor.core.models.exceptions import InvalidParameterError


class CLIConfigurationService:
    """Service for handling CLI configuration creation and management."""

    def create_configuration_from_context(
        self,
        cli_context: Optional[click.Context] = None,
        base_config: Optional[ExtractorConfig] = None,
    ) -> ExtractorConfig:
        """
        Create configuration from CLI context with proper precedence.

        Args:
            cli_context: Click context with CLI parameters (optional)
            base_config: Base configuration to override (optional)

        Returns:
            Immutable configuration object with CLI overrides applied
        """
        if cli_context is None:
            return base_config or ExtractorConfig.from_yaml()

        # Check if there's a profile config in the context
        profile_config = None
        if (
            hasattr(cli_context, "meta")
            and cli_context.meta
            and "profile_config" in cli_context.meta
        ):
            profile_config = cli_context.meta["profile_config"]

        # Use profile config as base if available, otherwise use provided base or env
        effective_base = profile_config or base_config

        # Create configuration from CLI context
        return create_config_from_click_context(cli_context, base_config=effective_base)

    def validate_cli_configuration(self, config: ExtractorConfig) -> bool:
        """
        Validate that CLI configuration is valid for operation.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Basic validation - extend as needed
        if config.analysis.chunk_size <= 0:
            raise InvalidParameterError()

        if config.analysis.max_concurrent_sections <= 0:
            raise InvalidParameterError()

        if config.retry.max_attempts <= 0:
            raise InvalidParameterError()

        return True


class CLIContainerFactory:
    """Factory for creating DI containers with CLI configuration."""

    def __init__(self, configuration_service: CLIConfigurationService):
        """Initialize factory with configuration service."""
        self._configuration_service = configuration_service

    def create_container_with_cli_config(
        self,
        cli_context: Optional[click.Context] = None,
    ) -> DIContainer:
        """
        Create DI container with CLI-specific configuration.

        Args:
            cli_context: Click context with CLI parameters (optional)

        Returns:
            Configured DI container ready for command execution
        """
        # Create base container with default configuration
        container = create_configured_container()

        # Apply CLI configuration overrides if context provided
        if cli_context is not None:
            cli_config = self._configuration_service.create_configuration_from_context(
                cli_context,
            )

            # Validate the CLI configuration
            self._configuration_service.validate_cli_configuration(cli_config)

            # Override the configuration in the container
            container.register_instance(ExtractorConfig, cli_config)

        return container

    def create_container_with_config(self, config: ExtractorConfig) -> DIContainer:
        """
        Create DI container with specific configuration.

        Args:
            config: Configuration to use

        Returns:
            Configured DI container
        """
        container = create_configured_container()

        # Validate the configuration
        self._configuration_service.validate_cli_configuration(config)

        # Register the specific configuration
        container.register_instance(ExtractorConfig, config)

        return container


# Default service instances for CLI commands
_default_configuration_service = CLIConfigurationService()
_default_container_factory = CLIContainerFactory(_default_configuration_service)


def get_cli_configuration_service() -> CLIConfigurationService:
    """Get the default CLI configuration service."""
    return _default_configuration_service


def get_cli_container_factory() -> CLIContainerFactory:
    """Get the default CLI container factory."""
    return _default_container_factory
