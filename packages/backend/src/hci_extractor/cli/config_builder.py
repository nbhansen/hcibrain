"""
Configuration builder for merging CLI arguments with existing configuration.

This module implements the configuration precedence logic:
CLI args > Environment vars > Config file > Defaults

It creates new immutable configuration objects that incorporate CLI overrides
while maintaining the existing configuration architecture.
"""

import argparse
import os
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Optional

from hci_extractor.cli.config_options import (
    CLI_CONFIG_MAPPING,
    CliConfigOption,
    get_config_path_value,
    set_config_path_value,
    validate_cli_value,
)
from hci_extractor.core.config import ExtractorConfig


class ConfigurationBuilder:
    """
    Builder for creating configuration objects with CLI argument overrides.

    This class maintains immutability by always returning new configuration
    objects rather than modifying existing ones.
    """

    def __init__(self, base_config: Optional[ExtractorConfig] = None):
        """
        Initialize configuration builder.

        Args:
            base_config: Base configuration to build upon (defaults to global config)
        """
        self._base_config = base_config or ExtractorConfig.from_yaml()
        self._overrides: Dict[str, Any] = {}

    def with_cli_args(self, args: argparse.Namespace) -> "ConfigurationBuilder":
        """
        Apply CLI arguments as configuration overrides.

        Args:
            args: Parsed CLI arguments from argparse or click

        Returns:
            New ConfigurationBuilder with CLI overrides applied
        """
        # Create new builder to maintain immutability
        new_builder = ConfigurationBuilder(self._base_config)
        new_builder._overrides = self._overrides.copy()

        # Process CLI arguments
        for arg_name, arg_value in vars(args).items():
            if arg_value is None:
                continue  # Skip unset arguments

            # Find corresponding configuration option
            cli_option = self._find_cli_option_by_arg_name(arg_name)
            if cli_option:
                # Validate the value
                validated_value = validate_cli_value(cli_option, arg_value)
                new_builder._overrides[cli_option.config_path] = validated_value

        return new_builder

    def with_env_vars(self, env_prefix: str = "HCI_") -> "ConfigurationBuilder":
        """
        Apply environment variable overrides.

        Args:
            env_prefix: Prefix for environment variables (default: HCI_)

        Returns:
            New ConfigurationBuilder with environment overrides applied
        """
        # Create new builder
        new_builder = ConfigurationBuilder(self._base_config)
        new_builder._overrides = self._overrides.copy()

        # Process environment variables
        for env_var, env_value in os.environ.items():
            if not env_var.startswith(env_prefix):
                continue

            # Convert environment variable name to config path
            config_path = self._env_var_to_config_path(env_var, env_prefix)
            if config_path:
                # Convert string value to appropriate type
                typed_value = self._convert_env_value(config_path, env_value)
                new_builder._overrides[config_path] = typed_value

        return new_builder

    def with_override(self, config_path: str, value: Any) -> "ConfigurationBuilder":
        """
        Apply a single configuration override.

        Args:
            config_path: Dot-separated configuration path (e.g., "analysis.chunk_size")
            value: Value to set

        Returns:
            New ConfigurationBuilder with override applied
        """
        new_builder = ConfigurationBuilder(self._base_config)
        new_builder._overrides = self._overrides.copy()
        new_builder._overrides[config_path] = value
        return new_builder

    def build(self) -> ExtractorConfig:
        """
        Build the final configuration object with all overrides applied.

        Returns:
            New immutable ExtractorConfig with overrides applied
        """
        if not self._overrides:
            return self._base_config

        # Create nested dictionary structure for overrides
        override_dict: Dict[str, Any] = {}
        for path, value in self._overrides.items():
            set_config_path_value(override_dict, path, value)

        # Apply overrides to create new configuration objects
        new_extraction = self._apply_overrides_to_dataclass(
            self._base_config.extraction, override_dict.get("extraction", {}),
        )

        new_analysis = self._apply_overrides_to_dataclass(
            self._base_config.analysis, override_dict.get("analysis", {}),
        )

        new_retry = self._apply_overrides_to_dataclass(
            self._base_config.retry, override_dict.get("retry", {}),
        )

        new_cache = self._apply_overrides_to_dataclass(
            self._base_config.cache, override_dict.get("cache", {}),
        )

        new_export = self._apply_overrides_to_dataclass(
            self._base_config.export, override_dict.get("export", {}),
        )

        # Create new main configuration
        return replace(
            self._base_config,
            extraction=new_extraction,
            analysis=new_analysis,
            retry=new_retry,
            cache=new_cache,
            export=new_export,
            log_level=override_dict.get("log_level", self._base_config.log_level),
            prompts_directory=override_dict.get(
                "prompts_directory", self._base_config.prompts_directory,
            ),
        )

    def _find_cli_option_by_arg_name(self, arg_name: str) -> Optional[CliConfigOption]:
        """Find CLI option definition by argument name."""
        # Convert argument name format to match CLI option names
        cli_arg_name = f"--{arg_name.replace('_', '-')}"

        for option in CLI_CONFIG_MAPPING.values():
            if option.cli_name == cli_arg_name:
                return option

        return None

    def _env_var_to_config_path(self, env_var: str, prefix: str) -> Optional[str]:
        """Convert environment variable name to configuration path."""
        # Remove prefix and convert to lowercase
        var_name = env_var[len(prefix) :].lower()

        # Map known environment variables to configuration paths
        env_mapping = {
            # Extraction
            "extraction_max_file_size_mb": "extraction.max_file_size_mb",
            "extraction_timeout_seconds": "extraction.timeout_seconds",
            "extraction_normalize_text": "extraction.normalize_text",
            "extraction_extract_positions": "extraction.extract_positions",
            # Analysis
            "analysis_chunk_size": "analysis.chunk_size",
            "analysis_chunk_overlap": "analysis.chunk_overlap",
            "analysis_max_concurrent": "analysis.max_concurrent_sections",
            "analysis_section_timeout": "analysis.section_timeout_seconds",
            "analysis_min_section_length": "analysis.min_section_length",
            "analysis_temperature": "analysis.temperature",
            "analysis_max_output_tokens": "analysis.max_output_tokens",
            # Retry
            "retry_max_attempts": "retry.max_attempts",
            "retry_initial_delay": "retry.initial_delay_seconds",
            "retry_backoff_multiplier": "retry.backoff_multiplier",
            "retry_max_delay": "retry.max_delay_seconds",
            # Cache
            "cache_enabled": "cache.enabled",
            "cache_dir": "cache.directory",
            "cache_ttl_seconds": "cache.ttl_seconds",
            "cache_max_size_mb": "cache.max_size_mb",
            # Export
            "export_include_metadata": "export.include_metadata",
            "export_include_confidence": "export.include_confidence",
            "export_min_confidence": "export.min_confidence_threshold",
            "export_timestamp_format": "export.timestamp_format",
            # Top-level
            "log_level": "log_level",
            "prompts_dir": "prompts_directory",
        }

        return env_mapping.get(var_name)

    def _convert_env_value(self, config_path: str, env_value: str) -> Any:
        """Convert environment variable string value to appropriate type."""
        # Find the current value to determine type
        try:
            current_value = get_config_path_value(self._base_config, config_path)
            current_type = type(current_value)

            # Convert based on current type
            if current_type is bool:
                return env_value.lower() in ("true", "1", "yes", "on")
            if current_type is int:
                return int(env_value)
            if current_type is float:
                return float(env_value)
            if current_type == Path:
                return Path(env_value)
            return env_value  # String or unknown type

        except (AttributeError, ValueError):
            # If we can't determine the type, return as string
            return env_value

    def _apply_overrides_to_dataclass(
        self, original: Any, overrides: Dict[str, Any],
    ) -> Any:
        """Apply overrides to a dataclass, returning a new instance."""
        if not overrides:
            return original

        # Use dataclass replace to create new instance with overrides
        return replace(original, **overrides)


