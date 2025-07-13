"""Tests for LLM markup generation functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hci_extractor.core.events import EventBus
from hci_extractor.providers.gemini_provider import GeminiProvider
from hci_extractor.providers.provider_config import LLMProviderConfig


class TestLLMMarkupGeneration:
    """Test LLM markup generation functionality."""

    @pytest.fixture
    def mock_genai(self):
        """Mock the entire google.generativeai module."""
        with patch("hci_extractor.providers.gemini_provider.genai") as mock_genai:
            # Mock the GenerativeModel class
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model

            # Mock the generation config
            mock_genai.types.GenerationConfig = MagicMock

            # Make configure a no-op
            mock_genai.configure = MagicMock()

            yield mock_genai, mock_model

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return MagicMock(spec=EventBus)

    @pytest.fixture
    def provider_config(self):
        """Create test provider configuration."""
        return LLMProviderConfig(
            api_key="test-api-key",
            temperature=0.1,
            max_output_tokens=100000,
            max_attempts=3,
            timeout_seconds=30.0,
            rate_limit_delay=1.0,
        )

    @pytest.fixture
    def sample_academic_text(self):
        """Sample academic text for markup testing."""
        return """
        Abstract: This study investigates machine learning approaches for document processing.

        1. Introduction
        The goal of this research is to develop automated systems for academic paper analysis.

        2. Methodology
        We employed deep learning techniques with neural networks and attention mechanisms.
        The experimental setup included data preprocessing and model validation.

        3. Results
        Our approach achieved 95% accuracy on the test dataset.
        Processing time was reduced by 40% compared to baseline methods.

        4. Conclusion
        The results demonstrate significant improvements in automated document processing.
        """

    @pytest.fixture
    def expected_markup(self):
        """Expected markup output with goal/method/result tags."""
        return """
        Abstract: This study investigates machine learning approaches for document processing.

        1. Introduction
        <goal confidence="0.92">The goal of this research is to develop automated systems for academic paper analysis.</goal>

        2. Methodology
        <method confidence="0.88">We employed deep learning techniques with neural networks and attention mechanisms.</method>
        <method confidence="0.85">The experimental setup included data preprocessing and model validation.</method>

        3. Results
        <result confidence="0.94">Our approach achieved 95% accuracy on the test dataset.</result>
        <result confidence="0.91">Processing time was reduced by 40% compared to baseline methods.</result>

        4. Conclusion
        The results demonstrate significant improvements in automated document processing.
        """

    @pytest.mark.asyncio
    async def test_generate_markup_success(
        self, provider_config, mock_event_bus, sample_academic_text, mock_genai
    ):
        """Test successful markup generation."""
        mock_genai_module, mock_model = mock_genai

        # Create provider with mock dependencies
        mock_prompt_loader = MagicMock()
        mock_prompt_loader.get_markup_prompt.return_value = (
            "Generate markup for: {text}"
        )

        # Mock the API response
        mock_response = MagicMock()
        mock_response.text = (
            """<goal confidence="0.92">develop automated systems</goal> sample text"""
        )

        # Set up the model's generate_content_async method
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        # Now create the provider - it will use our mocked genai
        provider = GeminiProvider(
            provider_config=provider_config,
            event_bus=mock_event_bus,
            markup_prompt_loader=mock_prompt_loader,
            model_name="gemini-1.5-flash",
        )

        # Test markup generation
        result = await provider.generate_markup(sample_academic_text)

        # Verify basic expectations
        assert isinstance(result, str)
        assert len(result) > 0
        assert "<goal" in result or "<method" in result or "<result" in result

    @pytest.mark.asyncio
    async def test_generate_markup_with_chunking(
        self, provider_config, mock_event_bus, mock_genai
    ):
        """Test markup generation with large text that requires chunking."""
        mock_genai_module, mock_model = mock_genai

        # Create large text that exceeds single chunk size
        large_text = "This is a test paper. " * 1000  # Create large text

        mock_prompt_loader = MagicMock()
        mock_prompt_loader.get_markup_prompt.return_value = (
            "Generate markup for: {text}"
        )

        # Mock the API responses for chunks
        mock_response = MagicMock()
        mock_response.text = "Processed chunk with markup"
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        # Create provider with mocked dependencies
        provider = GeminiProvider(
            provider_config=provider_config,
            event_bus=mock_event_bus,
            markup_prompt_loader=mock_prompt_loader,
            model_name="gemini-1.5-flash",
        )

        # Test chunked processing
        result = await provider.generate_markup(large_text)

        # Verify chunking worked
        assert isinstance(result, str)
        assert len(result) > 0
        # Verify multiple API calls were made (chunking occurred)
        assert mock_model.generate_content_async.call_count > 1

    @pytest.mark.asyncio
    async def test_generate_markup_api_failure(
        self, provider_config, mock_event_bus, sample_academic_text, mock_genai
    ):
        """Test markup generation with API failure."""
        mock_genai_module, mock_model = mock_genai

        mock_prompt_loader = MagicMock()
        mock_prompt_loader.get_markup_prompt.return_value = (
            "Generate markup for: {text}"
        )

        # Mock API failure
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )

        provider = GeminiProvider(
            provider_config=provider_config,
            event_bus=mock_event_bus,
            markup_prompt_loader=mock_prompt_loader,
            model_name="gemini-1.5-flash",
        )

        # Test that API failure is handled appropriately
        from hci_extractor.core.models.exceptions import GeminiApiError

        with pytest.raises(GeminiApiError):
            await provider.generate_markup(sample_academic_text)

    def test_markup_format_validation(self, expected_markup):
        """Test that markup follows expected format."""
        # This test validates the markup format we expect

        # Should contain goal tags with confidence
        assert '<goal confidence="' in expected_markup
        assert "</goal>" in expected_markup

        # Should contain method tags with confidence
        assert '<method confidence="' in expected_markup
        assert "</method>" in expected_markup

        # Should contain result tags with confidence
        assert '<result confidence="' in expected_markup
        assert "</result>" in expected_markup

        # Confidence values should be between 0.50 and 0.99
        import re

        confidence_pattern = r'confidence="(0\.\d+)"'
        confidences = re.findall(confidence_pattern, expected_markup)

        for conf_str in confidences:
            confidence = float(conf_str)
            assert 0.50 <= confidence <= 0.99, f"Confidence {confidence} out of range"

    @pytest.mark.asyncio
    async def test_empty_text_handling(
        self, provider_config, mock_event_bus, mock_genai
    ):
        """Test handling of empty or very short text."""
        mock_genai_module, mock_model = mock_genai

        mock_prompt_loader = MagicMock()
        mock_prompt_loader.get_markup_prompt.return_value = (
            "Generate markup for: {text}"
        )

        # Set up mock response for short text
        mock_response = MagicMock()
        mock_response.text = "Hi"
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        provider = GeminiProvider(
            provider_config=provider_config,
            event_bus=mock_event_bus,
            markup_prompt_loader=mock_prompt_loader,
            model_name="gemini-1.5-flash",
        )

        # Test empty text - should return empty without calling API
        result = await provider.generate_markup("")
        assert result == ""
        assert mock_model.generate_content_async.call_count == 0

        # Test very short text
        short_text = "Hi"
        result = await provider.generate_markup(short_text)
        assert isinstance(result, str)
        assert mock_model.generate_content_async.call_count == 1
