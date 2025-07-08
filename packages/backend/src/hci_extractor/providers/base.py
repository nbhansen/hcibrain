"""Abstract base class for LLM providers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from hci_extractor.core.events import EventBus
from hci_extractor.core.models import LLMError, LLMValidationError, RateLimitError
from hci_extractor.providers.provider_config import LLMProviderConfig
from hci_extractor.utils.retry_handler import RetryHandler, RetryPolicy, RetryStrategy

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(
        self,
        provider_config: LLMProviderConfig,
        event_bus: EventBus,
        retry_handler: Optional[RetryHandler] = None,
    ):
        """Initialize provider with injected dependencies.

        Args:
            provider_config: Provider-specific configuration
            event_bus: Event bus for publishing events
            retry_handler: Optional retry handler (will create default if not provided)
        """
        self._provider_config = provider_config
        self._event_bus = event_bus

        # Create retry handler if not provided
        if retry_handler is None:
            retry_policy = RetryPolicy(
                max_attempts=provider_config.max_attempts,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                initial_delay_seconds=1.0,
                backoff_multiplier=2.0,
                max_delay_seconds=30.0,
                retryable_exceptions=(LLMError, RateLimitError, asyncio.TimeoutError),
                non_retryable_exceptions=(LLMValidationError, ValueError, TypeError),
            )
            self._retry_handler = RetryHandler(
                policy=retry_policy,
                operation_name=f"{self.__class__.__name__}_api_request",
                publish_events=True,
                event_bus=event_bus,
            )
        else:
            self._retry_handler = retry_handler

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

    @abstractmethod
    async def generate_paper_summary(
        self,
        abstract_text: str,
        introduction_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate paper summary from abstract and introduction sections.

        Args:
            abstract_text: The text content of the abstract section
            introduction_text: The text content of the introduction section
            context: Additional context for analysis (paper metadata, etc.)

        Returns:
            Dictionary containing:
            - summary: Concise 2-3 sentence summary of the paper
            - confidence: Float between 0.0 and 1.0
            - source_sections: List of sections used for summary

        Raises:
            LLMError: For general API or processing errors
            RateLimitError: When rate limits are exceeded
            LLMValidationError: When response format is invalid
        """

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

    @abstractmethod
    async def _make_api_request(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
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

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests.

        Deprecated: This method is kept for backwards compatibility but does nothing.
        Rate limiting should be handled by the specific provider implementation.
        """
        logger.debug("Rate limiting is deprecated in base LLMProvider")

    async def execute_with_retry(
        self, operation: Any, *args: Any, **kwargs: Any,
    ) -> Any:
        """Execute operation with retry logic using the unified RetryHandler.

        This is the preferred method for new code. Use _retry_with_backoff for \
compatibility.

        Args:
            operation: Async function to execute
            *args, **kwargs: Arguments to pass to operation

        Returns:
            Result of successful operation

        Raises:
            LLMError: If all retries are exhausted
        """
        return await self._retry_with_backoff(operation, *args, **kwargs)

    async def _retry_with_backoff(
        self, operation: Any, *args: Any, **kwargs: Any,
    ) -> Any:
        """
        Execute operation with unified retry handler logic.

        This method maintains backward compatibility while using the new RetryHandler.

        Args:
            operation: Async function to execute
            *args, **kwargs: Arguments to pass to operation

        Returns:
            Result of successful operation

        Raises:
            LLMError: If all retries are exhausted
        """

        # Use the unified retry handler
        async def operation_wrapper() -> Any:
            return await operation(*args, **kwargs)

        result = await self._retry_handler.execute_with_retry(operation_wrapper)

        if result.success:
            return result.value
        # Convert retry handler error to LLMError for backward compatibility
        if result.error:
            raise LLMError(
                f"LLM operation failed after {result.attempts_made} attempts",
            ) from result.error
        raise LLMError(
            f"LLM operation failed after {result.attempts_made} attempts",
        )

    def get_rate_limit_delay(self) -> float:
        """Get the current rate limit delay from configuration."""
        return self._provider_config.rate_limit_delay

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

    def get_retry_policy(self) -> RetryPolicy:
        """Get the current retry policy for this provider."""
        return self._retry_handler._policy
