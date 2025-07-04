"""Test unified retry handler."""

import asyncio
import time

import pytest

from hci_extractor.core.events import (
    EventBus,
    RetryAttempted,
    RetryExhausted,
    RetrySucceeded,
)
from hci_extractor.core.models import LLMError, RateLimitError
from hci_extractor.utils import (
    RetryHandler,
    RetryPolicy,
    RetryStrategy,
    retry_async,
    retry_sync,
)


class TestRetryPolicy:
    """Test retry policy configuration."""

    def test_default_policy(self):
        """Test default retry policy."""
        policy = RetryPolicy()

        assert policy.max_attempts == 3
        assert policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert policy.initial_delay_seconds == 1.0
        assert policy.backoff_multiplier == 2.0
        assert policy.max_delay_seconds == 30.0
        assert policy.timeout_seconds is None

    def test_policy_from_config(self):
        """Test creating policy from configuration."""
        policy = RetryPolicy.from_config()

        # Should use values from get_config().retry
        assert policy.max_attempts >= 1
        assert policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert LLMError in policy.retryable_exceptions
        assert RateLimitError in policy.retryable_exceptions
        assert ValueError in policy.non_retryable_exceptions

    def test_policy_immutability(self):
        """Test that retry policy is immutable."""
        policy = RetryPolicy(max_attempts=5)

        # Should not be able to modify
        with pytest.raises(Exception):  # dataclass frozen error
            policy.max_attempts = 10


