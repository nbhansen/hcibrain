"""Configuration port interface for domain layer."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ConfigurationPort(ABC):
    """
    Port interface for configuration services in hexagonal architecture.

    This interface defines the contract that infrastructure adapters must implement
    to provide configuration services to the domain layer. The domain layer depends
    only on this abstraction, not on concrete implementations.
    """

    @abstractmethod
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider.

        Args:
            provider: Name of the provider (e.g., 'gemini', 'openai')

        Returns:
            API key if found, None otherwise
        """

    @abstractmethod
    def get_environment_value(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get environment variable value.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Environment value or default
        """

    @abstractmethod
    def get_configuration_dict(self) -> Dict[str, Any]:
        """
        Get the complete configuration as a dictionary.

        Returns:
            Complete configuration dictionary
        """

    @abstractmethod
    def load_configuration(self) -> Dict[str, Any]:
        """
        Load configuration from all sources (files, environment, etc.).

        Returns:
            Loaded configuration data
        """

    @abstractmethod
    def validate_configuration(self) -> bool:
        """
        Validate that the configuration is complete and valid.

        Returns:
            True if valid, False otherwise
        """
