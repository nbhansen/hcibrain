"""Gemini API provider implementation."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from hci_extractor.core.config import ExtractorConfig, get_config
from hci_extractor.core.metrics import LLMMetricsContext, get_metrics_collector
from hci_extractor.core.models import LLMError, RateLimitError, LLMValidationError
from hci_extractor.prompts import PromptManager
from hci_extractor.providers.base import LLMProvider
from hci_extractor.utils import recover_json, JsonRecoveryOptions

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini API provider for LLM-based text analysis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
        config: Optional[ExtractorConfig] = None,
        rate_limit_delay: Optional[float] = None,
        max_retries: Optional[int] = None,
        prompt_manager: Optional[PromptManager] = None,
    ):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Gemini API key (if None, reads from GEMINI_API_KEY env var)
            model_name: Gemini model to use
            config: Optional configuration object
            rate_limit_delay: Seconds to wait between requests (deprecated, use config)
            max_retries: Maximum number of retry attempts (deprecated, use config)
            prompt_manager: PromptManager instance for prompt templates
        """
        self.config = config or get_config()
        # Support legacy parameters for backwards compatibility
        rate_limit = rate_limit_delay if rate_limit_delay is not None else 1.0  # Will move to config later
        retries = max_retries if max_retries is not None else self.config.retry.max_attempts
        super().__init__(rate_limit, retries)
        
        # Initialize PromptManager for this provider
        self.prompt_manager = prompt_manager or PromptManager()

        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise LLMError(
                "Gemini API key not provided. Set GEMINI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        # Configure Gemini
        try:
            genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]
            self.model = genai.GenerativeModel(model_name)  # type: ignore[attr-defined]
        except Exception as e:
            raise LLMError(f"Failed to initialize Gemini model: {e}")

        # Generation configuration optimized for academic analysis
        self.generation_config = genai.types.GenerationConfig(
            temperature=self.config.analysis.temperature,
            max_output_tokens=self.config.analysis.max_output_tokens,
            response_mime_type="application/json",  # Force JSON output
        )
        
        # Store model name for metrics
        self.model_name = model_name

    async def analyze_section(
        self,
        section_text: str,
        section_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Analyze section using Gemini API."""
        if not section_text.strip():
            return []

        # Extract paper_id from context if available
        paper_id = context.get("paper_id") if context else None
        
        # Use metrics context manager for tracking
        with LLMMetricsContext(
            provider="gemini",
            model=self.model_name,
            operation="analyze_section",
            paper_id=paper_id,
            section_type=section_type
        ) as metrics:
            try:
                # Build the prompt using PromptManager
                prompt = self.prompt_manager.get_analysis_prompt(
                    section_text=section_text,
                    section_type=section_type,
                    context=context,
                    include_examples=True
                )
                
                # Estimate input tokens (rough approximation)
                metrics.tokens_input = len(prompt) // 4

                # Make API request with retry logic
                response = await self._retry_with_backoff(
                    self._make_api_request, prompt
                )

                # Parse and validate response
                elements = self._parse_response(response)
                
                # Estimate output tokens
                response_text = json.dumps(response) if isinstance(response, dict) else str(response)
                metrics.tokens_output = len(response_text) // 4

                logger.info(
                    f"Analyzed {section_type} section: {len(elements)} elements extracted"
                )

                return elements

            except Exception as e:
                logger.error(f"Error analyzing section {section_type}: {e}")
                if isinstance(e, (LLMError, RateLimitError, LLMValidationError)):
                    raise
                else:
                    raise LLMError(f"Unexpected error in section analysis: {e}")

    async def _make_api_request(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Make API request to Gemini."""
        try:
            # Generate content using Gemini
            response = await self.model.generate_content_async(
                prompt, generation_config=self.generation_config, **kwargs
            )

            # Check for successful response
            if not response.text:
                raise LLMError("Empty response from Gemini API")

            # Parse JSON response with recovery attempts
            try:
                response_data = json.loads(response.text)
            except json.JSONDecodeError as e:
                # Try to recover from common JSON issues
                recovery_options = JsonRecoveryOptions(
                    strategies=['truncation', 'array_completion'],
                    expected_structure={'elements': list}
                )
                recovery_result = recover_json(response.text, recovery_options)
                
                if recovery_result.success:
                    logger.warning(f"Recovered from JSON error using {recovery_result.strategy_used}: {e}")
                    response_data = recovery_result.recovered_data
                else:
                    raise LLMValidationError(f"Invalid JSON response from Gemini: {e}")

            return response_data  # type: ignore[no-any-return]

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
        """Validate Gemini response format."""
        try:
            # Check for required top-level structure
            if not isinstance(response, dict):
                raise LLMValidationError("Response must be a dictionary")

            if "elements" not in response:
                raise LLMValidationError("Response must contain 'elements' field")

            elements = response["elements"]
            if not isinstance(elements, list):
                raise LLMValidationError("Elements must be a list")

            # Validate each element
            for i, element in enumerate(elements):
                if not isinstance(element, dict):
                    raise LLMValidationError(f"Element {i} must be a dictionary")

                # Check required fields
                required_fields = [
                    "element_type",
                    "text",
                    "evidence_type",
                    "confidence",
                ]
                for field in required_fields:
                    if field not in element:
                        raise LLMValidationError(
                            f"Element {i} missing required field: {field}"
                        )

                # Validate field values
                if element["element_type"] not in ["claim", "finding", "method", "artifact"]:
                    raise LLMValidationError(
                        f"Element {i} has invalid element_type: {element['element_type']}"
                    )

                if element["evidence_type"] not in [
                    "quantitative",
                    "qualitative",
                    "theoretical",
                    "mixed",
                    "unknown",
                ]:
                    raise LLMValidationError(
                        f"Element {i} has invalid evidence_type: {element['evidence_type']}"
                    )

                if not isinstance(element["confidence"], (int, float)):
                    raise LLMValidationError(
                        f"Element {i} confidence must be numeric"
                    )

                if not 0.0 <= element["confidence"] <= 1.0:
                    raise LLMValidationError(
                        f"Element {i} confidence must be between 0.0 and 1.0"
                    )

                if not isinstance(element["text"], str) or not element["text"].strip():
                    raise LLMValidationError(
                        f"Element {i} text must be non-empty string"
                    )
                

            return True

        except LLMValidationError:
            raise
        except Exception as e:
            raise LLMValidationError(f"Unexpected validation error: {e}")


    def _parse_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse and validate Gemini response."""
        # Validate response format
        self.validate_response(response)

        # Extract elements
        elements = response["elements"]

        # Additional processing/cleaning if needed
        processed_elements = []
        for element in elements:
            # Clean up the element
            cleaned_element = {
                "element_type": element["element_type"],
                "text": element["text"].strip(),
                "evidence_type": element["evidence_type"],
                "confidence": float(element["confidence"]),
            }

            # Skip empty or very short extractions
            if len(cleaned_element["text"]) < 10:
                logger.debug(f"Skipping short extraction: {cleaned_element['text']}")
                continue

            processed_elements.append(cleaned_element)

        return processed_elements

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