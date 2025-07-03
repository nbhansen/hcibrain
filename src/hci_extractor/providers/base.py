"""Abstract base class for LLM providers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from hci_extractor.core.models import LLMError, LLMValidationError, RateLimitError

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, rate_limit_delay: float = 1.0, max_retries: int = 3):
        """Initialize provider with rate limiting configuration."""
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.last_request_time = 0.0

    @abstractmethod
    async def analyze_section(
        self,
        section_text: str,
        section_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Analyze a paper section and return extracted elements.
        
        Args:
            section_text: The text content of the section
            section_type: Type of section (e.g., 'abstract', 'introduction')
            context: Additional context for analysis (paper metadata, etc.)
            
        Returns:
            List of dictionaries representing extracted elements with fields:
            - element_type: "claim", "finding", or "method"
            - text: Exact verbatim text from the section
            - evidence_type: "quantitative", "qualitative", "theoretical", or "unknown"
            - confidence: Float between 0.0 and 1.0
            
        Raises:
            LLMError: For general API or processing errors
            RateLimitError: When rate limits are exceeded
            LLMValidationError: When response format is invalid
        """
        pass

    @abstractmethod
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate LLM response format and content.
        
        Args:
            response: Raw response from LLM API
            
        Returns:
            True if response is valid, False otherwise
            
        Raises:
            LLMValidationError: If response format is invalid
        """
        pass

    @abstractmethod
    async def _make_api_request(
        self, prompt: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Make the actual API request to the LLM provider.
        
        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Provider-specific parameters
            
        Returns:
            Raw response from the API
            
        Raises:
            LLMError: For API errors
            RateLimitError: For rate limit issues
        """
        pass

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        import time

        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()

    async def _retry_with_backoff(
        self, operation, *args, **kwargs
    ) -> Any:
        """
        Execute operation with exponential backoff retry logic.
        
        Args:
            operation: Async function to execute
            *args, **kwargs: Arguments to pass to operation
            
        Returns:
            Result of successful operation
            
        Raises:
            LLMError: If all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                await self._enforce_rate_limit()
                return await operation(*args, **kwargs)

            except RateLimitError as e:
                last_exception = e
                if e.retry_after:
                    delay = e.retry_after
                else:
                    delay = 2**attempt  # Exponential backoff

                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}), "
                    f"retrying in {delay:.2f} seconds"
                )
                await asyncio.sleep(delay)

            except LLMError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = 2**attempt
                    logger.warning(
                        f"LLM error (attempt {attempt + 1}/{self.max_retries}): {e}, "
                        f"retrying in {delay:.2f} seconds"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        # All retries exhausted
        raise LLMError(f"All {self.max_retries} retries exhausted") from last_exception

    def get_rate_limit_delay(self) -> float:
        """Return the current rate limit delay in seconds."""
        return self.rate_limit_delay

    def set_rate_limit_delay(self, delay: float) -> None:
        """Update the rate limit delay."""
        if delay < 0:
            raise ValueError("Rate limit delay must be non-negative")
        self.rate_limit_delay = delay

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Return usage statistics for the provider.
        
        Returns:
            Dictionary with usage information (requests, tokens, costs, etc.)
        """
        # Base implementation returns empty stats
        # Subclasses should override to provide actual metrics
        return {
            "requests_made": 0,
            "tokens_used": 0,
            "estimated_cost": 0.0,
        }