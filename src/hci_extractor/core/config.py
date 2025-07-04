"""
Centralized configuration management for HCI Extractor.

This module provides immutable configuration objects that can be loaded
from environment variables, ensuring all settings are centralized and
easily configurable without code changes.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from hci_extractor.infrastructure.configuration_service import EnvironmentConfiguration, ConfigurationService


@dataclass(frozen=True)
class ExtractionConfig:
    """Configuration for PDF extraction operations."""

    max_file_size_mb: int = 50
    timeout_seconds: float = 30.0
    normalize_text: bool = True
    extract_positions: bool = False  # Character positions are memory-intensive


@dataclass(frozen=True)
class AnalysisConfig:
    """Configuration for LLM analysis operations."""

    chunk_size: int = 10000
    chunk_overlap: int = 500
    max_concurrent_sections: int = 3
    section_timeout_seconds: float = 60.0
    min_section_length: int = 50
    temperature: float = 0.1
    max_output_tokens: int = 4000


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay_seconds: float = 2.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 30.0


@dataclass(frozen=True)
class CacheConfig:
    """Configuration for caching behavior."""

    enabled: bool = False
    directory: Optional[Path] = None
    ttl_seconds: int = 3600
    max_size_mb: int = 1000


@dataclass(frozen=True)
class ApiConfig:
    """Configuration for API settings."""

    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    rate_limit_delay: float = 1.0
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class ExportConfig:
    """Configuration for export operations."""

    include_metadata: bool = True
    include_confidence: bool = True
    min_confidence_threshold: float = 0.0
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"


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
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ExtractorConfig":
        """
        Create configuration from environment variables using infrastructure service.

        Environment variables follow the pattern: HCI_<SECTION>_<SETTING>
        For example: HCI_ANALYSIS_CHUNK_SIZE=8000
        """
        from hci_extractor.infrastructure.configuration_service import ConfigurationService
        
        config_service = ConfigurationService()
        env_config = config_service.load_from_environment()
        
        return cls.from_environment_configuration(env_config, config_service)
    
    @classmethod
    def from_environment_configuration(
        cls, 
        env_config: "EnvironmentConfiguration", 
        config_service: "ConfigurationService"
    ) -> "ExtractorConfig":
        """
        Create configuration from environment configuration object.
        
        This method separates domain logic from infrastructure concerns.
        """
        return cls(
            extraction=ExtractionConfig(
                max_file_size_mb=int(env_config.extraction_max_file_size_mb),
                timeout_seconds=float(env_config.extraction_timeout_seconds),
                normalize_text=env_config.extraction_normalize_text.lower() == "true",
                extract_positions=env_config.extraction_extract_positions.lower() == "true",
            ),
            analysis=AnalysisConfig(
                chunk_size=int(env_config.analysis_chunk_size),
                chunk_overlap=int(env_config.analysis_chunk_overlap),
                max_concurrent_sections=int(env_config.analysis_max_concurrent),
                section_timeout_seconds=float(env_config.analysis_section_timeout),
                min_section_length=int(env_config.analysis_min_section_length),
                temperature=float(env_config.analysis_temperature),
                max_output_tokens=int(env_config.analysis_max_output_tokens),
            ),
            api=ApiConfig(
                gemini_api_key=env_config.gemini_api_key,
                openai_api_key=env_config.openai_api_key,
                anthropic_api_key=env_config.anthropic_api_key,
                rate_limit_delay=float(env_config.api_rate_limit_delay),
                timeout_seconds=float(env_config.api_timeout_seconds),
            ),
            retry=RetryConfig(
                max_attempts=int(env_config.retry_max_attempts),
                initial_delay_seconds=float(env_config.retry_initial_delay),
                backoff_multiplier=float(env_config.retry_backoff_multiplier),
                max_delay_seconds=float(env_config.retry_max_delay),
            ),
            cache=CacheConfig(
                enabled=env_config.cache_enabled.lower() == "true",
                directory=config_service.get_cache_directory(env_config),
                ttl_seconds=int(env_config.cache_ttl_seconds),
                max_size_mb=int(env_config.cache_max_size_mb),
            ),
            export=ExportConfig(
                include_metadata=env_config.export_include_metadata.lower() == "true",
                include_confidence=env_config.export_include_confidence.lower() == "true",
                min_confidence_threshold=float(env_config.export_min_confidence),
                timestamp_format=env_config.export_timestamp_format,
            ),
            prompts_directory=config_service.get_prompts_directory(env_config),
            log_level=env_config.log_level,
        )

    @classmethod
    def for_testing(cls, **overrides: Any) -> "ExtractorConfig":
        """
        Create configuration suitable for testing.

        Provides sensible defaults for tests and allows overriding specific values.
        """
        # Use proper typed construction instead of dictionary unpacking
        extraction = overrides.get(
            "extraction", ExtractionConfig(max_file_size_mb=10, timeout_seconds=5.0)
        )
        analysis = overrides.get(
            "analysis", AnalysisConfig(chunk_size=1000, max_concurrent_sections=1)
        )
        api = overrides.get(
            "api", ApiConfig(gemini_api_key="test-key", rate_limit_delay=0.1)
        )
        retry = overrides.get(
            "retry", RetryConfig(max_attempts=1, initial_delay_seconds=0.1)
        )
        cache = overrides.get("cache", CacheConfig(enabled=False))
        export = overrides.get("export", ExportConfig())
        prompts_directory = overrides.get(
            "prompts_directory", Path("/tmp/test_prompts")
        )
        log_level = overrides.get("log_level", "DEBUG")

        return cls(
            extraction=extraction,
            analysis=analysis,
            api=api,
            retry=retry,
            cache=cache,
            export=export,
            prompts_directory=prompts_directory,
            log_level=log_level,
        )


# Note: ExtractorConfig is now managed by the DI container
# Use container.resolve(ExtractorConfig) to get the instance
# This removes the global state violation
