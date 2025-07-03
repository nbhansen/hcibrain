"""Gemini API provider implementation."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from .base import LLMError, LLMProvider, RateLimitError, LLMValidationError
from ..prompts import PromptManager

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini API provider for LLM-based text analysis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
        rate_limit_delay: float = 1.0,
        max_retries: int = 3,
        prompt_manager: Optional[PromptManager] = None,
    ):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Gemini API key (if None, reads from GEMINI_API_KEY env var)
            model_name: Gemini model to use
            rate_limit_delay: Seconds to wait between requests
            max_retries: Maximum number of retry attempts
            prompt_manager: PromptManager instance for prompt templates
        """
        super().__init__(rate_limit_delay, max_retries)
        
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
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            raise LLMError(f"Failed to initialize Gemini model: {e}")

        # Generation configuration optimized for academic analysis
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Low temperature for consistent output
            max_output_tokens=4000,  # Sufficient for element extraction
            response_mime_type="application/json",  # Force JSON output
        )

        # Usage tracking
        self._requests_made = 0
        self._tokens_used = 0
        self._estimated_cost = 0.0

    async def analyze_section(
        self,
        section_text: str,
        section_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Analyze section using Gemini API."""
        if not section_text.strip():
            return []

        try:
            # Build the prompt using PromptManager
            prompt = self.prompt_manager.get_analysis_prompt(
                section_text=section_text,
                section_type=section_type,
                context=context,
                include_examples=True
            )

            # Make API request with retry logic
            response = await self._retry_with_backoff(
                self._make_api_request, prompt
            )

            # Parse and validate response
            elements = self._parse_response(response)

            # Track usage
            self._requests_made += 1
            # Note: Actual token counting would require usage metadata from response
            self._tokens_used += len(section_text) // 4  # Rough estimate

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

    async def _make_api_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Make API request to Gemini."""
        try:
            # Generate content using Gemini
            response = await self.model.generate_content_async(
                prompt, generation_config=self.generation_config, **kwargs
            )

            # Check for successful response
            if not response.text:
                raise LLMError("Empty response from Gemini API")

            # Parse JSON response
            try:
                response_data = json.loads(response.text)
            except json.JSONDecodeError as e:
                raise LLMValidationError(f"Invalid JSON response from Gemini: {e}")

            return response_data

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
                
                # Validate optional hci_contribution_type field
                if "hci_contribution_type" in element:
                    valid_contribution_types = [
                        "knowledge-increasing", "knowledge-contesting", "artifact", 
                        "method", "theory", "synthesis", "unknown"
                    ]
                    if element["hci_contribution_type"] not in valid_contribution_types:
                        raise LLMValidationError(
                            f"Element {i} has invalid hci_contribution_type: {element['hci_contribution_type']}"
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
        """Return usage statistics."""
        # Rough cost estimation for Gemini 1.5 Flash
        # These are example rates - adjust based on actual pricing
        cost_per_1k_tokens = 0.000075  # $0.075 per 1M tokens
        estimated_cost = (self._tokens_used / 1000) * cost_per_1k_tokens

        return {
            "requests_made": self._requests_made,
            "tokens_used": self._tokens_used,
            "estimated_cost": estimated_cost,
            "model_name": "gemini-1.5-flash",
        }