"""Map extracted text to PDF coordinates for highlighting."""

import logging
from typing import Any, Optional, Tuple

from fuzzywuzzy import fuzz

from hci_extractor.core.models.pdf_models import (
    ElementCoordinates,
    ExtractedElement,
    PdfContent,
)

logger = logging.getLogger(__name__)


class CoordinateMapper:
    """Map extracted text back to PDF coordinates."""

    def __init__(self, fuzzy_match_threshold: float = 70.0):
        """Initialize coordinate mapper.

        Args:
            fuzzy_match_threshold: Minimum similarity score for fuzzy matching
        """
        self.fuzzy_match_threshold = fuzzy_match_threshold

    def map_element_coordinates(
        self, element: ExtractedElement, pdf_content: PdfContent,
    ) -> Optional[ElementCoordinates]:
        """Map an extracted element to PDF coordinates.

        Args:
            element: The extracted element to map
            pdf_content: PDF content with character positions

        Returns:
            ElementCoordinates if mapping successful, None otherwise
        """
        element_text = element.text.strip()
        if not element_text:
            return None

        # Try exact match first
        coordinates = self._find_exact_match(element_text, pdf_content)
        if coordinates:
            return coordinates

        # Try fuzzy matching if exact match fails
        return self._find_fuzzy_match(element_text, pdf_content)

    def _find_exact_match(
        self, text: str, pdf_content: PdfContent,
    ) -> Optional[ElementCoordinates]:
        """Find exact text match in PDF content."""
        full_text = pdf_content.full_text
        start_idx = full_text.find(text)

        if start_idx == -1:
            return None

        end_idx = start_idx + len(text)
        return self._create_coordinates_from_indices(
            start_idx, end_idx, pdf_content,
        )

    def _find_fuzzy_match(
        self, text: str, pdf_content: PdfContent,
    ) -> Optional[ElementCoordinates]:
        """Find fuzzy text match in PDF content."""
        full_text = pdf_content.full_text
        text_length = len(text)
        best_match_score = 0.0
        best_match_start = -1

        # Use sliding window approach for fuzzy matching
        for start_idx in range(len(full_text) - text_length + 1):
            window = full_text[start_idx:start_idx + text_length]
            score = fuzz.ratio(text, window)

            if score > best_match_score and score >= self.fuzzy_match_threshold:
                best_match_score = score
                best_match_start = start_idx

        if best_match_start == -1:
            logger.warning(f"Could not find fuzzy match for text: {text[:50]}...")
            return None

        end_idx = best_match_start + text_length
        return self._create_coordinates_from_indices(
            best_match_start, end_idx, pdf_content,
        )

    def _create_coordinates_from_indices(
        self, start_idx: int, end_idx: int, pdf_content: PdfContent,
    ) -> Optional[ElementCoordinates]:
        """Create ElementCoordinates from character indices."""
        start_positions = self._get_character_positions(start_idx, pdf_content)
        end_positions = self._get_character_positions(end_idx - 1, pdf_content)

        if not start_positions or not end_positions:
            return None

        start_page, start_char_pos = start_positions
        end_page, end_char_pos = end_positions

        # Handle multi-page text (use start page for simplicity)
        if start_page != end_page:
            logger.info(f"Multi-page text detected, using start page: {start_page}")

        # Calculate bounding box
        x = min(start_char_pos.x, end_char_pos.x)
        y = min(start_char_pos.y, end_char_pos.y)
        width = max(start_char_pos.bbox[2], end_char_pos.bbox[2]) - x
        height = max(start_char_pos.bbox[3], end_char_pos.bbox[3]) - y

        return ElementCoordinates(
            page_number=start_page,
            x=x,
            y=y,
            width=width,
            height=height,
            char_start=start_idx,
            char_end=end_idx,
        )

    def _get_character_positions(
        self, char_idx: int, pdf_content: PdfContent,
    ) -> Optional[Tuple[int, Any]]:
        """Get character position data for a given character index."""
        current_idx = 0

        for page in pdf_content.pages:
            if current_idx + page.char_count > char_idx:
                # Character is on this page
                local_idx = char_idx - current_idx
                if local_idx < len(page.char_positions):
                    return page.page_number, page.char_positions[local_idx]
                break
            current_idx += page.char_count

        return None

    def map_multiple_elements(
        self, elements: Tuple[ExtractedElement, ...], pdf_content: PdfContent,
    ) -> Tuple[ExtractedElement, ...]:
        """Map coordinates for multiple elements."""
        mapped_elements = []

        for element in elements:
            coordinates = self.map_element_coordinates(element, pdf_content)
            if coordinates:
                # Create new element with coordinates
                mapped_element = ExtractedElement(
                    element_id=element.element_id,
                    paper_id=element.paper_id,
                    element_type=element.element_type,
                    text=element.text,
                    section=element.section,
                    confidence=element.confidence,
                    evidence_type=element.evidence_type,
                    page_number=element.page_number,
                    coordinates=coordinates,
                    supporting_evidence=element.supporting_evidence,
                    methodology_context=element.methodology_context,
                    study_population=element.study_population,
                    limitations=element.limitations,
                    surrounding_context=element.surrounding_context,
                )
                mapped_elements.append(mapped_element)
            else:
                # Keep original element without coordinates
                mapped_elements.append(element)

        return tuple(mapped_elements)
