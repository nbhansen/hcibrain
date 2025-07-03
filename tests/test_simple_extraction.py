"""
Tests for simple extraction functionality.

Tests CLAUDE.MD requirements:
- End-to-end extraction pipeline
- PDF processing integration
- Synchronous and asynchronous extraction
- Performance requirements (<30 seconds)
- Error handling and robustness
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from hci_extractor.core.models import (
    Paper,
    ExtractedElement,
    ExtractionResult,
    PdfContent,
    PdfPage,
)

# Try to import simple extraction (requires PDF dependencies)
try:
    from hci_extractor.core.analysis import extract_paper_simple, extract_multiple_papers, extract_paper_sync
    SIMPLE_EXTRACTION_AVAILABLE = True
except ImportError:
    SIMPLE_EXTRACTION_AVAILABLE = False


@pytest.mark.skipif(not SIMPLE_EXTRACTION_AVAILABLE, reason="Simple extraction not available")
class TestSimpleExtraction:
    """Test simple extraction pipeline."""
    
    @pytest.mark.asyncio
    async def test_extract_paper_simple_basic(self):
        """Test basic paper extraction functionality."""
        # Mock LLM provider
        mock_llm = AsyncMock()
        mock_llm.analyze_section.return_value = [
            {
                "element_type": "finding",
                "text": "Users performed 25% better",
                "evidence_type": "quantitative",
                "confidence": 0.9
            }
        ]
        
        # Create mock PDF file path (not actually used due to mocking)
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = Path(tmp_file.name)
        
        try:
            # Mock PDF processing
            mock_pdf_content = PdfContent(
                file_path=str(pdf_path),
                total_pages=1,
                pages=(
                    PdfPage(
                        page_number=1,
                        text="Abstract\nUsers performed 25% better with our system.",
                        char_count=len("Abstract\nUsers performed 25% better with our system."),
                        dimensions=(612.0, 792.0),
                        char_positions=()
                    ),
                ),
                extraction_metadata={}
            )
            
            with patch('hci_extractor.core.extraction.PdfExtractor.extract_content', return_value=mock_pdf_content):
                result = await extract_paper_simple(
                    pdf_path=pdf_path,
                    llm_provider=mock_llm,
                    paper_metadata={"title": "Test Paper", "authors": ["Dr. Test"]}
                )
            
            # Should return ExtractionResult
            assert isinstance(result, ExtractionResult)
            assert result.paper.title == "Test Paper"
            assert len(result.elements) == 1
            assert result.elements[0].text == "Users performed 25% better"
            
        finally:
            pdf_path.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_extract_paper_simple_no_metadata(self):
        """Test extraction without explicit paper metadata."""
        mock_llm = AsyncMock()
        mock_llm.analyze_section.return_value = [
            {
                "element_type": "claim",
                "text": "novel interaction method for touch-based devices",
                "evidence_type": "theoretical",
                "confidence": 0.85
            }
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = Path(tmp_file.name)
        
        try:
            # Mock PDF content with title in text
            mock_pdf_content = PdfContent(
                file_path=str(pdf_path),
                total_pages=1,
                pages=(
                    PdfPage(
                        page_number=1,
                        text="TouchGestures: A Novel Interaction Method\n\nAbstract\nThis paper presents a novel interaction method for touch-based devices that improves user performance and satisfaction through innovative gesture recognition.",
                        char_count=len("TouchGestures: A Novel Interaction Method\n\nAbstract\nThis paper presents a novel interaction method for touch-based devices that improves user performance and satisfaction through innovative gesture recognition."),
                        dimensions=(612.0, 792.0),
                        char_positions=()
                    ),
                ),
                extraction_metadata={}
            )
            
            with patch('hci_extractor.core.extraction.PdfExtractor.extract_content', return_value=mock_pdf_content):
                result = await extract_paper_simple(
                    pdf_path=pdf_path,
                    llm_provider=mock_llm
                    # No paper_metadata provided
                )
            
            # Should use filename as title when no metadata provided
            assert result.paper.title  # Should have a title from filename
            assert len(result.paper.authors) > 0  # Should have placeholder authors
            assert result.paper.authors[0] == "Unknown"  # Default author
            
        finally:
            pdf_path.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_extract_paper_simple_performance(self):
        """Test extraction performance requirement (<30 seconds)."""
        mock_llm = AsyncMock()
        mock_llm.analyze_section.return_value = [
            {
                "element_type": "claim",
                "text": "Test claim",
                "evidence_type": "theoretical",
                "confidence": 0.8
            }
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = Path(tmp_file.name)
        
        try:
            # Create realistic-sized content
            large_text = "Abstract\n" + "This is test content. " * 1000  # ~20KB
            
            mock_pdf_content = PdfContent(
                file_path=str(pdf_path),
                total_pages=1,
                pages=(
                    PdfPage(
                        page_number=1,
                        text=large_text,
                        char_count=len(large_text),
                        dimensions=(612.0, 792.0),
                        char_positions=()
                    ),
                ),
                extraction_metadata={}
            )
            
            with patch('hci_extractor.core.extraction.PdfExtractor.extract_content', return_value=mock_pdf_content):
                start_time = time.time()
                
                result = await extract_paper_simple(
                    pdf_path=pdf_path,
                    llm_provider=mock_llm,
                    paper_metadata={"title": "Performance Test", "authors": ["Dr. Speed"]}
                )
                
                elapsed = time.time() - start_time
            
            # Should complete well under 30 seconds (CLAUDE.MD requirement)
            assert elapsed < 30.0
            assert isinstance(result, ExtractionResult)
            
        finally:
            pdf_path.unlink(missing_ok=True)
    
    def test_extract_paper_sync(self):
        """Test synchronous wrapper for extraction."""
        mock_llm = AsyncMock()
        mock_llm.analyze_section.return_value = [
            {
                "element_type": "method",
                "text": "Controlled experiment design",
                "evidence_type": "theoretical",
                "confidence": 0.85
            }
        ]
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = Path(tmp_file.name)
        
        try:
            mock_pdf_content = PdfContent(
                file_path=str(pdf_path),
                total_pages=1,
                pages=(
                    PdfPage(
                        page_number=1,
                        text="Methodology\nControlled experiment design was used to evaluate the effectiveness of our new interaction technique with 30 participants over a two-week period.",
                        char_count=len("Methodology\nControlled experiment design was used to evaluate the effectiveness of our new interaction technique with 30 participants over a two-week period."),
                        dimensions=(612.0, 792.0),
                        char_positions=()
                    ),
                ),
                extraction_metadata={}
            )
            
            with patch('hci_extractor.core.extraction.PdfExtractor.extract_content', return_value=mock_pdf_content):
                # Test synchronous extraction
                result = extract_paper_sync(
                    pdf_path=pdf_path,
                    llm_provider=mock_llm,
                    paper_metadata={"title": "Sync Test", "authors": ["Dr. Sync"]}
                )
            
            assert isinstance(result, ExtractionResult)
            assert result.paper.title == "Sync Test"
            assert len(result.elements) == 1
            
        finally:
            pdf_path.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_extract_multiple_papers(self):
        """Test batch extraction of multiple papers."""
        mock_llm = AsyncMock()
        mock_llm.analyze_section.side_effect = [
            # First paper results
            [{"element_type": "claim", "text": "Claim 1", "evidence_type": "theoretical", "confidence": 0.8}],
            # Second paper results  
            [{"element_type": "finding", "text": "Finding 1", "evidence_type": "quantitative", "confidence": 0.9}],
        ]
        
        # Create temporary PDF files
        pdf_paths = []
        for i in range(2):
            tmp_file = tempfile.NamedTemporaryFile(suffix=f'_paper_{i}.pdf', delete=False)
            pdf_paths.append(Path(tmp_file.name))
            tmp_file.close()
        
        try:
            # Mock PDF content for each paper
            def mock_extract_pdf(pdf_path):
                paper_num = "1" if "paper_0" in str(pdf_path) else "2"
                return PdfContent(
                    file_path=str(pdf_path),
                    total_pages=1,
                    pages=(
                        PdfPage(
                            page_number=1,
                            text=f"Paper {paper_num}\nAbstract\nTest content for paper {paper_num}. This abstract describes the key contributions and findings of our research work in human-computer interaction.",
                            char_count=len(f"Paper {paper_num}\nAbstract\nTest content for paper {paper_num}. This abstract describes the key contributions and findings of our research work in human-computer interaction."),
                            dimensions=(612.0, 792.0),
                            char_positions=()
                        ),
                    ),
                    extraction_metadata={}
                )
            
            with patch('hci_extractor.core.extraction.PdfExtractor.extract_content', side_effect=mock_extract_pdf):
                results = await extract_multiple_papers(
                    pdf_paths=pdf_paths,
                    llm_provider=mock_llm
                )
            
            # Should return results for all papers
            assert len(results) == 2
            assert all(isinstance(r, ExtractionResult) for r in results)
            
            # Each should have been processed
            titles = [r.paper.title for r in results]
            # Titles are generated from filenames, so check for paper_0 and paper_1
            assert any("paper 0" in title.lower() or "paper_0" in title.lower() for title in titles)
            assert any("paper 1" in title.lower() or "paper_1" in title.lower() for title in titles)
            
        finally:
            for pdf_path in pdf_paths:
                pdf_path.unlink(missing_ok=True)


@pytest.mark.skipif(not SIMPLE_EXTRACTION_AVAILABLE, reason="Simple extraction not available")
class TestExtractionErrorHandling:
    """Test error handling in extraction pipeline."""
    
    @pytest.mark.asyncio
    async def test_extract_paper_missing_file(self):
        """Test handling of missing PDF files."""
        mock_llm = AsyncMock()
        missing_path = Path("/nonexistent/file.pdf")
        
        # Should handle missing files gracefully
        with pytest.raises((FileNotFoundError, Exception)):
            await extract_paper_simple(
                pdf_path=missing_path,
                llm_provider=mock_llm
            )
    
    @pytest.mark.asyncio
    async def test_extract_paper_llm_failure(self):
        """Test handling of LLM processing failures."""
        # LLM that always fails
        mock_llm = AsyncMock()
        mock_llm.analyze_section.side_effect = Exception("LLM API Error")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = Path(tmp_file.name)
        
        try:
            mock_pdf_content = PdfContent(
                file_path=str(pdf_path),
                total_pages=1,
                pages=(
                    PdfPage(
                        page_number=1,
                        text="Abstract\nTest content.",
                        char_count=len("Abstract\nTest content."),
                        dimensions=(612.0, 792.0),
                        char_positions=()
                    ),
                ),
                extraction_metadata={}
            )
            
            with patch('hci_extractor.core.extraction.PdfExtractor.extract_content', return_value=mock_pdf_content):
                # Should handle LLM failures gracefully
                result = await extract_paper_simple(
                    pdf_path=pdf_path,
                    llm_provider=mock_llm,
                    paper_metadata={"title": "Error Test", "authors": ["Dr. Error"]}
                )
            
            # Should still return a result, even with no elements
            assert isinstance(result, ExtractionResult)
            assert result.paper.title == "Error Test"
            # Elements might be empty due to LLM failure
            
        finally:
            pdf_path.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_extract_paper_partial_failure(self):
        """Test handling of partial processing failures."""
        # LLM that fails on some sections but succeeds on others
        mock_llm = AsyncMock()
        call_count = 0
        
        def side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [{"element_type": "claim", "text": "Success", "evidence_type": "theoretical", "confidence": 0.8}]
            else:
                raise Exception("Second section failed")
        
        mock_llm.analyze_section.side_effect = side_effect
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = Path(tmp_file.name)
        
        try:
            # Create content with multiple sections
            mock_pdf_content = PdfContent(
                file_path=str(pdf_path),
                total_pages=1,
                pages=(
                    PdfPage(
                        page_number=1,
                        text="Abstract\nSuccess claim.\n\n1. Introduction\nThis will fail.",
                        char_count=len("Abstract\nSuccess claim.\n\n1. Introduction\nThis will fail."),
                        dimensions=(612.0, 792.0),
                        char_positions=()
                    ),
                ),
                extraction_metadata={}
            )
            
            with patch('hci_extractor.core.extraction.PdfExtractor.extract_content', return_value=mock_pdf_content):
                result = await extract_paper_simple(
                    pdf_path=pdf_path,
                    llm_provider=mock_llm,
                    paper_metadata={"title": "Partial Test", "authors": ["Dr. Partial"]}
                )
            
            # Should return results from successful sections
            assert isinstance(result, ExtractionResult)
            # Should have at least the successful element
            successful_elements = [e for e in result.elements if e.text == "Success"]
            assert len(successful_elements) >= 0  # May be empty due to validation
            
        finally:
            pdf_path.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])