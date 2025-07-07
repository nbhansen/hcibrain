"""
Pure function for detecting paper sections following IMRaD structure.

This module implements the Single Responsibility Principle (SRP) by focusing
solely on section detection. It's a pure function with no side effects,
returning immutable DetectedSection objects.
"""

import logging
import re
from typing import Tuple

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.models import DetectedSection, PdfContent

logger = logging.getLogger(__name__)


def detect_sections(
    pdf_content: PdfContent, config: ExtractorConfig
) -> Tuple[DetectedSection, ...]:
    """
    Detect academic paper sections from PDF content.

    Pure function that identifies sections following IMRaD structure
    (Introduction, Methods, Results, and Discussion) plus common variations.

    Args:
        pdf_content: Immutable PDF content to analyze
        config: Configuration object (required)

    Returns:
        Immutable tuple of detected sections, ordered by appearance

    Raises:
        ValueError: If PDF content is invalid
    """
    # Config is now required parameter
    if not pdf_content.pages:
        return ()

    # Get full text for analysis
    full_text = _get_full_text(pdf_content)
    if not full_text.strip():
        return ()

    logger.info(f"Detecting sections in document with {len(full_text)} characters")
    logger.debug(f"First 200 chars of text: {repr(full_text[:200])}")

    # Define section patterns following academic conventions
    section_patterns = _get_section_patterns()

    # Find all section headers
    detected_sections = []
    for pattern_name, patterns in section_patterns.items():
        sections = _find_sections_by_pattern(
            full_text, pdf_content, pattern_name, patterns, config
        )
        detected_sections.extend(sections)

    # Sort by character position and resolve overlaps
    detected_sections.sort(key=lambda s: s.char_start)
    resolved_sections = _resolve_overlapping_sections(detected_sections)

    # Log section size warnings
    _log_section_size_warnings(resolved_sections)

    logger.info(f"Detected {len(resolved_sections)} sections")
    return tuple(resolved_sections)


def _get_full_text(pdf_content: PdfContent) -> str:
    """Extract full text from PDF content with newlines between pages."""
    return "\n".join(page.text for page in pdf_content.pages)


def _get_section_patterns() -> dict[str, list[str]]:
    """
    Define regex patterns for academic section headers.

    Returns patterns ordered by specificity (most specific first) to handle
    overlapping matches correctly.
    """
    return {
        # Abstract - usually at the beginning
        "abstract": [
            r"(?i)^\s*abstract\s*$",
            r"(?i)^\s*abstract\s*[:]\s*$",
            r"(?i)\n\s*abstract\s*\n",
        ],
        # Introduction section
        "introduction": [
            r"(?i)^\s*1\.?\s*introduction\s*$",
            r"(?i)^\s*introduction\s*$",
            r"(?i)\n\s*1\.?\s*introduction\s*\n",
            r"(?i)\n\s*introduction\s*\n",
        ],
        # Related work / Background / Literature review
        "related_work": [
            r"(?i)^\s*\d+\.?\s*related\s+work\s*$",
            r"(?i)^\s*\d+\.?\s*background\s*$",
            r"(?i)^\s*\d+\.?\s*literature\s+review\s*$",
            r"(?i)^\s*\d+\.?\s*prior\s+work\s*$",
            r"(?i)\n\s*\d+\.?\s*related\s+work\s*\n",
            r"(?i)\n\s*\d+\.?\s*background\s*\n",
        ],
        # Methodology / Methods
        "methodology": [
            r"(?i)^\s*\d+\.?\s*methodology\s*$",
            r"(?i)^\s*\d+\.?\s*methods?\s*$",
            r"(?i)^\s*\d+\.?\s*approach\s*$",
            r"(?i)^\s*\d+\.?\s*experimental\s+design\s*$",
            r"(?i)\n\s*\d+\.?\s*methodology\s*\n",
            r"(?i)\n\s*\d+\.?\s*methods?\s*\n",
            # Unnumbered sections (common in test data)
            r"(?i)^\s*methodology\s*$",
            r"(?i)^\s*methods?\s*$",
        ],
        # Design section (common in HCI papers)
        "design": [
            r"(?i)^\s*\d+\.?\s*design\s*$",
            r"(?i)^\s*\d+\.?\s*system\s+design\s*$",
            r"(?i)^\s*\d+\.?\s*interface\s+design\s*$",
            r"(?i)\n\s*\d+\.?\s*design\s*\n",
        ],
        # Implementation
        "implementation": [
            r"(?i)^\s*\d+\.?\s*implementation\s*$",
            r"(?i)^\s*\d+\.?\s*system\s+implementation\s*$",
            r"(?i)\n\s*\d+\.?\s*implementation\s*\n",
        ],
        # Results / Findings
        "results": [
            r"(?i)^\s*\d+\.?\s*results?\s*$",
            r"(?i)^\s*\d+\.?\s*findings?\s*$",
            r"(?i)^\s*\d+\.?\s*experimental\s+results?\s*$",
            r"(?i)\n\s*\d+\.?\s*results?\s*\n",
            r"(?i)\n\s*\d+\.?\s*findings?\s*\n",
        ],
        # Evaluation (common in HCI papers)
        "evaluation": [
            r"(?i)^\s*\d+\.?\s*evaluation\s*$",
            r"(?i)^\s*\d+\.?\s*user\s+study\s*$",
            r"(?i)^\s*\d+\.?\s*study\s*$",
            r"(?i)\n\s*\d+\.?\s*evaluation\s*\n",
        ],
        # Discussion
        "discussion": [
            r"(?i)^\s*\d+\.?\s*discussion\s*$",
            r"(?i)^\s*\d+\.?\s*analysis\s*$",
            r"(?i)^\s*\d+\.?\s*interpretation\s*$",
            r"(?i)\n\s*\d+\.?\s*discussion\s*\n",
        ],
        # Conclusion
        "conclusion": [
            r"(?i)^\s*\d+\.?\s*conclusions?\s*$",
            r"(?i)^\s*\d+\.?\s*summary\s*$",
            r"(?i)^\s*\d+\.?\s*final\s+remarks\s*$",
            r"(?i)\n\s*\d+\.?\s*conclusions?\s*\n",
        ],
        # Future work
        "future_work": [
            r"(?i)^\s*\d+\.?\s*future\s+work\s*$",
            r"(?i)^\s*\d+\.?\s*future\s+directions\s*$",
            r"(?i)\n\s*\d+\.?\s*future\s+work\s*\n",
        ],
    }


