"""PDF text extraction with character-level positioning."""

import logging
import types
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.models import (
    CharacterPosition,
    CorruptedFileError,
    ExtractionQualityError,
    NoTextLayerError,
    PasswordProtectedError,
    PdfContent,
    PdfError,
    PdfPage,
)

logger = logging.getLogger(__name__)


class PdfExtractor:
    """Extract text from PDFs with character-level positioning."""

    def __init__(self, config: ExtractorConfig):
        """Initialize extractor with configuration.

        Args:
            config: Configuration object (required)
        """
        self.config = config
        self.min_text_length = 100  # Minimum text length to consider valid

    def extract_content(self, file_path: Path) -> PdfContent:
        """Extract complete PDF content with positioning data."""
        logger.info(f"Starting extraction for {file_path}")

        if not file_path.exists():
            raise PdfError(f"File not found: {file_path}")

        if not file_path.suffix.lower() == ".pdf":
            raise PdfError(f"Not a PDF file: {file_path}")

        try:
            doc = fitz.open(str(file_path))
        except fitz.FileDataError as e:
            if "password" in str(e).lower():
                raise PasswordProtectedError(f"PDF requires password: {file_path}")
            else:
                raise CorruptedFileError(f"Cannot open PDF: {e}")
        except Exception as e:
            raise PdfError(f"Unexpected error opening PDF: {e}")

        try:
            pages = []
            extraction_start = datetime.now()

            for page_num in range(len(doc)):
                page = doc[page_num]
                pdf_page = self._extract_page(page, page_num + 1)
                pages.append(pdf_page)

            if not pages:
                raise ExtractionQualityError("No pages extracted from PDF")

            # Check overall text quality
            total_text = "\n".join(page.text for page in pages)
            if len(total_text.strip()) < self.min_text_length:
                raise NoTextLayerError(
                    f"Insufficient text extracted ({len(total_text)} chars). "
                    "PDF may be scanned images without text layer."
                )

            extraction_time = (datetime.now() - extraction_start).total_seconds()

            metadata = {
                "extraction_time_seconds": extraction_time,
                "file_size_bytes": file_path.stat().st_size,
                "pymupdf_version": fitz.version[0],
                "total_chars": len(total_text),
            }

            content = PdfContent(
                file_path=str(file_path),
                total_pages=len(pages),
                pages=tuple(pages),
                extraction_metadata=types.MappingProxyType(metadata),
                created_at=extraction_start,
            )

            logger.info(
                f"Successfully extracted {len(pages)} pages, "
                f"{len(total_text)} chars in {extraction_time:.2f}s"
            )

            return content

        finally:
            doc.close()

    def _extract_page(self, page: fitz.Page, page_num: int) -> PdfPage:
        """Extract single page with character positions."""
        # Get page dimensions
        rect = page.rect
        dimensions = (rect.width, rect.height)

        # Extract text with detailed positioning
        text_dict = page.get_text("dict")

        # Build text and character positions
        page_text = ""
        char_positions = []
        char_index = 0

        for block in text_dict["blocks"]:
            if "lines" not in block:  # Skip image blocks
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    span_text = span["text"]
                    span_bbox = span["bbox"]

                    # Add character positions for this span
                    for i, char in enumerate(span_text):
                        # Approximate character position within span
                        char_x = span_bbox[0] + (i / len(span_text)) * (
                            span_bbox[2] - span_bbox[0]
                        )
                        char_pos = CharacterPosition(
                            char_index=char_index,
                            page_number=page_num,
                            x=char_x,
                            y=span_bbox[1],
                            bbox=span_bbox,
                        )
                        char_positions.append(char_pos)
                        char_index += 1

                    page_text += span_text

                # Add line break
                if page_text and not page_text.endswith("\n"):
                    page_text += "\n"
                    char_positions.append(
                        CharacterPosition(
                            char_index=char_index,
                            page_number=page_num,
                            x=0,
                            y=line["bbox"][3],
                            bbox=(0, line["bbox"][3], 0, line["bbox"][3]),
                        )
                    )
                    char_index += 1

        return PdfPage(
            page_number=page_num,
            text=page_text,
            char_count=len(page_text),
            dimensions=dimensions,
            char_positions=tuple(char_positions),
        )

    def validate_extraction(self, content: PdfContent) -> bool:
        """Validate extraction quality and completeness."""
        # Check basic requirements
        if content.total_pages == 0:
            return False

        if content.total_chars < self.min_text_length:
            return False

        # Verify page sequence
        for i, page in enumerate(content.pages):
            if page.page_number != i + 1:
                return False

        # Check for reasonable text distribution
        avg_chars_per_page = content.total_chars / content.total_pages
        if avg_chars_per_page < 50:  # Very sparse text
            return False

        return True
