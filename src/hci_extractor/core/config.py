"""
Centralized configuration management for HCI Extractor.

This module provides immutable configuration objects that can be loaded
from environment variables, ensuring all settings are centralized and
easily configurable without code changes.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
    retry: RetryConfig
    cache: CacheConfig
    export: ExportConfig
    prompts_directory: Path
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "ExtractorConfig":
        """
        Create configuration from environment variables.
        
        Environment variables follow the pattern: HCI_<SECTION>_<SETTING>
        For example: HCI_ANALYSIS_CHUNK_SIZE=8000
        """
        # Determine prompts directory
        prompts_dir = os.getenv("HCI_PROMPTS_DIR")
        if prompts_dir:
            prompts_path = Path(prompts_dir)
        else:
            # Default to prompts directory relative to package
            prompts_path = Path(__file__).parent.parent.parent / "prompts"
        
        return cls(
            extraction=ExtractionConfig(
                max_file_size_mb=int(os.getenv("HCI_EXTRACTION_MAX_FILE_SIZE_MB", "50")),
                timeout_seconds=float(os.getenv("HCI_EXTRACTION_TIMEOUT_SECONDS", "30.0")),
                normalize_text=os.getenv("HCI_EXTRACTION_NORMALIZE_TEXT", "true").lower() == "true",
                extract_positions=os.getenv("HCI_EXTRACTION_EXTRACT_POSITIONS", "false").lower() == "true",
            ),
            analysis=AnalysisConfig(
                chunk_size=int(os.getenv("HCI_ANALYSIS_CHUNK_SIZE", "10000")),
                chunk_overlap=int(os.getenv("HCI_ANALYSIS_CHUNK_OVERLAP", "500")),
                max_concurrent_sections=int(os.getenv("HCI_ANALYSIS_MAX_CONCURRENT", "3")),
                section_timeout_seconds=float(os.getenv("HCI_ANALYSIS_SECTION_TIMEOUT", "60.0")),
                min_section_length=int(os.getenv("HCI_ANALYSIS_MIN_SECTION_LENGTH", "50")),
                temperature=float(os.getenv("HCI_ANALYSIS_TEMPERATURE", "0.1")),
                max_output_tokens=int(os.getenv("HCI_ANALYSIS_MAX_OUTPUT_TOKENS", "4000")),
            ),
            retry=RetryConfig(
                max_attempts=int(os.getenv("HCI_RETRY_MAX_ATTEMPTS", "3")),
                initial_delay_seconds=float(os.getenv("HCI_RETRY_INITIAL_DELAY", "2.0")),
                backoff_multiplier=float(os.getenv("HCI_RETRY_BACKOFF_MULTIPLIER", "2.0")),
                max_delay_seconds=float(os.getenv("HCI_RETRY_MAX_DELAY", "30.0")),
            ),
            cache=CacheConfig(
                enabled=os.getenv("HCI_CACHE_ENABLED", "false").lower() == "true",
                directory=Path(os.getenv("HCI_CACHE_DIR")) if os.getenv("HCI_CACHE_DIR") else None,
                ttl_seconds=int(os.getenv("HCI_CACHE_TTL_SECONDS", "3600")),
                max_size_mb=int(os.getenv("HCI_CACHE_MAX_SIZE_MB", "1000")),
            ),
            export=ExportConfig(
                include_metadata=os.getenv("HCI_EXPORT_INCLUDE_METADATA", "true").lower() == "true",
                include_confidence=os.getenv("HCI_EXPORT_INCLUDE_CONFIDENCE", "true").lower() == "true",
                min_confidence_threshold=float(os.getenv("HCI_EXPORT_MIN_CONFIDENCE", "0.0")),
                timestamp_format=os.getenv("HCI_EXPORT_TIMESTAMP_FORMAT", "%Y-%m-%d %H:%M:%S"),
            ),
            prompts_directory=prompts_path,
            log_level=os.getenv("HCI_LOG_LEVEL", "INFO"),
        )
    
    @classmethod
    def for_testing(cls, **overrides) -> "ExtractorConfig":
        """
        Create configuration suitable for testing.
        
        Provides sensible defaults for tests and allows overriding specific values.
        """
        defaults = {
            "extraction": ExtractionConfig(max_file_size_mb=10, timeout_seconds=5.0),
            "analysis": AnalysisConfig(chunk_size=1000, max_concurrent_sections=1),
            "retry": RetryConfig(max_attempts=1, initial_delay_seconds=0.1),
            "cache": CacheConfig(enabled=False),
            "export": ExportConfig(),
            "prompts_directory": Path("/tmp/test_prompts"),
            "log_level": "DEBUG",
        }
        defaults.update(overrides)
        return cls(**defaults)


# Global configuration instance
_config: Optional[ExtractorConfig] = None


def get_config() -> ExtractorConfig:
    """
    Get the global configuration instance.
    
    Creates the configuration from environment on first call.
    """
    global _config
    if _config is None:
        _config = ExtractorConfig.from_env()
    return _config


def set_config(config: ExtractorConfig) -> None:
    """
    Set the global configuration instance.
    
    Useful for testing or overriding configuration.
    """
    global _config
    _config = config