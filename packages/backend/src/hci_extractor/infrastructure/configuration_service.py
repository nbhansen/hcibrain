"""YAML-based configuration service for HCIBrain."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from hci_extractor.core.config import ExtractorConfig, ConfigurationData
from hci_extractor.core.models.exceptions import ConfigurationError
from hci_extractor.core.ports import ConfigurationPort


class ConfigurationService(ConfigurationPort):
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
                f"ExtractorConfiguration file not found: {self.config_path}. "
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
                raise ConfigurationError(
                    "ExtractorConfiguration file must contain a YAML dictionary",
                )

            # Validate required sections exist
            required_sections = [
                "api",
                "extraction",
                "analysis",
                "retry",
                "cache",
                "export",
                "general",
            ]
            for section in required_sections:
                if section not in config_dict:
                    raise ConfigurationError(
                        f"Missing required configuration section: {section}",
                    )

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
            raise ConfigurationError(
                f"ExtractorConfiguration file not found: {self.config_path}",
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e

    def load_config(self, config_path: Path) -> ExtractorConfig:
        """Load configuration from YAML file and return ExtractorConfig object.
        
        This method is compatible with TDD tests.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Immutable ExtractorConfig object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValueError: If configuration validation fails
        """
        if not config_path.exists():
            raise FileNotFoundError(f"ExtractorConfiguration file not found: {config_path}")
            
        try:
            with config_path.open("r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
                
            if not isinstance(config_dict, dict):
                raise ValueError("ExtractorConfiguration file must contain a YAML dictionary")
                
            # Validate provider type
            provider_type = config_dict.get("api", {}).get("provider_type")
            if provider_type not in ["gemini", "openai", "anthropic"]:
                raise ValueError(f"Invalid provider type: {provider_type}")
                
            # Validate API key
            api_section = config_dict.get("api", {})
            api_key = api_section.get(f"{provider_type}_api_key")
            if not api_key or api_key == "":
                # Check environment variable
                env_key = os.environ.get(f"{provider_type.upper()}_API_KEY")
                if not env_key:
                    raise ValueError(f"API key required for provider: {provider_type}")
                # Override with environment variable
                config_dict["api"][f"{provider_type}_api_key"] = env_key
                
            # Type conversion and validation
            analysis = config_dict.get("analysis", {})
            temperature = analysis.get("temperature", 0.1)
            try:
                temperature = float(temperature)
                if not (0.0 <= temperature <= 1.0):
                    raise ValueError(f"Temperature must be between 0.0 and 1.0, got: {temperature}")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid temperature value: {temperature}") from e
                
            return ExtractorConfig.from_dict(config_dict)
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in configuration file: {e}") from e
        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError, yaml.YAMLError)):
                raise
            raise ValueError(f"Failed to load configuration: {e}") from e

    def get_prompts_directory(self, config_data: ConfigurationData) -> Path:
        """Get the prompts directory path from configuration.

        Args:
            config_data: ExtractorConfiguration data object

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
            config_data: ExtractorConfiguration data object

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
            config_data: ExtractorConfiguration data object

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
                "No valid API key configured. Please set at least one API key in "
                "config.yaml",
            )

    def get_environment_variable(
        self,
        key: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Get environment variable value through configuration service.

        Args:
            key: Environment variable key
            default: Default value if not found

        Returns:
            Environment variable value or default
        """

        return os.environ.get(key, default)

    def has_environment_variable(self, key: str) -> bool:
        """Check if environment variable exists.

        Args:
            key: Environment variable key

        Returns:
            True if environment variable exists
        """

        return key in os.environ

    def get_debug_mode(self) -> bool:
        """Get debug mode from environment or config.

        Returns:
            True if debug mode is enabled
        """
        debug_value = self.get_environment_variable("DEBUG", "false")
        return debug_value.lower() in ("true", "1", "yes") if debug_value else False

    def get_config_path_from_env(self) -> Optional[str]:
        """Get configuration path from environment variable.

        Returns:
            ExtractorConfiguration path from environment or None
        """
        return self.get_environment_variable("HCI_CONFIG_PATH")

    def get_log_level_from_env(self) -> Optional[str]:
        """Get log level from environment variable.

        Returns:
            Log level from environment or None
        """
        return self.get_environment_variable("HCI_LOG_LEVEL")

    # ExtractorConfigurationPort interface implementation

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        if provider.lower() == "gemini":
            return self.get_environment_variable("GEMINI_API_KEY")
        if provider.lower() == "openai":
            return self.get_environment_variable("OPENAI_API_KEY")
        return self.get_environment_variable(f"{provider.upper()}_API_KEY")

    def get_environment_value(
        self, key: str, default: Optional[str] = None
    ) -> Optional[str]:
        """Get environment variable value."""
        return self.get_environment_variable(key, default)

    def get_configuration_dict(self) -> Dict[str, Any]:
        """Get the complete configuration as a dictionary."""
        try:
            config_data = self.load_configuration()
            return {
                "api": config_data.api,
                "extraction": config_data.extraction,
                "analysis": config_data.analysis,
                "retry": config_data.retry,
                "cache": config_data.cache,
                "export": config_data.export,
                "general": config_data.general,
            }
        except ConfigurationError:
            return {}

    def validate_configuration(self) -> bool:
        """Validate that the configuration is complete and valid."""
        try:
            config_data = self.load_configuration()
            self.validate_api_configuration(config_data)
            return True
        except (ConfigurationError, Exception):
            return False
