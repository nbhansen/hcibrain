"""Tests for PDF extraction functionality."""

import tempfile
from pathlib import Path

import pytest

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.extraction.pdf_extractor import PdfExtractor


class TestPdfExtraction:
    """Test PDF text extraction functionality."""

    @pytest.fixture
    def test_config(self):
        """Create test configuration for PDF extractor."""
        config_dict = {
            "api": {"provider_type": "gemini", "gemini_api_key": "test-key"},
            "extraction": {
                "max_file_size_mb": 50,
                "timeout_seconds": 30.0,
                "normalize_text": True,
                "extract_positions": True,
            },
            "analysis": {"model_name": "gemini-1.5-flash"},
            "general": {"prompts_directory": "prompts"},
        }
        return ExtractorConfig.from_dict(config_dict)

    @pytest.fixture
    def pdf_extractor(self, test_config):
        """Create PdfExtractor instance for testing."""
        return PdfExtractor(config=test_config)

    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content for testing."""
        return """
        Test Paper Title

        Abstract: This is a test paper about machine learning research.

        1. Introduction
        The goal of this research is to improve accuracy in neural networks.
        We used a novel approach combining attention mechanisms.
        Our results show 15% improvement over baseline methods.

        2. Methods
        We employed deep learning techniques with the following methodology:
        - Data preprocessing with normalization
        - Model training with cross-validation
        - Evaluation using standard metrics

        3. Results
        The experimental results demonstrate significant improvements:
        - Accuracy increased from 85% to 97%
        - Processing time reduced by 30%
        - Memory usage optimized by 20%

        4. Conclusion
        This work shows that our method achieves better performance.
        """

    def test_extract_content_success(self, pdf_extractor, sample_pdf_content):
        """Test successful PDF content extraction."""
        # Create a simple PDF using PyMuPDF
        import fitz

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

            # Create a simple PDF document for testing
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), sample_pdf_content, fontsize=12)
            doc.save(temp_path)
            doc.close()

            try:
                result = pdf_extractor.extract_content(temp_path)

                # Test the actual interface
                assert hasattr(result, "full_text")
                assert hasattr(result, "extraction_metadata")
                assert isinstance(result.full_text, str)
                assert len(result.full_text) > 0

                # Verify some content is extracted
                assert len(result.full_text.strip()) >= 100

            finally:
                temp_path.unlink(missing_ok=True)

    def test_extract_content_file_not_found(self, pdf_extractor):
        """Test extraction with non-existent file."""
        non_existent_path = Path("/non/existent/file.pdf")

        from hci_extractor.core.models.exceptions import (
            FileNotFoundError as PDFFileNotFoundError,
        )

        with pytest.raises(PDFFileNotFoundError):
            pdf_extractor.extract_content(non_existent_path)

    def test_extract_content_invalid_file_type(self, pdf_extractor):
        """Test extraction with non-PDF file."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"This is not a PDF")
            temp_path = Path(temp_file.name)

            try:
                from hci_extractor.core.models.exceptions import InvalidFileTypeError

                with pytest.raises(InvalidFileTypeError):
                    pdf_extractor.extract_content(temp_path)
            finally:
                temp_path.unlink(missing_ok=True)

    def test_extracted_content_structure(self, pdf_extractor, sample_pdf_content):
        """Test that extracted content has expected structure."""
        import fitz

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

            # Create test PDF
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), sample_pdf_content, fontsize=12)
            doc.save(temp_path)
            doc.close()

            try:
                result = pdf_extractor.extract_content(temp_path)

                # Test actual structure
                assert hasattr(result, "full_text")
                assert hasattr(result, "extraction_metadata")
                assert hasattr(result, "pages")
                assert hasattr(result, "total_pages")
                # extraction_metadata is MappingProxyType (immutable) following CLAUDE.md
                import types

                assert isinstance(result.extraction_metadata, types.MappingProxyType)
                assert result.total_pages >= 1
                assert len(result.pages) == result.total_pages

            finally:
                temp_path.unlink(missing_ok=True)

    def test_extraction_performance_limits(self, pdf_extractor, sample_pdf_content):
        """Test that extraction respects time limits."""
        import time

        import fitz

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

            # Create test PDF
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 50), sample_pdf_content, fontsize=12)
            doc.save(temp_path)
            doc.close()

            try:
                start_time = time.time()
                result = pdf_extractor.extract_content(temp_path)
                end_time = time.time()

                # Extraction should complete within reasonable time
                extraction_time = end_time - start_time
                assert extraction_time < 30.0  # 30 second limit

                # Should also be recorded in metadata
                assert "extraction_time_seconds" in result.extraction_metadata

            finally:
                temp_path.unlink(missing_ok=True)
