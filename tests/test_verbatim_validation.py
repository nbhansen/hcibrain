"""
Comprehensive verbatim accuracy validation tests.

Tests CLAUDE.MD requirement: "Verbatim accuracy: 100% (extracted text must exist verbatim in source)"

This is a critical requirement for academic integrity - extracted text must exist
exactly as written in the source document with no paraphrasing or modification.
"""

import pytest
from typing import List

from hci_extractor.core.models import (
    PdfContent,
    PdfPage,
    ExtractedElement,
    Paper,
)
from hci_extractor.core.analysis import validate_extracted_elements


class TestVerbatimAccuracy:
    """Test 100% verbatim accuracy requirement."""
    
    def test_exact_text_match_passes(self):
        """Test that exactly matching text passes validation."""
        source_text = "Users completed tasks 25% faster with the new interface design."
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="exact_match.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Users completed tasks 25% faster with the new interface design",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should pass with exact match
        assert len(validated) == 1
        assert validated[0].text == "Users completed tasks 25% faster with the new interface design"
    
    def test_whitespace_normalization_allowed(self):
        """Test that whitespace differences are normalized (academic papers have formatting)."""
        source_text = "Users   completed\ntasks 25%   faster\n  with the new interface design."
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="whitespace_test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Users completed tasks 25% faster with the new interface design",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should pass with whitespace normalization
        assert len(validated) == 1
    
    def test_case_insensitive_matching(self):
        """Test that case differences are handled (PDF extraction can vary case)."""
        source_text = "USERS COMPLETED TASKS 25% FASTER WITH THE NEW INTERFACE DESIGN."
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="case_test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Users completed tasks 25% faster with the new interface design",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should pass with case normalization
        assert len(validated) == 1
    
    def test_paraphrased_text_rejected(self):
        """Test that paraphrased text is rejected (violates verbatim requirement)."""
        source_text = "Users completed tasks 25% faster with the new interface design."
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="paraphrase_test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            # This is paraphrased, not verbatim
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Participants performed tasks one quarter faster using the updated UI",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should reject paraphrased text
        assert len(validated) == 0
    
    def test_summarized_text_rejected(self):
        """Test that summarized text is rejected (violates verbatim requirement)."""
        source_text = """
        In our controlled study with 24 participants, we found that users completed 
        tasks 25% faster with the new interface design compared to the baseline 
        interface. The improvement was statistically significant (p < 0.001) and 
        consistent across all participant demographics.
        """
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="summary_test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            # This is a summary, not verbatim
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Study showed 25% performance improvement",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should reject summarized text
        assert len(validated) == 0
    
    def test_partial_text_extraction_allowed(self):
        """Test that extracting part of a sentence is allowed (common in academic analysis)."""
        source_text = """
        In our controlled study with 24 participants, we found that users completed 
        tasks 25% faster with the new interface design compared to the baseline 
        interface. The improvement was statistically significant (p < 0.001) and 
        consistent across all participant demographics.
        """
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="partial_test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            # Extract partial sentence - this is verbatim from source
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="users completed tasks 25% faster with the new interface design",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
            # Extract statistical information - also verbatim
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="statistically significant (p < 0.001)",
                section="results",
                confidence=0.90,
                evidence_type="quantitative"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should allow verbatim partial extractions
        assert len(validated) == 2
    
    def test_cross_page_text_handled(self):
        """Test behavior with text that spans pages (current implementation joins pages)."""
        page1_text = "Users completed tasks 25% faster"
        page2_text = "with the new interface design in our study."
        
        page1 = PdfPage(
            page_number=1,
            text=page1_text,
            char_count=len(page1_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        page2 = PdfPage(
            page_number=2,
            text=page2_text,
            char_count=len(page2_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="cross_page_test.pdf",
            total_pages=2,
            pages=(page1, page2),
            extraction_metadata={}
        )
        
        elements = (
            # Extract text that exists on page 1
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Users completed tasks 25% faster",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
            # Extract text that exists on page 2
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="with the new interface design in our study",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Both extractions should be valid since they exist in their respective pages
        assert len(validated) == 2
    
    def test_multiple_valid_extractions(self):
        """Test validation of multiple verbatim extractions from same source."""
        source_text = """
        Abstract
        
        We present TouchGestures, a novel multi-touch interface that reduces user 
        errors by 40% compared to traditional touch interfaces. In a controlled 
        study with 24 participants, users completed tasks 25% faster (p < 0.001) 
        and reported higher satisfaction scores (M = 6.8 vs M = 4.2 on 7-point scale).
        
        Introduction
        
        Traditional touch interfaces suffer from accuracy limitations. Our research 
        addresses the fundamental challenge of enabling complex gestural input while 
        maintaining system responsiveness.
        """
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="multiple_test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="users completed tasks 25% faster",
                section="abstract",
                confidence=0.95,
                evidence_type="quantitative"
            ),
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="reported higher satisfaction scores",
                section="abstract",
                confidence=0.90,
                evidence_type="quantitative"
            ),
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="claim",
                text="Traditional touch interfaces suffer from accuracy limitations",
                section="introduction",
                confidence=0.85,
                evidence_type="theoretical"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # All extractions should pass verbatim validation
        assert len(validated) == 3
        
        # Verify each text exists in source
        full_text = pdf_content.full_text
        for element in validated:
            assert element.text.lower() in full_text.lower()
    
    def test_empty_text_rejected(self):
        """Test that empty or whitespace-only text is rejected by validation."""
        source_text = "Valid content for testing purposes."
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="empty_test.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        # Note: ExtractedElement model validation prevents empty text at creation
        # So this tests the validation function's handling of empty-like text
        
        # Test with minimal text that would pass model validation but fail quality checks
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="a",  # Too short
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="123",  # No letters
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should reject low-quality text through quality filtering
        assert len(validated) == 0


class TestVerbatimEdgeCases:
    """Test edge cases in verbatim validation."""
    
    def test_special_characters_preserved(self):
        """Test that special characters and formatting are preserved."""
        source_text = "Performance improved by ~25% (β = 0.42, p < 0.001, CI₉₅ = [0.15, 0.35])."
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="special_chars.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text="Performance improved by ~25% (β = 0.42, p < 0.001, CI₉₅ = [0.15, 0.35])",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should preserve special characters
        assert len(validated) == 1
    
    def test_mathematical_notation(self):
        """Test that mathematical notation is preserved."""
        source_text = "The algorithm complexity is O(n²) with space requirements of Θ(n log n)."
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="math_notation.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="method",
                text="algorithm complexity is O(n²) with space requirements of Θ(n log n)",
                section="methodology",
                confidence=0.90,
                evidence_type="theoretical"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should preserve mathematical notation
        assert len(validated) == 1
    
    def test_citation_references(self):
        """Test that citation references are preserved."""
        source_text = "Previous work (Smith et al., 2019; Johnson & Lee, 2020) established the foundation."
        
        page = PdfPage(
            page_number=1,
            text=source_text,
            char_count=len(source_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="citations.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        elements = (
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="claim",
                text="Previous work (Smith et al., 2019; Johnson & Lee, 2020) established the foundation",
                section="related_work",
                confidence=0.85,
                evidence_type="theoretical"
            ),
        )
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        # Should preserve citation format
        assert len(validated) == 1


class TestVerbatimPerformance:
    """Test verbatim validation performance with large documents."""
    
    def test_large_document_validation(self):
        """Test verbatim validation performance with large academic papers."""
        # Create a realistic large document (simulate 20-page paper)
        section_text = "This is a test sentence that appears in the academic paper. " * 100
        large_text = section_text * 20  # ~120KB of text
        
        page = PdfPage(
            page_number=1,
            text=large_text,
            char_count=len(large_text),
            dimensions=(612.0, 792.0),
            char_positions=()
        )
        
        pdf_content = PdfContent(
            file_path="large_document.pdf",
            total_pages=1,
            pages=(page,),
            extraction_metadata={}
        )
        
        # Create many elements to validate
        elements = tuple(
            ExtractedElement.create_with_auto_id(
                paper_id="test-paper",
                element_type="finding",
                text=f"This is a test sentence that appears in the academic paper number {i}",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            )
            for i in range(50)  # 50 elements
        )
        
        import time
        start_time = time.time()
        
        validated = validate_extracted_elements(elements, pdf_content)
        
        elapsed = time.time() - start_time
        
        # Should complete validation quickly (< 1 second for this size)
        assert elapsed < 1.0
        
        # Most should fail validation (since we added numbers)
        # But the validation process should complete successfully
        assert isinstance(validated, tuple)


if __name__ == "__main__":
    pytest.main([__file__])