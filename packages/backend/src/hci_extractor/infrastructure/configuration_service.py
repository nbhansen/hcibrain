"""YAML-based configuration service for HCIBrain."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from hci_extractor.core.models.exceptions import ConfigurationError


@dataclass(frozen=True)
class ConfigurationData:
    """Immutable configuration data loaded from YAML."""

    # API configuration
    api: Dict[str, Any]

    # Extraction configuration
    extraction: Dict[str, Any]

    # Analysis configuration
    analysis: Dict[str, Any]

    # Retry configuration
    retry: Dict[str, Any]

    # Cache configuration
    cache: Dict[str, Any]

    # Export configuration
    export: Dict[str, Any]

    # General configuration
    general: Dict[str, Any]


class ConfigurationService:
    """Service for loading YAML-based configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration service.

        Args:
            config_path: Path to config.yaml file. If None, uses default location.
        """
        if config_path is None:
            # Default to config.yaml in project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config.yaml"

        self.config_path = Path(config_path)

        if not self.config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}. "
                "Please create config.yaml from the template.",
            )

    def load_configuration(self) -> ConfigurationData:
        """Load configuration from YAML file.

        Returns:
            Immutable configuration data object

        Raises:
            ConfigurationError: If config file cannot be loaded or is invalid
        """
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)

            if not isinstance(config_dict, dict):
                raise ConfigurationError("Configuration file must contain a YAML dictionary")

            # Validate required sections exist
            required_sections = ["api", "extraction", "analysis", "retry", "cache", "export", "general"]
            for section in required_sections:
                if section not in config_dict:
                    raise ConfigurationError(f"Missing required configuration section: {section}")

            return ConfigurationData(
                api=config_dict["api"],
                extraction=config_dict["extraction"],
                analysis=config_dict["analysis"],
                retry=config_dict["retry"],
                cache=config_dict["cache"],
                export=config_dict["export"],
                general=config_dict["general"],
            )

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}") from e
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e

    def get_prompts_directory(self, config_data: ConfigurationData) -> Path:
        """Get the prompts directory path from configuration.

        Args:
            config_data: Configuration data object

        Returns:
            Path to prompts directory
        """
        prompts_dir = config_data.general.get("prompts_directory", "prompts")

        if Path(prompts_dir).is_absolute():
            return Path(prompts_dir)
        # Relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        return project_root / prompts_dir

    def get_cache_directory(self, config_data: ConfigurationData) -> Optional[Path]:
        """Get the cache directory path if configured.

        Args:
            config_data: Configuration data object

        Returns:
            Path to cache directory or None if not configured
        """
        cache_dir = config_data.cache.get("directory")

        if cache_dir is None:
            return None

        if Path(cache_dir).is_absolute():
            return Path(cache_dir)
        # Relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        return project_root / cache_dir

    def validate_api_configuration(self, config_data: ConfigurationData) -> None:
        """Validate API configuration has required keys.

        Args:
            config_data: Configuration data object

        Raises:
            ConfigurationError: If API configuration is invalid
        """
        api_config = config_data.api

        # Check that at least one API key is configured
        api_keys = [
            api_config.get("gemini_api_key"),
            api_config.get("openai_api_key"),
            api_config.get("anthropic_api_key"),
        ]

        if not any(key and key != "your-gemini-api-key-here" for key in api_keys):
            raise ConfigurationError(
                "No valid API key configured. Please set at least one API key in config.yaml",
            )
