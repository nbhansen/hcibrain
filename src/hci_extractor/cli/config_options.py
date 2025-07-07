"""
Configuration option mapping for CLI arguments.

This module defines which configuration options should be exposed as CLI arguments,
their types, validation, and help text. It serves as the bridge between the
command-line interface and the internal configuration system.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import click

from hci_extractor.core.config import ExtractorConfig


@dataclass(frozen=True)
class CliConfigOption:
    """Definition of a CLI configuration option."""

    cli_name: str  # CLI argument name (e.g., --chunk-size)
    config_path: str  # Path in config object (e.g., "analysis.chunk_size")
    cli_type: Any  # Click type for argument parsing
    default_description: str  # Description of default value
    help_text: str  # Help text for CLI help
    validator: Optional[Callable[[Any], Any]] = None  # Optional validation function
    priority: str = "medium"  # Priority level: high, medium, low


# Core configuration options that should be exposed via CLI
CLI_CONFIG_MAPPING: Dict[str, CliConfigOption] = {
    # HIGH PRIORITY: Core operations that users frequently need to adjust
    "chunk_size": CliConfigOption(
        cli_name="--chunk-size",
        config_path="analysis.chunk_size",
        cli_type=int,
        default_description="10000 characters",
        help_text="Text processing chunk size in characters. Larger chunks mean "
        "fewer API calls but higher token usage.",
        validator=lambda x: max(1000, min(x, 50000)),  # Clamp between reasonable bounds
        priority="high",
    ),
    "timeout": CliConfigOption(
        cli_name="--timeout",
        config_path="analysis.section_timeout_seconds",
        cli_type=float,
        default_description="60.0 seconds",
        help_text="LLM request timeout in seconds. Increase for large sections "
        "or slow connections.",
        validator=lambda x: max(5.0, min(x, 300.0)),  # 5 seconds to 5 minutes
        priority="high",
    ),
    "extraction_timeout": CliConfigOption(
        cli_name="--extraction-timeout",
        config_path="extraction.timeout_seconds",
        cli_type=float,
        default_description="30.0 seconds",
        help_text="PDF extraction timeout in seconds. Increase for large files.",
        validator=lambda x: max(5.0, min(x, 300.0)),  # 5 seconds to 5 minutes
        priority="low",
    ),
    "max_retries": CliConfigOption(
        cli_name="--max-retries",
        config_path="retry.max_attempts",
        cli_type=int,
        default_description="3 attempts",
        help_text="Maximum retry attempts for failed operations. Higher values "
        "increase reliability but processing time.",
        validator=lambda x: max(1, min(x, 10)),  # 1 to 10 attempts
        priority="high",
    ),
    "retry_delay": CliConfigOption(
        cli_name="--retry-delay",
        config_path="retry.initial_delay_seconds",
        cli_type=float,
        default_description="2.0 seconds",
        help_text="Initial delay between retries in seconds. Uses exponential "
        "backoff for subsequent retries.",
        validator=lambda x: max(0.1, min(x, 60.0)),  # 0.1 seconds to 1 minute
        priority="high",
    ),
    "max_concurrent": CliConfigOption(
        cli_name="--max-concurrent",
        config_path="analysis.max_concurrent_sections",
        cli_type=int,
        default_description="3 operations",
        help_text="Maximum concurrent operations for batch processing. Higher "
        "values increase speed but API load.",
        validator=lambda x: max(1, min(x, 10)),  # 1 to 10 concurrent operations
        priority="high",
    ),
    # MEDIUM PRIORITY: LLM and processing settings
    "temperature": CliConfigOption(
        cli_name="--temperature",
        config_path="analysis.temperature",
        cli_type=float,
        default_description="0.1 (focused)",
        help_text="LLM temperature for creativity vs consistency. Lower values "
        "(0.0-0.3) for consistent extraction.",
        validator=lambda x: max(0.0, min(x, 2.0)),  # Standard temperature range
        priority="medium",
    ),
    "max_tokens": CliConfigOption(
        cli_name="--max-tokens",
        config_path="analysis.max_output_tokens",
        cli_type=int,
        default_description="4000 tokens",
        help_text="Maximum tokens per LLM response. Higher values allow more "
        "extractions per section.",
        validator=lambda x: max(
            500, min(x, 8000)
        ),  # Reasonable bounds for token limits
        priority="medium",
    ),
    "chunk_overlap": CliConfigOption(
        cli_name="--chunk-overlap",
        config_path="analysis.chunk_overlap",
        cli_type=int,
        default_description="500 characters",
        help_text="Character overlap between text chunks to avoid splitting sentences.",
        validator=lambda x: max(0, min(x, 2000)),  # 0 to 2000 characters
        priority="medium",
    ),
    "min_section_length": CliConfigOption(
        cli_name="--min-section-length",
        config_path="analysis.min_section_length",
        cli_type=int,
        default_description="50 characters",
        help_text="Minimum section length to process. Shorter sections are skipped.",
        validator=lambda x: max(10, min(x, 1000)),  # 10 to 1000 characters
        priority="medium",
    ),
    # LOW PRIORITY: Advanced and debugging options
    "log_level": CliConfigOption(
        cli_name="--log-level",
        config_path="log_level",
        cli_type=click.Choice(
            ["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False
        ),
        default_description="INFO",
        help_text="Logging level for debugging and monitoring.",
        priority="low",
    ),
    "normalize_text": CliConfigOption(
        cli_name="--normalize-text",
        config_path="extraction.normalize_text",
        cli_type=bool,
        default_description="True",
        help_text="Apply text normalization to clean PDF extraction artifacts.",
        priority="low",
    ),
    "max_file_size": CliConfigOption(
        cli_name="--max-file-size",
        config_path="extraction.max_file_size_mb",
        cli_type=int,
        default_description="50 MB",
        help_text="Maximum PDF file size to process in megabytes.",
        validator=lambda x: max(1, min(x, 500)),  # 1 MB to 500 MB
        priority="low",
    ),
    "max_delay": CliConfigOption(
        cli_name="--max-retry-delay",
        config_path="retry.max_delay_seconds",
        cli_type=float,
        default_description="30.0 seconds",
        help_text="Maximum delay between retries using exponential backoff.",
        validator=lambda x: max(1.0, min(x, 300.0)),  # 1 second to 5 minutes
        priority="low",
    ),
    "min_confidence": CliConfigOption(
        cli_name="--min-confidence",
        config_path="export.min_confidence_threshold",
        cli_type=float,
        default_description="0.0 (all elements)",
        help_text="Minimum confidence score for exported elements (0.0-1.0).",
        validator=lambda x: max(0.0, min(x, 1.0)),  # 0.0 to 1.0
        priority="low",
    ),
}


def get_options_by_priority(priority: str) -> Dict[str, CliConfigOption]:
    """Get configuration options filtered by priority level."""
    return {
        name: option
        for name, option in CLI_CONFIG_MAPPING.items()
        if option.priority == priority
    }


def get_high_priority_options() -> Dict[str, CliConfigOption]:
    """Get high priority configuration options for core commands."""
    return get_options_by_priority("high")


def get_medium_priority_options() -> Dict[str, CliConfigOption]:
    """Get medium priority configuration options for advanced usage."""
    return get_options_by_priority("medium")


def get_low_priority_options() -> Dict[str, CliConfigOption]:
    """Get low priority configuration options for debugging and fine-tuning."""
    return get_options_by_priority("low")


def add_config_arguments(
    parser: click.Command,
    priorities: Optional[list[str]] = None,
    command_specific: Optional[Dict[str, CliConfigOption]] = None,
) -> None:
    """
    Add configuration arguments to a Click command.

    Args:
        parser: Click command to add arguments to
        priorities: List of priority levels to include (high, medium, low)
        command_specific: Optional command-specific configuration options
    """
    # Get options for specified priorities
    if priorities is None:
        priorities = ["high"]
    
    options_to_add = {}
    for priority in priorities:
        options_to_add.update(get_options_by_priority(priority))

    # Add command-specific options
    if command_specific:
        options_to_add.update(command_specific)

    # Add each option as a Click argument
    for option_name, option in options_to_add.items():
        # Create Click option
        click_option = click.option(
            option.cli_name,
            type=option.cli_type,
            help=f"{option.help_text} (default: {option.default_description})",
        )

        # Apply the decorator to the parser
        parser = click_option(parser)


def get_config_path_value(config: ExtractorConfig, path: str) -> Any:
    """
    Get a configuration value using dot notation path.

    Args:
        config: Configuration object to query
        path: Dot-separated path (e.g., "analysis.chunk_size")

    Returns:
        Configuration value at the specified path
    """
    parts = path.split(".")
    value = config

    for part in parts:
        value = getattr(value, part)

    return value


def set_config_path_value(config_dict: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set a configuration value using dot notation path in a dictionary structure.

    Args:
        config_dict: Dictionary to modify (nested structure)
        path: Dot-separated path (e.g., "analysis.chunk_size")
        value: Value to set
    """
    parts = path.split(".")
    current = config_dict

    # Navigate to the parent of the target
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set the final value
    current[parts[-1]] = value


