"""Test metrics collection integration."""

from unittest.mock import patch

import pytest

from hci_extractor.core.metrics import get_metrics_collector
from hci_extractor.providers import GeminiProvider


@pytest.mark.asyncio
async def test_gemini_provider_collects_metrics():
    """Test that GeminiProvider uses metrics collector instead of internal state."""
    # Clear metrics
    collector = get_metrics_collector()
    collector.clear()

    # Create provider with mocked API
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        provider = GeminiProvider()

        # Mock the API request
        mock_response = {
            "elements": [
                {
                    "element_type": "finding",
                    "text": "Test finding",
                    "evidence_type": "quantitative",
                    "confidence": 0.9,
                }
            ]
        }

        with patch.object(provider, "_make_api_request", return_value=mock_response):
            # Analyze a section
            result = await provider.analyze_section(
                "Test section text for analysis",
                "results",
                context={"paper_id": "test-123"},
            )

            assert len(result) == 1
            assert result[0]["element_type"] == "finding"

    # Check metrics were collected
    summary = collector.get_llm_summary()
    assert summary.total_requests == 1
    assert summary.successful_requests == 1
    assert summary.total_tokens > 0  # Should have estimated tokens
    assert "gemini" in summary.requests_by_provider

    # Verify provider has no mutable state
    assert not hasattr(provider, "_requests_made")
    assert not hasattr(provider, "_tokens_used")
    assert not hasattr(provider, "_estimated_cost")


@pytest.mark.asyncio
async def test_metrics_collection_with_errors():
    """Test that metrics are collected even when errors occur."""
    collector = get_metrics_collector()
    collector.clear()

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        provider = GeminiProvider()

        # Mock API to raise an error
        with patch.object(
            provider, "_make_api_request", side_effect=Exception("API Error")
        ):
            with pytest.raises(Exception):
                await provider.analyze_section("Test text", "results")

    # Metrics should still be collected for failed request
    summary = collector.get_llm_summary()
    assert summary.total_requests == 1
    assert summary.failed_requests == 1
    assert summary.successful_requests == 0


def test_deprecated_usage_stats():
    """Test that get_usage_stats is deprecated but still works."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        provider = GeminiProvider(model_name="test-model")

        # Should return empty stats and log warning
        with patch("hci_extractor.providers.gemini_provider.logger") as mock_logger:
            stats = provider.get_usage_stats()

            assert stats["requests_made"] == 0
            assert stats["tokens_used"] == 0
            assert stats["estimated_cost"] == 0.0
            assert stats["model_name"] == "test-model"

            # Should have logged deprecation warning
            mock_logger.warning.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
