"""
Comprehensive tests for immutable data models.

Tests CLAUDE.MD requirements:
- Immutability validation (frozen dataclasses)
- Field validation and constraints
- Factory method functionality
- UUID generation uniqueness
"""

import uuid

import pytest

from hci_extractor.core.models import (
    CharacterPosition,
    # Exceptions
    DataValidationError,
    DetectedSection,
    ExtractedElement,
    ExtractionResult,
    HciExtractorError,
    Paper,
    PdfContent,
    PdfPage,
)


class TestPaper:
    """Test Paper data model immutability and validation."""

    def test_paper_creation_with_auto_id(self):
        """Test Paper.create_with_auto_id generates unique IDs."""
        paper1 = Paper.create_with_auto_id(
            title="Test Paper 1",
            authors=("Dr. Test",),
            venue="Test Conference",
        )

        paper2 = Paper.create_with_auto_id(
            title="Test Paper 2",
            authors=("Dr. Test",),
            venue="Test Conference",
        )

        # Should have unique IDs
        assert paper1.paper_id != paper2.paper_id
        assert uuid.UUID(paper1.paper_id)  # Valid UUID
        assert uuid.UUID(paper2.paper_id)  # Valid UUID

    def test_paper_immutability(self):
        """Test that Paper objects are truly immutable."""
        paper = Paper.create_with_auto_id(
            title="Immutable Test",
            authors=("Dr. Frozen",),
        )

        # Should not be able to modify any field
        with pytest.raises((AttributeError, TypeError)):
            paper.title = "Modified Title"

        with pytest.raises((AttributeError, TypeError)):
            paper.authors = ("Different Author",)

        with pytest.raises((AttributeError, TypeError)):
            paper.paper_id = "new-id"

    def test_paper_validation(self):
        """Test Paper field validation."""
        # Empty paper ID should fail
        with pytest.raises(ValueError, match="Paper ID cannot be empty"):
            Paper(paper_id="", title="Test", authors=("Author",))

        # Empty title should fail
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Paper(paper_id="test-id", title="", authors=("Author",))

        # Empty authors should fail
        with pytest.raises(ValueError, match="Authors cannot be empty"):
            Paper(paper_id="test-id", title="Test", authors=())

    def test_paper_authors_immutable_tuple(self):
        """Test that authors field uses immutable tuple."""
        paper = Paper.create_with_auto_id(
            title="Authors Test",
            authors=["Dr. A", "Dr. B"],  # Pass list
        )

        # Should be converted to tuple
        assert isinstance(paper.authors, tuple)
        assert paper.authors == ("Dr. A", "Dr. B")

        # Tuple should be immutable
        with pytest.raises((AttributeError, TypeError)):
            paper.authors[0] = "Modified"


