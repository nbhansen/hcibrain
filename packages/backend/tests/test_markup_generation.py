"""Test markup generation core functionality."""

import pytest

from hci_extractor.core.di_container import create_configured_container
from hci_extractor.core.ports.llm_provider_port import LLMProviderPort


class TestMarkupGeneration:
    """Test core markup generation functionality."""

    @pytest.fixture
    def container(self):
        """Create configured DI container."""
        return create_configured_container()

    @pytest.fixture
    def llm_provider(self, container):
        """Get LLM provider from DI container."""
        return container.resolve(LLMProviderPort)

    @pytest.mark.asyncio
    async def test_can_generate_markup_for_paper_text(self, llm_provider):
        """Test that markup generation works for basic paper text."""
        # Sample academic paper text
        test_text = """
        Abstract: This study investigates user interaction patterns.
        
        1. Introduction
        The goal of this research is to understand how users interact with interfaces.
        We employed a mixed-methods approach combining surveys and observations.
        Our results show significant improvements in user satisfaction.
        """

        # Generate markup
        result = await llm_provider.generate_markup(test_text)

        # Verify we got a string response
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify markup contains the original text (or processed version)
        assert "interaction" in result.lower()

    @pytest.mark.asyncio
    async def test_handles_empty_text_gracefully(self, llm_provider):
        """Test that markup generation handles empty text gracefully."""
        # Test with empty string
        result = await llm_provider.generate_markup("")

        # Should return empty or minimal result without crashing
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_handles_minimal_text(self, llm_provider):
        """Test that markup generation works with minimal text."""
        test_text = "This is a minimal test."

        result = await llm_provider.generate_markup(test_text)

        assert isinstance(result, str)
        assert len(result) > 0
