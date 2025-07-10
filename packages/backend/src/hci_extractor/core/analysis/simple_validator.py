"""
Simple text validation - just the basics that matter.

No complex statistical analysis, just:
1. Does the extracted text exist in the source PDF?
2. Remove exact duplicates
3. Basic quality checks

Keep it simple!
"""

import logging
from typing import Any, Set, Tuple

from hci_extractor.core.models import ExtractedElement, PdfContent

logger = logging.getLogger(__name__)


def validate_extracted_elements(
    elements: Tuple[ExtractedElement, ...],
    pdf_content: PdfContent,
) -> Tuple[ExtractedElement, ...]:
    """
    Simple validation: verify text exists in source and remove duplicates.

    Args:
        elements: Extracted elements to validate
        pdf_content: Original PDF content for verification

    Returns:
        Filtered tuple of validated elements
    """
    if not elements:
        return ()

    logger.info(f"Validating {len(elements)} extracted elements...")

    # Get full PDF text for searching
    full_text = _get_full_pdf_text(pdf_content)

    # Step 1: Check if text exists in source (verbatim validation)
    verified_elements = []
    for element in elements:
        if _text_exists_in_source(element.text, full_text):
            verified_elements.append(element)
        else:
            logger.warning(f"Text not found in source: '{element.text[:50]}...'")

    logger.info(
        f"✅ Verbatim check: {len(verified_elements)}/{len(elements)} elements verified"
    )

    # Step 2: Remove exact duplicates
    unique_elements = _remove_duplicates(verified_elements)

    logger.info(f"✅ Deduplication: {len(unique_elements)} unique elements remaining")

    # Step 3: Basic quality filtering
    quality_elements = _basic_quality_filter(unique_elements)

    logger.info(
        f"✅ Quality filter: {len(quality_elements)} elements pass quality check",
    )

    return tuple(quality_elements)


def _get_full_pdf_text(pdf_content: PdfContent) -> str:
    """Get complete PDF text for searching."""
    return "\n".join(page.text for page in pdf_content.pages)


def _text_exists_in_source(extracted_text: str, full_text: str) -> bool:
    """
    Check if extracted text exists verbatim in the source.

    Simple string search - if the text is in the PDF, it should be found.
    """
    if not extracted_text.strip():
        return False

    # Clean up whitespace for more flexible matching
    cleaned_extracted = " ".join(extracted_text.split())
    cleaned_full = " ".join(full_text.split())

    return cleaned_extracted.lower() in cleaned_full.lower()


def _remove_duplicates(elements: list[ExtractedElement]) -> list[ExtractedElement]:
    """
    Remove elements with identical text.

    Keep the first occurrence of each unique text.
    """
    seen_texts: Set[str] = set()
    unique_elements = []

    for element in elements:
        # Normalize text for comparison
        normalized_text = " ".join(element.text.split()).lower()

        if normalized_text not in seen_texts:
            seen_texts.add(normalized_text)
            unique_elements.append(element)
        else:
            logger.debug(f"Removing duplicate: '{element.text[:30]}...'")

    return unique_elements


def _basic_quality_filter(elements: list[ExtractedElement]) -> list[ExtractedElement]:
    """
    Basic quality filtering - remove obviously bad extractions.

    Simple rules:
    - Text must be at least 10 characters
    - Text must contain at least 2 words
    - Text shouldn't be just numbers or punctuation
    """
    quality_elements = []

    for element in elements:
        text = element.text.strip()

        # Too short
        if len(text) < 10:
            logger.debug(f"Removing too short: '{text}'")
            continue

        # Must have multiple words
        words = text.split()
        if len(words) < 2:
            logger.debug(f"Removing single word: '{text}'")
            continue

        # Must contain letters (not just numbers/punctuation)
        if not any(c.isalpha() for c in text):
            logger.debug(f"Removing no letters: '{text}'")
            continue

        quality_elements.append(element)

    return quality_elements


def quick_validation_stats(
    original_elements: Tuple[ExtractedElement, ...],
    validated_elements: Tuple[ExtractedElement, ...],
) -> dict[str, Any]:
    """
    Quick validation statistics for logging/debugging.

    Returns:
        Dict with validation metrics
    """
    if not original_elements:
        return {"status": "no_elements_to_validate"}

    return {
        "original_count": len(original_elements),
        "validated_count": len(validated_elements),
        "removed_count": len(original_elements) - len(validated_elements),
        "validation_rate": len(validated_elements) / len(original_elements),
        "sections_represented": len({e.section for e in validated_elements}),
        "element_types": {
            element_type: len(
                [e for e in validated_elements if e.element_type == element_type],
            )
            for element_type in ["claim", "finding", "method"]
        },
    }
