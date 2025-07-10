"""
Comprehensive verbatim accuracy validation tests.

Tests CLAUDE.MD requirement: "Verbatim accuracy: 100%"
"""

import pytest

from hci_extractor.core.analysis import validate_extracted_elements
from hci_extractor.core.models import (
    ExtractedElement,
    PdfContent,
    PdfPage,
)


class TestVerbatimAccuracy:
    """Test 100% verbatim accuracy requirement."""

    def test_exact_text_match_passes(self):
        """Test that exactly matching text passes validation."""
        source_text = "Users completed tasks 25% faster with the new interface."

        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=(),
        )

        pdf_content = PdfContent(
            file_path="test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={},
        )

        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Users completed tasks 25% faster with the new interface",
                section="results",
                confidence=0.95,
                evidence_type="quantitative",
            ),
        )

        validated = validate_extracted_elements(elements, pdf_content)
        assert len(validated) == 1

    def test_paraphrased_text_rejected(self):
        """Test that paraphrased text is rejected."""
        source_text = "Users completed tasks 25% faster with the new interface."

        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=(),
        )

        pdf_content = PdfContent(
            file_path="test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={},
        )

        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Participants performed tasks one quarter faster",
                section="results",
                confidence=0.95,
                evidence_type="quantitative",
            ),
        )

        validated = validate_extracted_elements(elements, pdf_content)
        assert len(validated) == 0

    def test_partial_text_extraction_allowed(self):
        """Test that extracting part of a sentence is allowed."""
        source_text = (
            "In our study, users completed tasks 25% faster with the new "
            "interface design compared to the baseline."
        )

        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=(),
        )

        pdf_content = PdfContent(
            file_path="test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={},
        )

        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="users completed tasks 25% faster",
                section="results",
                confidence=0.95,
                evidence_type="quantitative",
            ),
        )

        validated = validate_extracted_elements(elements, pdf_content)
        assert len(validated) == 1


if __name__ == "__main__":
    pytest.main([__file__])
