"""Provider-specific configuration interfaces following hexagonal architecture."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from hci_extractor.core.config import ExtractorConfig


@dataclass(frozen=True)
class LLMProviderConfig:
    """Configuration interface for LLM providers."""

    api_key: Optional[str]
    temperature: float
    max_output_tokens: int
    max_attempts: int
    timeout_seconds: float
    rate_limit_delay: float


class ProviderConfigurationPort(ABC):
    """Port for accessing provider-specific configuration."""

    @abstractmethod
    def get_gemini_config(self) -> LLMProviderConfig:
        """Get configuration for Gemini provider."""

    @abstractmethod
    def get_openai_config(self) -> LLMProviderConfig:
        """Get configuration for OpenAI provider."""

    @abstractmethod
    def get_anthropic_config(self) -> LLMProviderConfig:
        """Get configuration for Anthropic provider."""


class ExtractorConfigurationAdapter(ProviderConfigurationPort):
    """Adapter that converts ExtractorConfig to provider-specific configurations."""

    def __init__(self, extractor_config: "ExtractorConfig") -> None:
        self._config = extractor_config

    def get_gemini_config(self) -> LLMProviderConfig:
        """Get configuration for Gemini provider."""
        return LLMProviderConfig(
            api_key=self._config.api.gemini_api_key,
            temperature=self._config.analysis.temperature,
            max_output_tokens=self._config.analysis.max_output_tokens,
            max_attempts=self._config.retry.max_attempts,
            timeout_seconds=self._config.api.timeout_seconds,
            rate_limit_delay=self._config.api.rate_limit_delay,
        )

    def get_openai_config(self) -> LLMProviderConfig:
        """Get configuration for OpenAI provider."""
        return LLMProviderConfig(
            api_key=self._config.api.openai_api_key,
            temperature=self._config.analysis.temperature,
            max_output_tokens=self._config.analysis.max_output_tokens,
            max_attempts=self._config.retry.max_attempts,
            timeout_seconds=self._config.api.timeout_seconds,
            rate_limit_delay=self._config.api.rate_limit_delay,
        )

    def get_anthropic_config(self) -> LLMProviderConfig:
        """Get configuration for Anthropic provider."""
        return LLMProviderConfig(
            api_key=self._config.api.anthropic_api_key,
            temperature=self._config.analysis.temperature,
            max_output_tokens=self._config.analysis.max_output_tokens,
            max_attempts=self._config.retry.max_attempts,
            timeout_seconds=self._config.api.timeout_seconds,
            rate_limit_delay=self._config.api.rate_limit_delay,
        )