class TestExtractedElement:
    """Test ExtractedElement data model."""

    def test_element_creation_with_auto_id(self):
        """Test ExtractedElement.create_with_auto_id."""
        element = ExtractedElement.create_with_auto_id(
            paper_id="test-paper-id",
            element_type="finding",
            text="Users completed tasks 30% faster",
            section="results",
            confidence=0.95,
            evidence_type="quantitative",
        )

        assert uuid.UUID(element.element_id)  # Valid UUID
        assert element.paper_id == "test-paper-id"
        assert element.element_type == "finding"
        assert element.confidence == 0.95

    def test_element_immutability(self):
        """Test ExtractedElement immutability."""
        element = ExtractedElement.create_with_auto_id(
            paper_id="test-id",
            element_type="claim",
            text="Test claim",
            section="abstract",
            confidence=0.8,
            evidence_type="theoretical",
        )

        with pytest.raises((AttributeError, TypeError)):
            element.text = "Modified text"

        with pytest.raises((AttributeError, TypeError)):
            element.confidence = 0.9

    def test_element_validation(self):
        """Test ExtractedElement field validation."""
        # Invalid confidence range
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            ExtractedElement.create_with_auto_id(
                paper_id="test-id",
                element_type="finding",
                text="Test",
                section="results",
                confidence=1.5,  # Invalid
                evidence_type="quantitative",
            )

        # Empty text
        with pytest.raises(ValueError, match="Text cannot be empty"):
            ExtractedElement.create_with_auto_id(
                paper_id="test-id",
                element_type="finding",
                text="",  # Invalid
                section="results",
                confidence=0.8,
                evidence_type="quantitative",
            )

        # Invalid page number
        with pytest.raises(ValueError, match="Page number must be >= 1"):
            ExtractedElement(
                element_id="test-id",
                paper_id="paper-id",
                element_type="finding",
                text="Test text",
                section="results",
                confidence=0.8,
                evidence_type="quantitative",
                page_number=0,  # Invalid
            )

    def test_element_type_validation(self):
        """Test element_type literal validation."""
        # Valid types should work
        for element_type in ["claim", "finding", "method"]:
            element = ExtractedElement.create_with_auto_id(
                paper_id="test-id",
                element_type=element_type,
                text="Test text",
                section="test",
                confidence=0.8,
                evidence_type="quantitative",
            )
            assert element.element_type == element_type

    def test_evidence_type_validation(self):
        """Test evidence_type literal validation."""
        # Valid evidence types should work
        for evidence_type in ["quantitative", "qualitative", "theoretical", "unknown"]:
            element = ExtractedElement.create_with_auto_id(
                paper_id="test-id",
                element_type="finding",
                text="Test text",
                section="test",
                confidence=0.8,
                evidence_type=evidence_type,
            )
            assert element.evidence_type == evidence_type


class TestDetectedSection:
    """Test DetectedSection data model."""

    def test_section_creation_with_auto_id(self):
        """Test DetectedSection.create_with_auto_id."""
        section = DetectedSection.create_with_auto_id(
            section_type="abstract",
            title="Abstract",
            text="This paper presents...",
            start_page=1,
            end_page=1,
            confidence=0.9,
            char_start=0,
            char_end=100,
        )

        assert uuid.UUID(section.section_id)  # Valid UUID
        assert section.section_type == "abstract"
        assert section.confidence == 0.9

    def test_section_immutability(self):
        """Test DetectedSection immutability."""
        section = DetectedSection.create_with_auto_id(
            section_type="methodology",
            title="3. Methodology",
            text="We conducted...",
            start_page=2,
            end_page=3,
            confidence=0.85,
            char_start=500,
            char_end=800,
        )

        with pytest.raises((AttributeError, TypeError)):
            section.text = "Modified text"

        with pytest.raises((AttributeError, TypeError)):
            section.confidence = 0.95

    def test_section_validation(self):
        """Test DetectedSection field validation."""
        # Invalid page ordering
        with pytest.raises(ValueError, match="End page must be >= start page"):
            DetectedSection.create_with_auto_id(
                section_type="test",
                title="Test",
                text="Test text",
                start_page=3,
                end_page=2,  # Invalid: end < start
                confidence=0.8,
                char_start=0,
                char_end=100,
            )

        # Invalid character ordering
        with pytest.raises(ValueError, match="Character end must be > character start"):
            DetectedSection.create_with_auto_id(
                section_type="test",
                title="Test",
                text="Test text",
                start_page=1,
                end_page=1,
                confidence=0.8,
                char_start=100,
                char_end=50,  # Invalid: end < start
            )