def _find_sections_by_pattern(
    full_text: str,
    pdf_content: PdfContent,
    section_type: str,
    patterns: list[str],
    config: ExtractorConfig,
) -> list[DetectedSection]:
    """Find sections matching the given patterns."""
    sections = []

    for pattern in patterns:
        matches = list(re.finditer(pattern, full_text, re.MULTILINE))

        for match in matches:
            start_pos = match.start()
            title = match.group().strip()

            # Find section end (next section header or end of document)
            end_pos = _find_section_end(full_text, start_pos)

            # Extract section text
            section_text = full_text[start_pos:end_pos].strip()

            if (
                len(section_text) < config.analysis.min_section_length
            ):  # Skip very short sections
                continue

            # Map character positions to pages
            start_page, end_page = _get_page_range(pdf_content, start_pos, end_pos)

            # Create detected section with confidence based on pattern specificity
            confidence = _calculate_confidence(pattern, title, section_text)

            section = DetectedSection.create_with_auto_id(
                section_type=section_type,
                title=title,
                text=section_text,
                start_page=start_page,
                end_page=end_page,
                confidence=confidence,
                char_start=start_pos,
                char_end=end_pos,
            )

            sections.append(section)

    return sections


def _find_section_end(full_text: str, start_pos: int) -> int:
    """Find the end position of a section by looking for the next header."""
    # Look for next section header patterns
    next_header_patterns = [
        r"(?i)\n\s*\d+\.?\s*[a-z][a-z\s]+\n",  # Numbered section
        r"(?i)\n\s*[a-z][a-z\s]*(?:conclusion|reference|acknowledgment)",  # End sections
    ]

    min_end_pos = len(full_text)

    for pattern in next_header_patterns:
        matches = re.finditer(
            pattern, full_text[start_pos + 100 :]
        )  # Skip current header
        for match in matches:
            actual_pos = start_pos + 100 + match.start()
            if actual_pos < min_end_pos:
                min_end_pos = actual_pos

    return min_end_pos


def _get_page_range(
    pdf_content: PdfContent, char_start: int, char_end: int
) -> tuple[int, int]:
    """Map character positions to page numbers."""
    start_page = 1
    end_page = 1

    char_pos = 0
    for page in pdf_content.pages:
        page_end = char_pos + len(page.text) + 1  # +1 for newline

        if char_start >= char_pos and char_start < page_end:
            start_page = page.page_number

        if char_end >= char_pos and char_end <= page_end:
            end_page = page.page_number

        char_pos = page_end

    return start_page, max(start_page, end_page)


def _calculate_confidence(pattern: str, title: str, section_text: str) -> float:
    """Calculate confidence score based on pattern specificity and content."""
    base_confidence = 0.8

    # Higher confidence for numbered sections
    if re.search(r"\d+\.", title):
        base_confidence += 0.1

    # Higher confidence for longer sections
    if len(section_text) > 500:
        base_confidence += 0.05

    # Lower confidence for very short titles
    if len(title.strip()) < 5:
        base_confidence -= 0.1

    return min(1.0, max(0.1, base_confidence))


def _resolve_overlapping_sections(
    sections: list[DetectedSection],
) -> list[DetectedSection]:
    """
    Resolve overlapping sections by keeping the most confident ones.

    This is a pure function that returns a new list without modifying the input.
    """
    if not sections:
        return []

    resolved: list[DetectedSection] = []

    for current in sections:
        # Check if current section overlaps with any resolved section
        overlaps = False

        for existing in resolved:
            if _sections_overlap(current, existing):
                # Keep the section with higher confidence
                if current.confidence > existing.confidence:
                    # Replace existing with current
                    resolved = [s for s in resolved if s != existing]
                    resolved.append(current)
                overlaps = True
                break

        if not overlaps:
            resolved.append(current)

    return sorted(resolved, key=lambda s: s.char_start)


def _sections_overlap(section1: DetectedSection, section2: DetectedSection) -> bool:
    """Check if two sections overlap in character positions."""
    return not (
        section1.char_end <= section2.char_start
        or section2.char_end <= section1.char_start
    )


def _log_section_size_warnings(sections: list[DetectedSection]) -> None:
    """Log warnings for sections that may cause processing issues."""
    large_section_threshold = 15000  # Characters
    very_large_threshold = 25000  # Characters

    for section in sections:
        section_size = len(section.text)

        if section_size > very_large_threshold:
            logger.warning(
                f"Very large {section.section_type} section detected "
                f"({section_size:,} chars). This may cause timeouts or "
                f"JSON parsing issues. Consider manual review."
            )
        elif section_size > large_section_threshold:
            logger.info(
                f"Large {section.section_type} section detected "
                f"({section_size:,} chars). Will be automatically chunked for "
                "processing."
            )

    total_size = sum(len(s.text) for s in sections)
    if total_size > 100000:  # 100k characters
        logger.warning(
            f"Very large document detected ({total_size:,} total chars). "
            f"Processing may take several minutes."
        )
