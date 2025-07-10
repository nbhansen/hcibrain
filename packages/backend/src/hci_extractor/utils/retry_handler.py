"""
Unified retry handler for resilient operation execution.

This module provides a flexible, configurable retry mechanism that can handle
various failure scenarios with different backoff strategies, timeout support,
and event integration.

Example usage:
    >>> from hci_extractor.utils.retry_handler import RetryHandler, RetryConfig
    >>>
    >>> async def flaky_operation():
    ...     # Some operation that might fail
    ...     return "success"
    >>>
    >>> handler = RetryHandler()
    >>> result = await handler.execute_with_retry(flaky_operation)
    >>> print(result.success, result.value)
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Optional,
    Protocol,
    Tuple,
    Type,
    runtime_checkable,
)

from hci_extractor.core.config import RetryConfig as ConfigRetryConfig
from hci_extractor.core.events import (
    EventBus,
    RetryAttempted,
    RetryExhausted,
    RetrySucceeded,
)
from hci_extractor.core.models import LLMError, RateLimitError

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Available retry strategies."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


# Retry events are defined in hci_extractor.core.events


@runtime_checkable
class RetryableError(Protocol):
    """Protocol for errors that can indicate specific retry behavior."""

    @property
    def retry_after(self) -> Optional[float]:
        """Suggested delay before retry, if available."""
        ...


@dataclass(frozen=True)
class RetryPolicy:
    """Immutable retry policy configuration."""

    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    initial_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 30.0
    timeout_seconds: Optional[float] = None
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()

    @classmethod
    def from_config(cls, config: Optional[ConfigRetryConfig] = None) -> "RetryPolicy":
        """Create retry policy from configuration."""
        if config is None:
            # Use default values when no config is provided
            from hci_extractor.core.config import RetryConfig

            config = RetryConfig(
                max_attempts=3,
                initial_delay_seconds=1.0,
                backoff_multiplier=2.0,
                max_delay_seconds=60.0,
            )

        return cls(
            max_attempts=config.max_attempts,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=config.initial_delay_seconds,
            backoff_multiplier=config.backoff_multiplier,
            max_delay_seconds=config.max_delay_seconds,
            # Default retryable exceptions for LLM operations
            retryable_exceptions=(LLMError, RateLimitError, asyncio.TimeoutError),
            non_retryable_exceptions=(ValueError, TypeError),
        )


@dataclass(frozen=True)
class RetryResult:
    """Immutable result of a retry operation."""

    success: bool
    value: Any = None
    error: Optional[Exception] = None
    attempts_made: int = 0
    total_duration_seconds: float = 0.0
    strategy_used: Optional[RetryStrategy] = None


class RetryHandler:
    """
    Unified retry handler with configurable strategies and event integration.

    This class is immutable - configuration is passed at construction time
    and cannot be changed afterwards.
    """

    def __init__(
        self,
        policy: Optional[RetryPolicy] = None,
        operation_name: Optional[str] = None,
        publish_events: bool = True,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize retry handler.

        Args:
            policy: Retry policy to use (defaults to policy from config)
            operation_name: Name for logging and events
            publish_events: Whether to publish retry events
            event_bus: Event bus for publishing events (required if publish_events=True)
        """
        self._policy = policy or RetryPolicy.from_config()
        self._operation_name = operation_name or "unknown_operation"
        self._publish_events = publish_events

        if publish_events and event_bus is None:
            raise ValueError("EventBus is required when publish_events=True")
        self._event_bus = event_bus if publish_events else None

    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> RetryResult:
        """
        Execute an async operation with retry logic.

        Args:
            operation: Async callable to execute
            *args, **kwargs: Arguments to pass to operation

        Returns:
            RetryResult with success status and value or error
        """
        start_time = time.time()
        last_exception: Optional[Exception] = None

        for attempt in range(self._policy.max_attempts):
            try:
                # Apply timeout if configured
                if self._policy.timeout_seconds:
                    result = await asyncio.wait_for(
                        operation(*args, **kwargs),
                        timeout=self._policy.timeout_seconds,
                    )
                else:
                    result = await operation(*args, **kwargs)

                # Success!
                duration = time.time() - start_time

                if self._publish_events and self._event_bus and attempt > 0:
                    self._event_bus.publish(
                        RetrySucceeded(
                            operation_name=self._operation_name,
                            successful_attempt=attempt + 1,
                            total_duration_seconds=duration,
                        ),
                    )

                return RetryResult(
                    success=True,
                    value=result,
                    attempts_made=attempt + 1,
                    total_duration_seconds=duration,
                    strategy_used=self._policy.strategy,
                )

            except Exception as e:
                last_exception = e

                # Check if this exception should not be retried
                if self._should_not_retry(e):
                    logger.info(f"Non-retryable exception: {type(e).__name__}: {e}")
                    break

                # Don't retry on last attempt
                if attempt >= self._policy.max_attempts - 1:
                    break

                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, e)

                # Publish retry event
                if self._publish_events and self._event_bus:
                    self._event_bus.publish(
                        RetryAttempted(
                            operation_name=self._operation_name,
                            attempt_number=attempt + 1,
                            max_attempts=self._policy.max_attempts,
                            delay_seconds=delay,
                            error_type=type(e).__name__,
                            error_message=str(e),
                        ),
                    )

                logger.warning(
                    f"Attempt {attempt + 1}/{self._policy.max_attempts} failed for "
                    f"{self._operation_name}: {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f}s",
                )

                await asyncio.sleep(delay)

        # All retries exhausted
        duration = time.time() - start_time
        actual_attempts = attempt + 1

        if self._publish_events and self._event_bus:
            self._event_bus.publish(
                RetryExhausted(
                    operation_name=self._operation_name,
                    total_attempts=actual_attempts,
                    total_duration_seconds=duration,
                    final_error_type=(
                        type(last_exception).__name__ if last_exception else "Unknown"
                    ),
                    final_error_message=(
                        str(last_exception) if last_exception else "Unknown error"
                    ),
                ),
            )

        return RetryResult(
            success=False,
            error=last_exception,
            attempts_made=actual_attempts,
            total_duration_seconds=duration,
            strategy_used=self._policy.strategy,
        )

    def execute_with_retry_sync(
        self,
        operation: Callable[[], Any],
        *args: Any,
        **kwargs: Any,
    ) -> RetryResult:
        """
        Execute a synchronous operation with retry logic.

        Args:
            operation: Callable to execute
            *args, **kwargs: Arguments to pass to operation

        Returns:
            RetryResult with success status and value or error
        """
        start_time = time.time()
        last_exception: Optional[Exception] = None

        for attempt in range(self._policy.max_attempts):
            try:
                result = operation(*args, **kwargs)

                # Success!
                duration = time.time() - start_time

                return RetryResult(
                    success=True,
                    value=result,
                    attempts_made=attempt + 1,
                    total_duration_seconds=duration,
                    strategy_used=self._policy.strategy,
                )

            except Exception as e:
                last_exception = e

                # Check if this exception should not be retried
                if self._should_not_retry(e):
                    break

                # Don't retry on last attempt
                if attempt >= self._policy.max_attempts - 1:
                    break

                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, e)

                logger.warning(
                    f"Attempt {attempt + 1}/{self._policy.max_attempts} failed for "
                    f"{self._operation_name}: {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f}s",
                )

                time.sleep(delay)

        # All retries exhausted
        duration = time.time() - start_time
        actual_attempts = attempt + 1

        return RetryResult(
            success=False,
            error=last_exception,
            attempts_made=actual_attempts,
            total_duration_seconds=duration,
            strategy_used=self._policy.strategy,
        )

    def _should_not_retry(self, exception: Exception) -> bool:
        """Check if an exception should not be retried."""
        # Check non-retryable exceptions first (takes precedence)
        if self._policy.non_retryable_exceptions and isinstance(
            exception,
            self._policy.non_retryable_exceptions,
        ):
            return True

        # Check if it's in the retryable exceptions
        return bool(
            self._policy.retryable_exceptions
            and not isinstance(exception, self._policy.retryable_exceptions),
        )

    def _calculate_delay(self, attempt: int, exception: Exception) -> float:
        """Calculate delay before next retry attempt."""
        # Check if exception suggests a specific delay
        if isinstance(exception, RetryableError) and exception.retry_after:
            return min(exception.retry_after, self._policy.max_delay_seconds)

        # Apply strategy-specific delay calculation
        if self._policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self._policy.initial_delay_seconds * (
                self._policy.backoff_multiplier**attempt
            )
        elif self._policy.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self._policy.initial_delay_seconds * (attempt + 1)
        elif self._policy.strategy == RetryStrategy.FIXED_DELAY:
            delay = self._policy.initial_delay_seconds
        else:  # IMMEDIATE
            delay = 0.0

        return min(delay, self._policy.max_delay_seconds)


# Convenience functions for common use cases


async def retry_async(
    operation: Callable[[], Awaitable[Any]],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    operation_name: str = "async_operation",
) -> RetryResult:
    """
    Convenience function for simple async retry.

    Args:
        operation: Async operation to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries
        operation_name: Name for logging

    Returns:
        RetryResult with outcome
    """
    policy = RetryPolicy(max_attempts=max_attempts, initial_delay_seconds=initial_delay)
    handler = RetryHandler(policy=policy, operation_name=operation_name)
    return await handler.execute_with_retry(operation)


def retry_sync(
    operation: Callable[[], Any],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    operation_name: str = "sync_operation",
) -> RetryResult:
    """
    Convenience function for simple synchronous retry.

    Args:
        operation: Operation to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries
        operation_name: Name for logging

    Returns:
        RetryResult with outcome
    """
    policy = RetryPolicy(max_attempts=max_attempts, initial_delay_seconds=initial_delay)
    handler = RetryHandler(policy=policy, operation_name=operation_name)
    return handler.execute_with_retry_sync(operation)
