"""
YAML-based configuration management for HCI Extractor.

This module provides immutable configuration objects loaded from config.yaml,
ensuring all settings are centralized in a single source of truth.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from hci_extractor.core.ports import ConfigurationPort


@dataclass(frozen=True)
class ConfigurationData:
    """Immutable configuration data loaded from configuration sources."""

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


@dataclass(frozen=True)
class ExtractionConfig:
    """Configuration for PDF extraction operations."""

    max_file_size_mb: int
    timeout_seconds: float
    normalize_text: bool
    extract_positions: bool


@dataclass(frozen=True)
class AnalysisConfig:
    """Configuration for LLM analysis operations."""

    chunk_size: int
    chunk_overlap: int
    max_concurrent_sections: int
    section_timeout_seconds: float
    min_section_length: int
    model_name: str
    temperature: float
    max_output_tokens: int


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int
    initial_delay_seconds: float
    backoff_multiplier: float
    max_delay_seconds: float


@dataclass(frozen=True)
class CacheConfig:
    """Configuration for caching behavior."""

    enabled: bool
    directory: Optional[Path]
    ttl_seconds: int
    max_size_mb: int


@dataclass(frozen=True)
class ApiConfig:
    """Configuration for API settings."""

    provider_type: str  # "gemini", "openai", "anthropic"
    gemini_api_key: Optional[str]
    openai_api_key: Optional[str]
    anthropic_api_key: Optional[str]
    rate_limit_delay: float
    timeout_seconds: float


@dataclass(frozen=True)
class ExportConfig:
    """Configuration for export operations."""

    include_metadata: bool
    include_confidence: bool
    min_confidence_threshold: float
    timestamp_format: str



@dataclass(frozen=True)
class ExtractorConfig:
    """Main configuration object containing all sub-configurations."""

    extraction: ExtractionConfig
    analysis: AnalysisConfig
    api: ApiConfig
    retry: RetryConfig
    cache: CacheConfig
    export: ExportConfig
    prompts_directory: Path
    log_level: str

    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> "ExtractorConfig":
        """
        Create configuration from YAML file.

        Args:
            config_path: Path to config.yaml file. If None, uses default location.

        Returns:
            Immutable configuration object loaded from YAML

        Raises:
            ConfigurationError: If config file cannot be loaded or is invalid
        """
        from hci_extractor.infrastructure.configuration_service import (
            ConfigurationService,
        )

        config_service = ConfigurationService(config_path)
        config_data = config_service.load_configuration()

        # Validate API configuration
        config_service.validate_api_configuration(config_data)

        return cls.from_configuration_data(config_data, config_service)

    @classmethod
    def from_configuration_data(
        cls,
        config_data: ConfigurationData,
        config_service: ConfigurationPort,
    ) -> "ExtractorConfig":
        """
        Create configuration from configuration data object.

        This method separates domain logic from infrastructure concerns.
        """
        return cls(
            extraction=ExtractionConfig(
                max_file_size_mb=int(config_data.extraction["max_file_size_mb"]),
                timeout_seconds=float(config_data.extraction["timeout_seconds"]),
                normalize_text=bool(config_data.extraction["normalize_text"]),
                extract_positions=bool(config_data.extraction["extract_positions"]),
            ),
            analysis=AnalysisConfig(
                chunk_size=int(config_data.analysis["chunk_size"]),
                chunk_overlap=int(config_data.analysis["chunk_overlap"]),
                max_concurrent_sections=int(
                    config_data.analysis["max_concurrent_sections"],
                ),
                section_timeout_seconds=float(
                    config_data.analysis["section_timeout_seconds"],
                ),
                min_section_length=int(config_data.analysis["min_section_length"]),
                model_name=str(config_data.analysis["model_name"]),
                temperature=float(config_data.analysis["temperature"]),
                max_output_tokens=int(config_data.analysis["max_output_tokens"]),
            ),
            api=ApiConfig(
                provider_type=str(config_data.api["provider_type"]),
                gemini_api_key=config_data.api.get("gemini_api_key"),
                openai_api_key=config_data.api.get("openai_api_key"),
                anthropic_api_key=config_data.api.get("anthropic_api_key"),
                rate_limit_delay=float(config_data.api["rate_limit_delay"]),
                timeout_seconds=float(config_data.api["timeout_seconds"]),
            ),
            retry=RetryConfig(
                max_attempts=int(config_data.retry["max_attempts"]),
                initial_delay_seconds=float(config_data.retry["initial_delay_seconds"]),
                backoff_multiplier=float(config_data.retry["backoff_multiplier"]),
                max_delay_seconds=float(config_data.retry["max_delay_seconds"]),
            ),
            cache=CacheConfig(
                enabled=bool(config_data.cache["enabled"]),
                directory=config_service.get_cache_directory(config_data),
                ttl_seconds=int(config_data.cache["ttl_seconds"]),
                max_size_mb=int(config_data.cache["max_size_mb"]),
            ),
            export=ExportConfig(
                include_metadata=bool(config_data.export["include_metadata"]),
                include_confidence=bool(config_data.export["include_confidence"]),
                min_confidence_threshold=float(
                    config_data.export["min_confidence_threshold"],
                ),
                timestamp_format=str(config_data.export["timestamp_format"]),
            ),
            prompts_directory=config_service.get_prompts_directory(config_data),
            log_level=str(config_data.general["log_level"]),
        )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "ExtractorConfig":
        """Create ExtractorConfig from dictionary (for TDD tests)."""
        # Convert dict to expected structure with type conversion
        extraction_data = config_dict.get("extraction", {})
        extraction = ExtractionConfig(
            max_file_size_mb=int(extraction_data.get("max_file_size_mb", 50)),
            timeout_seconds=float(extraction_data.get("timeout_seconds", 30.0)),
            normalize_text=bool(extraction_data.get("normalize_text", True)),
            extract_positions=bool(extraction_data.get("extract_positions", True)),
        )
        
        analysis_data = config_dict.get("analysis", {})
        analysis = AnalysisConfig(
            chunk_size=int(analysis_data.get("chunk_size", 10000)),
            chunk_overlap=int(analysis_data.get("chunk_overlap", 500)),
            max_concurrent_sections=int(analysis_data.get("max_concurrent_sections", 3)),
            section_timeout_seconds=float(analysis_data.get("section_timeout_seconds", 60.0)),
            min_section_length=int(analysis_data.get("min_section_length", 50)),
            model_name=str(analysis_data.get("model_name", "gemini-1.5-flash")),
            temperature=float(analysis_data.get("temperature", 0.1)),
            max_output_tokens=int(analysis_data.get("max_output_tokens", 100000)),
        )
        
        api = ApiConfig(
            provider_type=config_dict.get("api", {}).get("provider_type", "gemini"),
            gemini_api_key=config_dict.get("api", {}).get("gemini_api_key"),
            openai_api_key=config_dict.get("api", {}).get("openai_api_key"),
            anthropic_api_key=config_dict.get("api", {}).get("anthropic_api_key"),
            rate_limit_delay=config_dict.get("api", {}).get("rate_limit_delay", 1.0),
            timeout_seconds=config_dict.get("api", {}).get("timeout_seconds", 30.0),
        )
        
        retry = RetryConfig(
            max_attempts=config_dict.get("retry", {}).get("max_attempts", 3),
            initial_delay_seconds=config_dict.get("retry", {}).get("initial_delay_seconds", 2.0),
            backoff_multiplier=config_dict.get("retry", {}).get("backoff_multiplier", 2.0),
            max_delay_seconds=config_dict.get("retry", {}).get("max_delay_seconds", 30.0),
        )
        
        cache = CacheConfig(
            enabled=config_dict.get("cache", {}).get("enabled", False),
            directory=None,
            ttl_seconds=config_dict.get("cache", {}).get("ttl_seconds", 3600),
            max_size_mb=config_dict.get("cache", {}).get("max_size_mb", 1000),
        )
        
        export = ExportConfig(
            include_metadata=config_dict.get("export", {}).get("include_metadata", True),
            include_confidence=config_dict.get("export", {}).get("include_confidence", True),
            min_confidence_threshold=config_dict.get("export", {}).get("min_confidence_threshold", 0.0),
            timestamp_format=config_dict.get("export", {}).get("timestamp_format", "%Y-%m-%d %H:%M:%S"),
        )
        
        return cls(
            extraction=extraction,
            analysis=analysis,
            api=api,
            retry=retry,
            cache=cache,
            export=export,
            prompts_directory=Path(config_dict.get("general", {}).get("prompts_directory", "prompts")),
            log_level=config_dict.get("general", {}).get("log_level", "INFO"),
        )