def validate_cli_value(option: CliConfigOption, value: Any) -> Any:
    """
    Validate and potentially transform a CLI argument value.

    Args:
        option: Configuration option definition
        value: Raw value from CLI argument

    Returns:
        Validated and potentially transformed value

    Raises:
        click.BadParameter: If validation fails
    """
    if value is None:
        return None

    try:
        # Apply validator if present
        if option.validator:
            validated_value = option.validator(value)
            if validated_value != value:
                click.echo(
                    f"Note: {option.cli_name} value adjusted from {value} to "
                    f"{validated_value} "
                    f"(within valid range)",
                    err=True,
                )
            return validated_value

        return value

    except Exception as e:
        raise click.BadParameter(
            f"Invalid value for {option.cli_name}: {value}. {str(e)}"
        ) from e


# Command-specific option sets for different CLI commands

EXTRACT_COMMAND_OPTIONS = {
    # High priority options most relevant for single paper extraction
    **get_high_priority_options(),
    # Selected medium priority options for advanced users
    "temperature": CLI_CONFIG_MAPPING["temperature"],
    "max_tokens": CLI_CONFIG_MAPPING["max_tokens"],
}

BATCH_COMMAND_OPTIONS = {
    # All high priority options are relevant for batch processing
    **get_high_priority_options(),
    # Medium priority options particularly useful for batch operations
    "chunk_overlap": CLI_CONFIG_MAPPING["chunk_overlap"],
    "min_section_length": CLI_CONFIG_MAPPING["min_section_length"],
}

EXPORT_COMMAND_OPTIONS = {
    # Export-specific options
    "min_confidence": CLI_CONFIG_MAPPING["min_confidence"],
    "log_level": CLI_CONFIG_MAPPING["log_level"],
}

VALIDATE_COMMAND_OPTIONS = {
    # Validation-specific options
    "extraction_timeout": CLI_CONFIG_MAPPING["extraction_timeout"],
    "max_file_size": CLI_CONFIG_MAPPING["max_file_size"],
    "normalize_text": CLI_CONFIG_MAPPING["normalize_text"],
}