def merge_configurations(
    cli_args: Optional[argparse.Namespace] = None,
    env_prefix: str = "HCI_",
    base_config: Optional[ExtractorConfig] = None,
) -> ExtractorConfig:
    """
    Convenience function to merge configurations with proper precedence.

    Precedence (highest to lowest):
    1. CLI arguments (explicit user intent)
    2. Environment variables (session configuration)
    3. Configuration file (persistent settings)
    4. Default values (fallback)

    Args:
        cli_args: Parsed CLI arguments
        env_prefix: Environment variable prefix
        base_config: Base configuration (defaults to global config)

    Returns:
        New ExtractorConfig with all overrides applied
    """
    builder = ConfigurationBuilder(base_config)

    # Apply environment variables first (lower precedence)
    builder = builder.with_env_vars(env_prefix)

    # Apply CLI arguments last (highest precedence)
    if cli_args:
        builder = builder.with_cli_args(cli_args)

    return builder.build()


def create_config_from_click_context(ctx: Any, base_config: Optional[ExtractorConfig] = None) -> ExtractorConfig:
    """
    Create configuration from Click context.

    Args:
        ctx: Click context containing parsed arguments
        base_config: Base configuration to override (optional)

    Returns:
        ExtractorConfig with CLI overrides applied
    """
    # Convert Click context to Namespace-like object
    if hasattr(ctx, "params"):
        # Create namespace from Click parameters
        args = argparse.Namespace()
        for key, value in ctx.params.items():
            setattr(args, key, value)

        return merge_configurations(cli_args=args, base_config=base_config)

    # Fallback to base configuration
    return base_config or ExtractorConfig.from_yaml()


def validate_configuration(config: ExtractorConfig) -> ExtractorConfig:
    """
    Validate a configuration object and return a corrected version if needed.

    Args:
        config: Configuration to validate

    Returns:
        Validated configuration (may be modified to fix invalid values)

    Raises:
        ValueError: If configuration contains invalid values that cannot be corrected
    """
    issues = []

    # Validate extraction configuration
    if config.extraction.max_file_size_mb <= 0:
        issues.append("max_file_size_mb must be positive")

    if config.extraction.timeout_seconds <= 0:
        issues.append("timeout_seconds must be positive")

    # Validate analysis configuration
    if config.analysis.chunk_size < 100:
        issues.append("chunk_size must be at least 100 characters")

    if config.analysis.chunk_overlap >= config.analysis.chunk_size:
        issues.append("chunk_overlap must be less than chunk_size")

    if config.analysis.max_concurrent_sections <= 0:
        issues.append("max_concurrent_sections must be positive")

    if not (0.0 <= config.analysis.temperature <= 2.0):
        issues.append("temperature must be between 0.0 and 2.0")

    # Validate retry configuration
    if config.retry.max_attempts <= 0:
        issues.append("max_attempts must be positive")

    if config.retry.initial_delay_seconds < 0:
        issues.append("initial_delay_seconds cannot be negative")

    if config.retry.backoff_multiplier < 1.0:
        issues.append("backoff_multiplier must be at least 1.0")

    # Validate export configuration
    if not (0.0 <= config.export.min_confidence_threshold <= 1.0):
        issues.append("min_confidence_threshold must be between 0.0 and 1.0")

    if issues:
        raise ValueError(f"Configuration validation failed: {'; '.join(issues)}")

    return config
