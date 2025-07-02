"""
Comprehensive tests for pipeline components.

Tests CLAUDE.MD requirements:
- Section detection accuracy and completeness
- LLM processing with dependency injection
- Concurrent processing functionality
- Validation pipeline components
- Immutable data flow through pipeline
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict, Any

import pytest

from hci_extractor.models import (
    PdfContent,
    PdfPage,
    Paper,
    DetectedSection,
    ExtractedElement,
    ExtractionResult,
)
from hci_extractor.pipeline import (
    detect_sections,
    SectionProcessor,
    LLMSectionProcessor,
    process_sections_batch,
    validate_extracted_elements,
    quick_validation_stats,
)


class TestSectionDetection:
    """Test section detection functionality."""
    
    def test_detect_sections_basic(self):
        """Test basic section detection with typical academic structure."""
        academic_text = """
        Title: Test Paper
        
        Abstract
        
        This paper presents a novel approach to test detection.
        
        1. Introduction
        
        Human-computer interaction research has shown...
        
        2. Methodology
        
        We conducted a controlled study with participants.
        
        3. Results
        
        Our findings demonstrate significant improvements.
        
        4. Discussion
        
        The results indicate that our approach is effective.
        
        5. Conclusion
        
        We have presented a novel method for detection.
        """
        
        page = PdfPage(
            page_number=1,
            text=academic_text,
            char_count=len(academic_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        sections = detect_sections(pdf_content)
        
        # Should detect major sections
        section_types = [s.section_type for s in sections]
        assert "abstract" in section_types
        assert "introduction" in section_types  
        assert "methodology" in section_types
        assert "results" in section_types
        assert "discussion" in section_types
        assert "conclusion" in section_types
        
        # All sections should be immutable
        for section in sections:
            with pytest.raises((AttributeError, TypeError)):
                section.text = "Modified"
    
    def test_detect_sections_minimal_paper(self):
        """Test section detection with minimal paper structure."""
        minimal_text = """
        Abstract
        This is a minimal paper.
        
        Introduction
        Brief introduction here.
        """
        
        page = PdfPage(
            page_number=1,
            text=minimal_text,
            char_count=len(minimal_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="minimal.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        sections = detect_sections(pdf_content)
        
        # Should still detect what's available
        assert len(sections) >= 2
        section_types = [s.section_type for s in sections]
        assert "abstract" in section_types
        assert "introduction" in section_types
    
    def test_detect_sections_immutable_output(self):
        """Test that section detection returns immutable structures."""
        text = "Abstract\nTest content."
        
        page = PdfPage(
            page_number=1,
            text=text,
            char_count=len(text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        sections = detect_sections(pdf_content)
        
        # Returned tuple should be immutable
        assert isinstance(sections, tuple)
        
        # Individual sections should be frozen
        for section in sections:
            with pytest.raises((AttributeError, TypeError)):
                section.confidence = 0.5


class TestSectionProcessor:
    """Test SectionProcessor interface and implementations."""
    
    def test_section_processor_interface(self):
        """Test that SectionProcessor is properly abstract."""
        from hci_extractor.pipeline.section_processor import SectionProcessor
        
        # Should not be able to instantiate abstract base
        with pytest.raises(TypeError):
            SectionProcessor()
    
    @pytest.mark.asyncio
    async def test_llm_section_processor_initialization(self):
        """Test LLMSectionProcessor dependency injection."""
        # Mock LLM provider
        mock_llm = AsyncMock()
        mock_llm.analyze_section.return_value = []
        
        processor = LLMSectionProcessor(llm_provider=mock_llm)
        
        # Should accept injected dependency
        assert processor.llm_provider == mock_llm
    
    @pytest.mark.asyncio
    async def test_llm_section_processor_analyze_section(self):
        """Test LLM section processing functionality."""
        # Mock LLM provider with realistic response
        mock_llm = AsyncMock()
        mock_llm.analyze_section.return_value = [
            {
                "element_type": "finding",
                "text": "Users completed tasks 25% faster",
                "evidence_type": "quantitative",
                "confidence": 0.9
            }
        ]
        
        processor = LLMSectionProcessor(llm_provider=mock_llm)
        
        # Create test section
        section = DetectedSection.create_with_auto_id(
            section_type="results",
            title="4. Results",
            text="Users completed tasks 25% faster with our system.",
            start_page=1,
            end_page=1,
            confidence=0.8,
            char_start=100,
            char_end=200
        )
        
        paper = Paper.create_with_auto_id(
            title="Test Paper",
            authors=("Dr. Test",)
        )
        
        # Process section
        elements = await processor.analyze_section(section, paper)
        
        # Should return extracted elements
        assert len(elements) == 1
        assert elements[0].element_type == "finding"
        assert elements[0].text == "Users completed tasks 25% faster"
        assert elements[0].paper_id == paper.paper_id
        
        # Should have called LLM provider
        mock_llm.analyze_section.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_sections_batch_concurrent(self):
        """Test concurrent batch processing of sections."""
        # Mock LLM provider
        mock_llm = AsyncMock()
        mock_llm.analyze_section.side_effect = [
            [{"element_type": "claim", "text": "Claim 1", "evidence_type": "theoretical", "confidence": 0.8}],
            [{"element_type": "finding", "text": "Finding 1", "evidence_type": "quantitative", "confidence": 0.9}],
        ]
        
        processor = LLMSectionProcessor(llm_provider=mock_llm)
        
        # Create test sections
        sections = (
            DetectedSection.create_with_auto_id(
                section_type="abstract",
                title="Abstract",
                text="Test abstract content",
                start_page=1,
                end_page=1,
                confidence=0.9,
                char_start=0,
                char_end=50
            ),
            DetectedSection.create_with_auto_id(
                section_type="results",
                title="Results",
                text="Test results content",
                start_page=2,
                end_page=2,
                confidence=0.85,
                char_start=100,
                char_end=150
            )
        )
        
        paper = Paper.create_with_auto_id(
            title="Test Paper",
            authors=("Dr. Test",)
        )
        
        # Process sections concurrently
        all_elements = await process_sections_batch(
            sections=sections,
            paper=paper,
            processor=processor,
            max_concurrent=2
        )
        
        # Should return all elements from all sections
        assert len(all_elements) == 2
        assert all_elements[0].element_type == "claim"
        assert all_elements[1].element_type == "finding"
        
        # Should have called LLM provider for each section
        assert mock_llm.analyze_section.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_sections_batch_error_handling(self):
        """Test error handling in batch processing."""
        # Mock LLM provider that fails on second call
        mock_llm = AsyncMock()
        mock_llm.analyze_section.side_effect = [
            [{"element_type": "claim", "text": "Success", "evidence_type": "theoretical", "confidence": 0.8}],
            Exception("LLM API Error")
        ]
        
        processor = LLMSectionProcessor(llm_provider=mock_llm)
        
        sections = (
            DetectedSection.create_with_auto_id(
                section_type="abstract",
                title="Abstract",
                text="Test content",
                start_page=1,
                end_page=1,
                confidence=0.9,
                char_start=0,
                char_end=50
            ),
            DetectedSection.create_with_auto_id(
                section_type="results",
                title="Results",
                text="Test content",
                start_page=2,
                end_page=2,
                confidence=0.85,
                char_start=100,
                char_end=150
            )
        )
        
        paper = Paper.create_with_auto_id(title="Test", authors=("Author",))
        
        # Should handle errors gracefully
        all_elements = await process_sections_batch(
            sections=sections,
            paper=paper,
            processor=processor,
            max_concurrent=2
        )
        
        # Should return elements from successful sections only
        assert len(all_elements) == 1
        assert all_elements[0].text == "Success"


class TestValidation:
    """Test validation pipeline components."""
    
    def test_validate_extracted_elements_duplicates(self):
        """Test duplicate detection in validation."""
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Duplicate text for testing validation",
                section="results",
                confidence=0.9,
                evidence_type="quantitative"
            ),
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="claim",
                text="Duplicate text for testing validation",  # Same text
                section="abstract",
                confidence=0.8,
                evidence_type="theoretical"
            ),
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="method",
                text="Unique text for testing validation methodology",
                section="methodology",
                confidence=0.85,
                evidence_type="qualitative"
            )
        )
        
        # Create PDF content with source text
        page = PdfPage(
            page_number=1,
            text="This contains: Duplicate text for testing validation and Unique text for testing validation methodology",
            char_count=100,
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        validated_elements = validate_extracted_elements(elements, pdf_content)
        
        # Should remove duplicates but keep unique text
        assert len(validated_elements) == 2
        texts = [e.text for e in validated_elements]
        assert "Unique text for testing validation methodology" in texts
        # Should keep the first occurrence of duplicate
        assert texts.count("Duplicate text for testing validation") == 1
    
    def test_validate_extracted_elements_verbatim_check(self):
        """Test verbatim accuracy validation (CLAUDE.MD requirement)."""
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="exact match text for testing",  # Will be found
                section="results",
                confidence=0.9,
                evidence_type="quantitative"
            ),
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="claim",
                text="modified text not in source",  # Will not be found
                section="abstract",
                confidence=0.8,
                evidence_type="theoretical"
            )
        )
        
        # Create PDF content with source text
        page = PdfPage(
            page_number=1,
            text="This document contains exact match text for testing but not the other.",
            char_count=75,
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        validated_elements = validate_extracted_elements(elements, pdf_content)
        
        # Should only keep elements with verbatim matches
        assert len(validated_elements) == 1
        assert validated_elements[0].text == "exact match text for testing"
    
    def test_quick_validation_stats(self):
        """Test validation statistics generation."""
        original_elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Finding one for testing validation",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Finding two for testing validation",
                section="results",
                confidence=0.85,
                evidence_type="quantitative"
            ),
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="claim",
                text="Claim one for testing validation",
                section="abstract",
                confidence=0.75,
                evidence_type="theoretical"
            )
        )
        
        validated_elements = (
            original_elements[0],  # Keep first
            original_elements[2],  # Keep third, skip second
        )
        
        stats = quick_validation_stats(original_elements, validated_elements)
        
        # Should provide validation statistics
        assert stats["original_count"] == 3
        assert stats["validated_count"] == 2
        assert stats["removed_count"] == 1
        assert stats["validation_rate"] == pytest.approx(2/3, rel=0.01)
        assert stats["element_types"]["finding"] == 1
        assert stats["element_types"]["claim"] == 1
        assert stats["element_types"]["method"] == 0


class TestPipelineIntegration:
    """Test end-to-end pipeline integration."""
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_flow(self):
        """Test complete extraction pipeline from PDF to validated elements."""
        # Create realistic academic content
        academic_text = """
        TouchGestures: Enhanced Multi-touch Interaction
        
        Abstract
        
        We present TouchGestures, a novel interaction technique that enables users to perform complex multi-touch gestures with 40% fewer errors than standard touch interfaces.
        
        1. Introduction
        
        Traditional touch interfaces limit user expression and efficiency.
        
        2. Results
        
        Users completed tasks 23% faster using TouchGestures compared to conventional touch input (M=42.3s vs M=55.1s, p<0.001).
        """
        
        # Create PDF content
        page = PdfPage(
            page_number=1,
            text=academic_text,
            char_count=len(academic_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="integration_test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={"test": True}
        )
        
        # Step 1: Detect sections
        sections = detect_sections(pdf_content)
        assert len(sections) >= 3  # abstract, introduction, results
        
        # Step 2: Mock LLM processing
        mock_llm = AsyncMock()
        mock_llm.analyze_section.return_value = [
            {
                "element_type": "finding",
                "text": "Users completed tasks 23% faster using TouchGestures compared to conventional touch input",
                "evidence_type": "quantitative",
                "confidence": 0.95
            }
        ]
        
        processor = LLMSectionProcessor(llm_provider=mock_llm)
        paper = Paper.create_with_auto_id(
            title="TouchGestures Paper",
            authors=("Dr. Touch",)
        )
        
        # Step 3: Process sections
        all_elements = await process_sections_batch(
            sections=sections,
            paper=paper,
            processor=processor,
            max_concurrent=2
        )
        
        # Step 4: Validate elements
        validated_elements = validate_extracted_elements(all_elements, academic_text)
        
        # Should maintain data integrity throughout pipeline
        assert len(validated_elements) > 0
        for element in validated_elements:
            assert element.paper_id == paper.paper_id
            assert element.text in academic_text  # Verbatim requirement
        
        # Step 5: Generate stats
        stats = quick_validation_stats(validated_elements)
        assert stats["total_elements"] > 0
        assert "element_type_counts" in stats
        assert "average_confidence" in stats
    
    def test_pipeline_immutability_preserved(self):
        """Test that immutability is preserved through entire pipeline."""
        # Create test data
        text = "Abstract\nTest finding about performance."
        
        page = PdfPage(
            page_number=1,
            text=text,
            char_count=len(text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="immutable_test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        # Detect sections
        sections = detect_sections(pdf_content)
        
        # All returned data should be immutable
        assert isinstance(sections, tuple)  # Immutable sequence
        
        for section in sections:
            # DetectedSection should be frozen
            with pytest.raises((AttributeError, TypeError)):
                section.text = "Modified"
        
        # Original PDF content should remain unchanged
        assert pdf_content.pages[0].text == text
        assert pdf_content.total_pages == 1


if __name__ == "__main__":
    pytest.main([__file__])