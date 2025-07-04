"""Gemini API provider implementation."""

import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.events import EventBus
from hci_extractor.core.models import LLMError, LLMValidationError, RateLimitError
from hci_extractor.prompts import PromptManager
from hci_extractor.providers.base import LLMProvider
from hci_extractor.core.domain.transformers import ResponseParser
from hci_extractor.utils.retry_handler import RetryPolicy, RetryStrategy

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini API provider for LLM-based text analysis."""

    def __init__(
        self,
        config: ExtractorConfig,
        event_bus: EventBus,
        prompt_manager: Optional[PromptManager] = None,
        model_name: str = "gemini-1.5-flash",
    ):
        """
        Initialize Gemini provider.

        Args:
            config: Configuration object with all settings including API key
            event_bus: Event bus for publishing events
            prompt_manager: PromptManager instance for prompt templates
            model_name: Gemini model to use
        """
        super().__init__(config, event_bus)

        # Initialize PromptManager for this provider
        self.prompt_manager = prompt_manager or PromptManager()

        # Get API key from configuration
        self.api_key = config.api.gemini_api_key
        if not self.api_key:
            raise LLMError(
                "Gemini API key not found in configuration. "
                "Set GEMINI_API_KEY environment variable or provide in config."
            )

        # Configure Gemini
        try:
            genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]
            self.model = genai.GenerativeModel(model_name)  # type: ignore[attr-defined]
        except Exception as e:
            raise LLMError(f"Failed to initialize Gemini model: {e}")

        # Generation configuration optimized for academic analysis
        self.generation_config = genai.types.GenerationConfig(
            temperature=self._config.analysis.temperature,
            max_output_tokens=self._config.analysis.max_output_tokens,
            response_mime_type="application/json",  # Force JSON output
        )

        # Configure Gemini-specific retry policy
        gemini_retry_policy = RetryPolicy(
            max_attempts=self._config.retry.max_attempts,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=1.0,
            backoff_multiplier=2.0,
            max_delay_seconds=60.0,  # Longer max delay for API rate limits
            retryable_exceptions=(LLMError, RateLimitError),
            non_retryable_exceptions=(LLMValidationError, ValueError, TypeError),
        )
        # Note: Retry policy is now handled by the base class

        # Store model name for metrics
        self.model_name = model_name

    async def analyze_section(
        self,
        section_text: str,
        section_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Make API call to analyze section - pure infrastructure operation."""
        if not section_text.strip():
            return []

        try:
            # Build the prompt using PromptManager
            prompt = self.prompt_manager.get_analysis_prompt(
                section_text=section_text,
                section_type=section_type,
                context=context,
                include_examples=True,
            )

            # Make API request with retry logic
            response = await self._retry_with_backoff(self._make_api_request, prompt)

            # Parse response and return raw elements
            # Domain layer will handle validation and transformation
            raw_text = response.get("raw_response", "")
            response_data = ResponseParser.parse_analysis_response(raw_text)

            return response_data.get("elements", [])

        except Exception as e:
            logger.error(f"Gemini API error for section {section_type}: {e}")
            if isinstance(e, (LLMError, RateLimitError, LLMValidationError)):
                raise
            else:
                raise LLMError(f"Gemini API error: {e}")

    async def generate_paper_summary(
        self,
        abstract_text: str,
        introduction_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make API call to generate summary - pure infrastructure operation."""
        if not abstract_text.strip() and not introduction_text.strip():
            return {"summary": "", "confidence": 0.0, "source_sections": []}

        try:
            # Build the summary prompt using PromptManager
            prompt = self.prompt_manager.get_paper_summary_prompt(
                abstract_text=abstract_text,
                introduction_text=introduction_text,
                context=context,
            )

            # Make API request with retry logic
            response = await self._retry_with_backoff(self._make_api_request, prompt)

            # Parse response and return raw summary
            # Domain layer will handle validation and transformation
            raw_text = response.get("raw_response", "")
            summary_data = ResponseParser.parse_summary_response(raw_text)

            return summary_data

        except Exception as e:
            logger.error(f"Gemini API error for summary generation: {e}")
            if isinstance(e, (LLMError, RateLimitError, LLMValidationError)):
                raise
            else:
                raise LLMError(f"Gemini API error: {e}")

    async def _make_api_request(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Make API request to Gemini - pure infrastructure operation."""
        try:
            # Generate content using Gemini
            response = await self.model.generate_content_async(
                prompt, generation_config=self.generation_config, **kwargs
            )

            # Check for successful response
            if not response.text:
                raise LLMError("Empty response from Gemini API")

            # Return raw text - domain layer will handle parsing
            return {"raw_response": response.text}

        except Exception as e:
            # Handle specific Gemini errors
            error_msg = str(e).lower()

            if "quota" in error_msg or "rate limit" in error_msg:
                raise RateLimitError(f"Gemini rate limit exceeded: {e}")
            elif "invalid api key" in error_msg or "authentication" in error_msg:
                raise LLMError(f"Gemini authentication error: {e}")
            elif "blocked" in error_msg or "safety" in error_msg:
                raise LLMError(f"Gemini safety filter triggered: {e}")
            else:
                raise LLMError(f"Gemini API error: {e}")

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Basic response validation - delegates to domain layer."""
        # Minimal validation - just check we got a response
        # Domain layer handles actual validation
        return "raw_response" in response and response["raw_response"]

    def get_usage_stats(self) -> Dict[str, Any]:
        """Return usage statistics.

        This method is deprecated. Use the global metrics collector instead.
        Returns empty stats for backwards compatibility.
        """
        logger.warning(
            "GeminiProvider.get_usage_stats() is deprecated. "
            "Use get_metrics_collector().get_llm_summary() instead."
        )
        return {
            "requests_made": 0,
            "tokens_used": 0,
            "estimated_cost": 0.0,
            "model_name": self.model_name,
        }
