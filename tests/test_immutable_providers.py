"""Test that LLM providers maintain immutability."""

import pytest
from unittest.mock import AsyncMock, patch
import asyncio

from hci_extractor.providers.base import LLMProvider
from hci_extractor.providers import GeminiProvider
from hci_extractor.core.models import RateLimitError, LLMError


class TestLLMProvider(LLMProvider):
    """Concrete test implementation of LLMProvider."""
    
    async def analyze_section(self, section_text, section_type, context=None):
        return []
    
    def validate_response(self, response):
        return True
    
    async def _make_api_request(self, prompt, **kwargs):
        return {"elements": []}


def test_base_provider_has_no_mutable_state():
    """Test that base LLMProvider has no mutable attributes."""
    provider = TestLLMProvider()
    
    # Check that provider has no mutable state
    assert not hasattr(provider, 'last_request_time')
    assert not hasattr(provider, '_requests_made')
    assert not hasattr(provider, '_tokens_used')
    
    # Only immutable attributes should exist
    assert hasattr(provider, 'rate_limit_delay')
    assert hasattr(provider, 'max_retries')
    
    # These should be simple values, not mutable containers
    assert isinstance(provider.rate_limit_delay, (int, float))
    assert isinstance(provider.max_retries, int)


def test_gemini_provider_has_no_mutable_state():
    """Test that GeminiProvider has no mutable attributes."""
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
        provider = GeminiProvider()
        
        # Check that provider has no mutable state
        assert not hasattr(provider, 'last_request_time')
        assert not hasattr(provider, '_requests_made')
        assert not hasattr(provider, '_tokens_used')
        assert not hasattr(provider, '_estimated_cost')
        
        # Only immutable attributes should exist
        attributes = vars(provider)
        
        # Check that no lists, dicts, or sets exist as attributes
        for attr_name, attr_value in attributes.items():
            if attr_name.startswith('_'):  # Skip private attributes from parent classes
                continue
            assert not isinstance(attr_value, (list, dict, set)), \
                f"Mutable attribute found: {attr_name} is a {type(attr_value)}"


@pytest.mark.asyncio
async def test_retry_logic_without_state():
    """Test that retry logic works without mutable state."""
    provider = TestLLMProvider(max_retries=3)
    
    # Test successful operation
    mock_operation = AsyncMock(return_value="success")
    result = await provider._retry_with_backoff(mock_operation)
    assert result == "success"
    assert mock_operation.call_count == 1
    
    # Test operation that fails then succeeds
    call_count = 0
    async def failing_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise LLMError("Temporary failure")
        return "success"
    
    result = await provider._retry_with_backoff(failing_operation)
    assert result == "success"
    assert call_count == 3
    
    # Verify the provider still has no mutable state
    assert not hasattr(provider, 'last_request_time')


@pytest.mark.asyncio
async def test_retry_with_rate_limit_error():
    """Test retry logic handles RateLimitError correctly."""
    provider = TestLLMProvider(max_retries=3)
    
    # Test operation that hits rate limit then succeeds
    call_count = 0
    async def rate_limited_operation():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RateLimitError("Rate limit hit", retry_after=0.1)
        return "success"
    
    start_time = asyncio.get_event_loop().time()
    result = await provider._retry_with_backoff(rate_limited_operation)
    duration = asyncio.get_event_loop().time() - start_time
    
    assert result == "success"
    assert call_count == 2
    assert duration >= 0.09  # Should wait at least the retry_after time


@pytest.mark.asyncio
async def test_retry_exhaustion():
    """Test that retries are properly exhausted."""
    provider = TestLLMProvider(max_retries=2)
    
    # Operation that always fails
    async def always_fails():
        raise LLMError("Persistent failure")
    
    with pytest.raises(LLMError) as exc_info:
        await provider._retry_with_backoff(always_fails)
    
    # The last attempt raises the original exception
    assert "Persistent failure" in str(exc_info.value)


def test_rate_limit_delay_setter():
    """Test rate limit delay setter for backwards compatibility."""
    provider = TestLLMProvider()
    
    # Should be able to set rate limit delay
    provider.set_rate_limit_delay(2.0)
    assert provider.get_rate_limit_delay() == 2.0
    
    # Should reject negative values
    with pytest.raises(ValueError):
        provider.set_rate_limit_delay(-1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])