class TestRetryHandler:
    """Test retry handler functionality."""

    @pytest.fixture
    def simple_policy(self):
        """Create a simple retry policy for testing."""
        return RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.1,  # Fast for testing
            backoff_multiplier=2.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        )

    @pytest.fixture
    def event_collector(self):
        """Create event collector for testing."""
        events = []

        class EventCollector:
            def handle(self, event):
                events.append(event)

            def get_events(self):
                return events

            def clear(self):
                events.clear()

        collector = EventCollector()
        event_bus = EventBus()  # Create a fresh EventBus for testing
        event_bus.subscribe_all(collector)

        yield collector

        event_bus.clear()

    @pytest.mark.asyncio
    async def test_successful_operation_no_retry(self, simple_policy):
        """Test operation that succeeds on first attempt."""
        event_bus = EventBus()
        handler = RetryHandler(policy=simple_policy, operation_name="test_op", event_bus=event_bus)

        async def successful_operation():
            return "success"

        result = await handler.execute_with_retry(successful_operation)

        assert result.success
        assert result.value == "success"
        assert result.attempts_made == 1
        assert result.error is None
        assert result.strategy_used == RetryStrategy.EXPONENTIAL_BACKOFF

    @pytest.mark.asyncio
    async def test_operation_succeeds_after_retries(
        self, simple_policy, event_collector
    ):
        """Test operation that fails then succeeds."""
        event_bus = EventBus()
        handler = RetryHandler(policy=simple_policy, operation_name="test_retry", event_bus=event_bus)

        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LLMError(f"Failure {call_count}")
            return "success"

        start_time = time.time()
        result = await handler.execute_with_retry(flaky_operation)
        duration = time.time() - start_time

        assert result.success
        assert result.value == "success"
        assert result.attempts_made == 3
        assert result.error is None
        assert duration >= 0.3  # Should have waited for retries

        # Check events
        events = event_collector.get_events()
        retry_attempted_events = [e for e in events if isinstance(e, RetryAttempted)]
        retry_succeeded_events = [e for e in events if isinstance(e, RetrySucceeded)]

        assert len(retry_attempted_events) == 2  # First two attempts failed
        assert len(retry_succeeded_events) == 1

        assert retry_attempted_events[0].attempt_number == 1
        assert retry_attempted_events[1].attempt_number == 2
        assert retry_succeeded_events[0].successful_attempt == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self, simple_policy, event_collector):
        """Test operation that always fails."""
        event_bus = EventBus()
        handler = RetryHandler(policy=simple_policy, operation_name="always_fails", event_bus=event_bus)

        async def always_fails():
            raise LLMError("Persistent failure")

        result = await handler.execute_with_retry(always_fails)

        assert not result.success
        assert result.value is None
        assert isinstance(result.error, LLMError)
        assert result.attempts_made == 3

        # Check events
        events = event_collector.get_events()
        retry_attempted_events = [e for e in events if isinstance(e, RetryAttempted)]
        retry_exhausted_events = [e for e in events if isinstance(e, RetryExhausted)]

        assert len(retry_attempted_events) == 2  # Two retry attempts
        assert len(retry_exhausted_events) == 1

        assert retry_exhausted_events[0].total_attempts == 3
        assert retry_exhausted_events[0].final_error_type == "LLMError"

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self, simple_policy):
        """Test that non-retryable exceptions are not retried."""
        policy = RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.1,
            retryable_exceptions=(LLMError,),  # Only LLMError should be retried
            non_retryable_exceptions=(ValueError,),
        )
        event_bus = EventBus()
        handler = RetryHandler(policy=policy, operation_name="non_retryable", event_bus=event_bus)

        async def raises_value_error():
            raise ValueError("This should not be retried")

        result = await handler.execute_with_retry(raises_value_error)

        assert not result.success
        assert isinstance(result.error, ValueError)
        assert result.attempts_made == 1  # Should not retry

    @pytest.mark.asyncio
    async def test_rate_limit_error_with_retry_after(self, simple_policy):
        """Test rate limit error with suggested retry delay."""

        # Create a rate limit error with retry_after property
        class TestRateLimitError(RateLimitError):
            def __init__(self, message, retry_after=None):
                super().__init__(message)
                self.retry_after = retry_after

        event_bus = EventBus()
        handler = RetryHandler(policy=simple_policy, operation_name="rate_limited", event_bus=event_bus)

        call_count = 0

        async def rate_limited_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TestRateLimitError("Rate limited", retry_after=0.2)
            return "success"

        start_time = time.time()
        result = await handler.execute_with_retry(rate_limited_operation)
        duration = time.time() - start_time

        assert result.success
        assert result.value == "success"
        assert result.attempts_made == 2
        assert duration >= 0.2  # Should respect retry_after

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling."""
        policy = RetryPolicy(
            max_attempts=2, timeout_seconds=0.1, initial_delay_seconds=0.05
        )
        event_bus = EventBus()
        handler = RetryHandler(policy=policy, operation_name="timeout_test", event_bus=event_bus)

        async def slow_operation():
            await asyncio.sleep(0.2)  # Longer than timeout
            return "success"

        result = await handler.execute_with_retry(slow_operation)

        assert not result.success
        assert isinstance(result.error, asyncio.TimeoutError)
        assert result.attempts_made == 2  # Should retry timeout errors

    def test_synchronous_retry(self, simple_policy):
        """Test synchronous retry functionality."""
        event_bus = EventBus()
        handler = RetryHandler(policy=simple_policy, operation_name="sync_test", event_bus=event_bus)

        call_count = 0

        def flaky_sync_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMError("Sync failure")
            return "sync_success"

        result = handler.execute_with_retry_sync(flaky_sync_operation)

        assert result.success
        assert result.value == "sync_success"
        assert result.attempts_made == 2


class TestRetryStrategies:
    """Test different retry strategies."""

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        policy = RetryPolicy(
            max_attempts=4,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=0.1,
            backoff_multiplier=2.0,
        )
        event_bus = EventBus()
        handler = RetryHandler(policy=policy, operation_name="exponential_test", event_bus=event_bus)

        # Test delay calculation directly
        exception = LLMError("Test error")

        delay0 = handler._calculate_delay(0, exception)
        delay1 = handler._calculate_delay(1, exception)
        delay2 = handler._calculate_delay(2, exception)

        # Check exponential progression: 0.1, 0.2, 0.4
        assert abs(delay0 - 0.1) < 0.01
        assert abs(delay1 - 0.2) < 0.01
        assert abs(delay2 - 0.4) < 0.01

    def test_linear_backoff_calculation(self):
        """Test linear backoff delay calculation."""
        policy = RetryPolicy(
            max_attempts=4,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            initial_delay_seconds=0.1,
        )
        event_bus = EventBus()
        handler = RetryHandler(policy=policy, operation_name="linear_test", event_bus=event_bus)

        exception = LLMError("Test error")

        delay0 = handler._calculate_delay(0, exception)
        delay1 = handler._calculate_delay(1, exception)
        delay2 = handler._calculate_delay(2, exception)

        # Check linear progression: 0.1, 0.2, 0.3
        assert abs(delay0 - 0.1) < 0.01
        assert abs(delay1 - 0.2) < 0.01
        assert abs(delay2 - 0.3) < 0.01

    def test_fixed_delay_calculation(self):
        """Test fixed delay calculation."""
        policy = RetryPolicy(
            max_attempts=4,
            strategy=RetryStrategy.FIXED_DELAY,
            initial_delay_seconds=0.15,
        )
        event_bus = EventBus()
        handler = RetryHandler(policy=policy, operation_name="fixed_test", event_bus=event_bus)

        exception = LLMError("Test error")

        delay0 = handler._calculate_delay(0, exception)
        delay1 = handler._calculate_delay(1, exception)
        delay2 = handler._calculate_delay(2, exception)

        # All delays should be the same
        assert abs(delay0 - 0.15) < 0.01
        assert abs(delay1 - 0.15) < 0.01
        assert abs(delay2 - 0.15) < 0.01

    def test_max_delay_limit_calculation(self):
        """Test that delays respect max_delay_seconds."""
        policy = RetryPolicy(
            max_attempts=5,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=1.0,
            backoff_multiplier=10.0,  # Very aggressive
            max_delay_seconds=2.0,
        )
        event_bus = EventBus()
        handler = RetryHandler(policy=policy, operation_name="max_delay_test", event_bus=event_bus)

        exception = LLMError("Test error")

        # Calculate delays for several attempts
        delays = [handler._calculate_delay(i, exception) for i in range(4)]

        # No delay should exceed max_delay_seconds
        assert all(delay <= 2.0 for delay in delays)

        # First delay should be normal, later ones should be capped
        assert abs(delays[0] - 1.0) < 0.01  # 1.0
        assert delays[1] <= 2.0  # Would be 10.0 without cap
        assert delays[2] <= 2.0  # Would be 100.0 without cap


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_retry_async_convenience(self):
        """Test retry_async convenience function."""
        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMError("Flaky")
            return "success"

        result = await retry_async(
            flaky_operation,
            max_attempts=3,
            initial_delay=0.05,
            operation_name="convenience_test",
        )

        assert result.success
        assert result.value == "success"
        assert result.attempts_made == 2

    def test_retry_sync_convenience(self):
        """Test retry_sync convenience function."""
        call_count = 0

        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMError("Flaky")
            return "success"

        result = retry_sync(
            flaky_operation,
            max_attempts=3,
            initial_delay=0.05,
            operation_name="sync_convenience_test",
        )

        assert result.success
        assert result.value == "success"
        assert result.attempts_made == 2


class TestEventIntegration:
    """Test event system integration."""

    @pytest.fixture
    def event_collector(self):
        """Create event collector for testing."""
        events = []

        class EventCollector:
            def handle(self, event):
                events.append(event)

            def get_events_by_type(self, event_type):
                return [e for e in events if isinstance(e, event_type)]

            def clear(self):
                events.clear()

        collector = EventCollector()
        event_bus = EventBus()  # Create a fresh EventBus for testing
        event_bus.subscribe_all(collector)

        yield collector

        event_bus.clear()

    @pytest.mark.asyncio
    async def test_events_disabled(self):
        """Test that events can be disabled."""
        policy = RetryPolicy(max_attempts=2, initial_delay_seconds=0.01)
        handler = RetryHandler(
            policy=policy, operation_name="no_events", publish_events=False
        )

        async def always_fails():
            raise LLMError("Always fails")

        # Should not publish any events
        await handler.execute_with_retry(always_fails)

        # No way to easily test this without mocking the event bus
        # The test passes if no errors are raised

    @pytest.mark.asyncio
    async def test_event_details(self, event_collector):
        """Test detailed event information."""
        policy = RetryPolicy(max_attempts=3, initial_delay_seconds=0.05)
        event_bus = EventBus()
        handler = RetryHandler(policy=policy, operation_name="detailed_events", event_bus=event_bus)

        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LLMError("First failure")
            elif call_count == 2:
                raise RateLimitError("Rate limited")
            return "success"

        result = await handler.execute_with_retry(flaky_operation)

        assert result.success

        # Check event details
        retry_events = event_collector.get_events_by_type(RetryAttempted)
        success_events = event_collector.get_events_by_type(RetrySucceeded)

        assert len(retry_events) == 2
        assert len(success_events) == 1

        # First retry event
        assert retry_events[0].operation_name == "detailed_events"
        assert retry_events[0].attempt_number == 1
        assert retry_events[0].max_attempts == 3
        assert retry_events[0].error_type == "LLMError"
        assert "First failure" in retry_events[0].error_message

        # Second retry event
        assert retry_events[1].error_type == "RateLimitError"
        assert "Rate limited" in retry_events[1].error_message

        # Success event
        assert success_events[0].successful_attempt == 3
        assert success_events[0].total_duration_seconds > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
