"""Configuration service for environment variable access."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class EnvironmentConfiguration:
    """Raw environment configuration values."""
    
    # Extraction configuration
    extraction_max_file_size_mb: str
    extraction_timeout_seconds: str
    extraction_normalize_text: str
    extraction_extract_positions: str
    
    # Analysis configuration
    analysis_chunk_size: str
    analysis_chunk_overlap: str
    analysis_max_concurrent: str
    analysis_section_timeout: str
    analysis_min_section_length: str
    analysis_temperature: str
    analysis_max_output_tokens: str
    
    # API configuration
    gemini_api_key: Optional[str]
    openai_api_key: Optional[str]
    anthropic_api_key: Optional[str]
    api_rate_limit_delay: str
    api_timeout_seconds: str
    
    # Retry configuration
    retry_max_attempts: str
    retry_initial_delay: str
    retry_backoff_multiplier: str
    retry_max_delay: str
    
    # Cache configuration
    cache_enabled: str
    cache_dir: Optional[str]
    cache_ttl_seconds: str
    cache_max_size_mb: str
    
    # Export configuration
    export_include_metadata: str
    export_include_confidence: str
    export_min_confidence: str
    export_timestamp_format: str
    
    # General configuration
    prompts_dir: Optional[str]
    log_level: str


class ConfigurationService:
    """Infrastructure service for accessing environment variables."""
    
    def load_from_environment(self) -> EnvironmentConfiguration:
        """Load configuration from environment variables."""
        return EnvironmentConfiguration(
            # Extraction configuration
            extraction_max_file_size_mb=os.getenv("HCI_EXTRACTION_MAX_FILE_SIZE_MB", "50"),
            extraction_timeout_seconds=os.getenv("HCI_EXTRACTION_TIMEOUT_SECONDS", "30.0"),
            extraction_normalize_text=os.getenv("HCI_EXTRACTION_NORMALIZE_TEXT", "true"),
            extraction_extract_positions=os.getenv("HCI_EXTRACTION_EXTRACT_POSITIONS", "false"),
            
            # Analysis configuration
            analysis_chunk_size=os.getenv("HCI_ANALYSIS_CHUNK_SIZE", "10000"),
            analysis_chunk_overlap=os.getenv("HCI_ANALYSIS_CHUNK_OVERLAP", "500"),
            analysis_max_concurrent=os.getenv("HCI_ANALYSIS_MAX_CONCURRENT", "3"),
            analysis_section_timeout=os.getenv("HCI_ANALYSIS_SECTION_TIMEOUT", "60.0"),
            analysis_min_section_length=os.getenv("HCI_ANALYSIS_MIN_SECTION_LENGTH", "50"),
            analysis_temperature=os.getenv("HCI_ANALYSIS_TEMPERATURE", "0.1"),
            analysis_max_output_tokens=os.getenv("HCI_ANALYSIS_MAX_OUTPUT_TOKENS", "4000"),
            
            # API configuration
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            api_rate_limit_delay=os.getenv("HCI_API_RATE_LIMIT_DELAY", "1.0"),
            api_timeout_seconds=os.getenv("HCI_API_TIMEOUT_SECONDS", "30.0"),
            
            # Retry configuration
            retry_max_attempts=os.getenv("HCI_RETRY_MAX_ATTEMPTS", "3"),
            retry_initial_delay=os.getenv("HCI_RETRY_INITIAL_DELAY", "2.0"),
            retry_backoff_multiplier=os.getenv("HCI_RETRY_BACKOFF_MULTIPLIER", "2.0"),
            retry_max_delay=os.getenv("HCI_RETRY_MAX_DELAY", "30.0"),
            
            # Cache configuration
            cache_enabled=os.getenv("HCI_CACHE_ENABLED", "false"),
            cache_dir=os.getenv("HCI_CACHE_DIR"),
            cache_ttl_seconds=os.getenv("HCI_CACHE_TTL_SECONDS", "3600"),
            cache_max_size_mb=os.getenv("HCI_CACHE_MAX_SIZE_MB", "1000"),
            
            # Export configuration
            export_include_metadata=os.getenv("HCI_EXPORT_INCLUDE_METADATA", "true"),
            export_include_confidence=os.getenv("HCI_EXPORT_INCLUDE_CONFIDENCE", "true"),
            export_min_confidence=os.getenv("HCI_EXPORT_MIN_CONFIDENCE", "0.0"),
            export_timestamp_format=os.getenv("HCI_EXPORT_TIMESTAMP_FORMAT", "%Y-%m-%d %H:%M:%S"),
            
            # General configuration
            prompts_dir=os.getenv("HCI_PROMPTS_DIR"),
            log_level=os.getenv("HCI_LOG_LEVEL", "INFO"),
        )
    
    def get_prompts_directory(self, env_config: EnvironmentConfiguration) -> Path:
        """Get the prompts directory path."""
        if env_config.prompts_dir:
            return Path(env_config.prompts_dir)
        else:
            # Default to prompts directory relative to package
            return Path(__file__).parent.parent.parent.parent / "prompts"
    
    def get_cache_directory(self, env_config: EnvironmentConfiguration) -> Optional[Path]:
        """Get the cache directory path if specified."""
        if env_config.cache_dir:
            return Path(env_config.cache_dir)
        return None