class TestExtractionResult:
    """Test ExtractionResult data model."""

    def test_extraction_result_creation(self):
        """Test ExtractionResult creation and properties."""
        paper = Paper.create_with_auto_id(title="Test Paper", authors=("Dr. Test",))

        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id=paper.paper_id,
                element_type="claim",
                text="Test claim",
                section="abstract",
                confidence=0.9,
                evidence_type="theoretical",
            ),
            ExtractedElement.create_with_auto_id(
                paper_id=paper.paper_id,
                element_type="finding",
                text="Test finding",
                section="results",
                confidence=0.95,
                evidence_type="quantitative",
            ),
        )

        result = ExtractionResult(
            paper=paper,
            elements=elements,
            extraction_metadata={"test": True},
        )

        assert result.paper == paper
        assert result.elements == elements
        assert result.total_elements == 2
        assert result.extraction_metadata["test"] is True

    def test_extraction_result_immutability(self):
        """Test ExtractionResult immutability."""
        paper = Paper.create_with_auto_id(title="Test", authors=("Author",))
        result = ExtractionResult(paper=paper, elements=(), extraction_metadata={})

        with pytest.raises((AttributeError, TypeError)):
            result.paper = Paper.create_with_auto_id(
                title="Different",
                authors=("Other",),
            )

        with pytest.raises((AttributeError, TypeError)):
            result.elements = (
                ExtractedElement.create_with_auto_id(
                    paper_id="test",
                    element_type="claim",
                    text="test",
                    section="test",
                    confidence=0.8,
                    evidence_type="theoretical",
                ),
            )


class TestPdfModels:
    """Test PDF-related data models."""

    def test_pdf_page_validation(self):
        """Test PdfPage validation."""
        # Text length must match char_count
        with pytest.raises(ValueError, match="Text length must match char_count"):
            PdfPage(
                page_number=1,
                text="Hello",  # 5 chars
                char_count=10,  # Mismatch
                dimensions=(612.0, 792.0),
                char_positions=(),
            )

        # Page number must be >= 1
        with pytest.raises(ValueError, match="Page number must be >= 1"):
            PdfPage(
                page_number=0,  # Invalid
                text="Hello",
                char_count=5,
                dimensions=(612.0, 792.0),
                char_positions=(),
            )

    def test_character_position_validation(self):
        """Test CharacterPosition validation."""
        # Character index must be >= 0
        with pytest.raises(ValueError, match="Character index must be >= 0"):
            CharacterPosition(
                char_index=-1,  # Invalid
                page_number=1,
                x=100.0,
                y=200.0,
                bbox=(0.0, 0.0, 50.0, 20.0),
            )

        # BBox must have 4 coordinates
        with pytest.raises(ValueError, match="Bbox must have exactly 4 coordinates"):
            CharacterPosition(
                char_index=0,
                page_number=1,
                x=100.0,
                y=200.0,
                bbox=(0.0, 0.0, 50.0),  # Only 3 coordinates
            )

    def test_pdf_content_properties(self):
        """Test PdfContent computed properties."""
        page1 = PdfPage(
            page_number=1,
            text="Page 1 content",
            char_count=14,
            dimensions=(612.0, 792.0),
            char_positions=(),
        )

        page2 = PdfPage(
            page_number=2,
            text="Page 2 content",
            char_count=14,
            dimensions=(612.0, 792.0),
            char_positions=(),
        )

        pdf_content = PdfContent(
            file_path="test.pdf",
            total_pages=2,
            pages=(page1, page2),
            extraction_metadata={},
        )

        # Test computed properties
        assert pdf_content.total_chars == 28  # 14 + 14
        assert len(pdf_content.pages) == 2


class TestExceptionHierarchy:
    """Test the unified exception hierarchy."""

    def test_exception_inheritance(self):
        """Test exception inheritance relationships."""
        # All should inherit from HciExtractorError
        from hci_extractor.core.models import (
            DataValidationError,
            LLMError,
            PdfError,
            ProcessingError,
        )

        assert issubclass(ProcessingError, HciExtractorError)
        assert issubclass(DataValidationError, HciExtractorError)
        assert issubclass(LLMError, ProcessingError)
        assert issubclass(PdfError, ProcessingError)

    def test_exception_creation(self):
        """Test exception creation and messages."""
        error = DataValidationError("Test validation error")
        assert str(error) == "Test validation error"
        assert isinstance(error, HciExtractorError)


if __name__ == "__main__":
    pytest.main([__file__])
