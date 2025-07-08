"""Test configuration integration with components."""

from unittest.mock import AsyncMock

import pytest

from hci_extractor.core.analysis import LLMSectionProcessor, detect_sections
from hci_extractor.core.config import AnalysisConfig, ExtractorConfig, RetryConfig
from hci_extractor.core.models import PdfContent, PdfPage


def test_section_detector_uses_config():
    """Test that section detector respects config min_section_length."""
    # Create two configs with different min section lengths
    config_30 = ExtractorConfig.for_testing(
        analysis=AnalysisConfig(min_section_length=30)
    )
    config_150 = ExtractorConfig.for_testing(
        analysis=AnalysisConfig(min_section_length=150)
    )

    # Create PDF with sections of different lengths
    # The methodology section will be exactly 45 chars after the header
    test_text = """Title of Paper

Abstract

This is the abstract section with sufficient content to be detected in all cases.

1. Introduction

This is the introduction section with even more content to ensure it's always detected regardless of the minimum length setting.

2. Methodology

Short methodology section with 45 characters.

3. Results

The results section has a reasonable amount of content that should be detected with lower thresholds but might be filtered with very high ones."""

    pdf_content = PdfContent(
        file_path="test.pdf",
        total_pages=1,
        pages=(
            PdfPage(
                page_number=1,
                text=test_text,
                char_count=len(test_text),
                dimensions=(612.0, 792.0),
                char_positions=(),
            ),
        ),
        extraction_metadata={},
    )

    # Test with lenient config (min=30)
    sections_30 = detect_sections(pdf_content, config_30)

    # Test with strict config (min=150)
    sections_150 = detect_sections(pdf_content, config_150)

    # With lenient config, sections should be detected
    assert len(sections_30) >= 2  # At least intro and methodology

    # With strict config, short sections should be filtered out
    assert len(sections_150) <= len(sections_30)  # Should be same or fewer

    # Verify that remaining sections meet the minimum length
    for section in sections_150:
        assert len(section.text) >= 150


@pytest.mark.asyncio
async def test_llm_processor_uses_config():
    """Test that LLM processor uses config values."""
    # Create config with custom values
    config = ExtractorConfig.for_testing(
        analysis=AnalysisConfig(
            chunk_size=500, chunk_overlap=50, section_timeout_seconds=10.0
        ),
        retry=RetryConfig(max_attempts=1),
    )

    # Create mock LLM provider
    mock_llm = AsyncMock()

    # Create processor with config
    processor = LLMSectionProcessor(mock_llm, config=config)

    # Verify config values are used
    assert processor.chunk_size == 500
    assert processor.chunk_overlap == 50
    assert processor.timeout_seconds == 10.0
    assert processor.max_retries == 1

    # Test backwards compatibility - explicit params override config
    processor2 = LLMSectionProcessor(
        mock_llm, config=config, chunk_size=1000, max_retries=5
    )
    assert processor2.chunk_size == 1000  # Overridden
    assert processor2.chunk_overlap == 50  # From config
    assert processor2.max_retries == 5  # Overridden


def test_config_integration_end_to_end():
    """Test that configuration flows through the system."""
    # Create a test config
    config = ExtractorConfig.for_testing(
        analysis=AnalysisConfig(min_section_length=75, chunk_size=2000)
    )

    # Create test PDF
    test_text = """Abstract

Short abstract text here.

1. Introduction

This is a longer introduction section that should definitely be detected because it has enough content to meet the minimum length requirement."""

    pdf_content = PdfContent(
        file_path="test.pdf",
        total_pages=1,
        pages=(
            PdfPage(
                page_number=1,
                text=test_text,
                char_count=len(test_text),
                dimensions=(612.0, 792.0),
                char_positions=(),
            ),
        ),
        extraction_metadata={},
    )

    # Detect sections with config
    sections = detect_sections(pdf_content, config)

    # Check that configuration is being respected
    for section in sections:
        # All detected sections should meet the min length
        assert len(section.text) >= 75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
