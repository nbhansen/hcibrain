"""Immutable data models for PDF content extraction."""

import types
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Literal, Optional, Union


@dataclass(frozen=True)
class CharacterPosition:
    """Character-level positioning for verbatim validation."""

    char_index: int
    page_number: int
    x: float
    y: float
    bbox: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        """Validate character position data."""
        if self.char_index < 0:
            raise ValueError("Character index must be >= 0")
        if self.page_number < 1:
            raise ValueError("Page number must be >= 1")
        if len(self.bbox) != 4:
            raise ValueError("Bbox must have exactly 4 coordinates")


@dataclass(frozen=True)
class PdfPage:
    """Immutable representation of a single PDF page."""

    page_number: int
    text: str
    char_count: int
    dimensions: tuple[float, float]  # width, height
    char_positions: tuple[CharacterPosition, ...] = ()

    def __post_init__(self) -> None:
        """Validate page data integrity."""
        if self.page_number < 1:
            raise ValueError("Page number must be >= 1")
        if len(self.text) != self.char_count:
            raise ValueError("Text length must match char_count")
        if len(self.dimensions) != 2:
            raise ValueError("Dimensions must be (width, height)")
        if self.dimensions[0] <= 0 or self.dimensions[1] <= 0:
            raise ValueError("Dimensions must be positive")


@dataclass(frozen=True)
class PdfContent:
    """Immutable representation of complete PDF document."""

    file_path: str
    total_pages: int
    pages: tuple[PdfPage, ...]
    extraction_metadata: types.MappingProxyType[str, Any] = field(
        default_factory=lambda: types.MappingProxyType({})
    )
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate PDF content integrity."""
        if self.total_pages != len(self.pages):
            raise ValueError("Total pages must match pages tuple length")
        if self.total_pages < 1:
            raise ValueError("PDF must have at least 1 page")
        if not self.file_path:
            raise ValueError("File path cannot be empty")

    @property
    def full_text(self) -> str:
        """Return complete text content across all pages."""
        return "\n".join(page.text for page in self.pages)

    @property
    def total_chars(self) -> int:
        """Return total character count across all pages."""
        return sum(page.char_count for page in self.pages)

    def get_text_at_position(self, char_index: int) -> tuple[str, int]:
        """Return character and page number at global character index."""
        if char_index < 0 or char_index >= self.total_chars:
            raise IndexError("Character index out of range")

        current_index = 0
        for page in self.pages:
            if current_index + page.char_count > char_index:
                local_index = char_index - current_index
                return page.text[local_index], page.page_number
            current_index += page.char_count

        raise IndexError("Character index out of range")


@dataclass(frozen=True)
class TextTransformation:
    """Track text cleaning transformations for reversibility."""

    original_text: str
    cleaned_text: str
    transformations: tuple[str, ...] = ()
    char_mapping: types.MappingProxyType[int, int] = field(
        default_factory=lambda: types.MappingProxyType({})
    )

    def reverse_lookup(self, cleaned_position: int) -> int:
        """Map cleaned text position back to original."""
        return self.char_mapping.get(cleaned_position, -1)

    def __post_init__(self) -> None:
        """Validate transformation data."""
        if not self.original_text and not self.cleaned_text:
            raise ValueError("At least one text field must be non-empty")


@dataclass(frozen=True)
class DetectedSection:
    """Immutable representation of a detected paper section."""

    section_id: str
    section_type: str
    title: str
    text: str
    start_page: int
    end_page: int
    confidence: float
    char_start: int
    char_end: int

    def __post_init__(self) -> None:
        """Validate detected section data."""
        if not self.section_id:
            raise ValueError("Section ID cannot be empty")
        if not self.section_type:
            raise ValueError("Section type cannot be empty")
        if not self.text.strip():
            raise ValueError("Section text cannot be empty")
        if self.start_page < 1:
            raise ValueError("Start page must be >= 1")
        if self.end_page < self.start_page:
            raise ValueError("End page must be >= start page")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.char_start < 0:
            raise ValueError("Character start must be >= 0")
        if self.char_end <= self.char_start:
            raise ValueError("Character end must be > character start")

    @classmethod
    def create_with_auto_id(
        cls,
        section_type: str,
        title: str,
        text: str,
        start_page: int,
        end_page: int,
        confidence: float,
        char_start: int,
        char_end: int,
    ) -> "DetectedSection":
        """Create a DetectedSection with automatically generated UUID."""
        return cls(
            section_id=str(uuid.uuid4()),
            section_type=section_type,
            title=title,
            text=text,
            start_page=start_page,
            end_page=end_page,
            confidence=confidence,
            char_start=char_start,
            char_end=char_end,
        )


@dataclass(frozen=True)
class Paper:
    """Immutable representation of an academic paper."""

    paper_id: str
    title: str
    authors: tuple[str, ...]
    venue: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    file_path: str = ""

    def __post_init__(self) -> None:
        """Validate paper data."""
        if not self.paper_id:
            raise ValueError("Paper ID cannot be empty")
        if not self.title:
            raise ValueError("Title cannot be empty")
        if not self.authors:
            raise ValueError("Authors cannot be empty")
        if self.year is not None and (self.year < 1900 or self.year > 2030):
            raise ValueError("Year must be between 1900 and 2030")

    @classmethod
    def create_with_auto_id(
        cls,
        title: str,
        authors: Union[tuple[str, ...], list[str]],
        venue: Optional[str] = None,
        year: Optional[int] = None,
        doi: Optional[str] = None,
        file_path: str = "",
    ) -> "Paper":
        """Create a Paper with automatically generated UUID."""
        # Convert list to tuple for immutability
        if isinstance(authors, list):
            authors = tuple(authors)

        return cls(
            paper_id=str(uuid.uuid4()),
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            doi=doi,
            file_path=file_path,
        )


@dataclass(frozen=True)
class ExtractedElement:
    """Immutable representation of an extracted academic element."""

    element_id: str
    paper_id: str
    element_type: Literal["claim", "finding", "method", "artifact"]
    text: str
    section: str
    confidence: float
    evidence_type: Literal["quantitative", "qualitative", "theoretical", "unknown"]
    page_number: Optional[int] = None
    # Optional context fields for enhanced manual comparison
    supporting_evidence: Optional[str] = None
    methodology_context: Optional[str] = None
    study_population: Optional[str] = None
    limitations: Optional[str] = None
    surrounding_context: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate extracted element data."""
        if not self.element_id:
            raise ValueError("Element ID cannot be empty")
        if not self.paper_id:
            raise ValueError("Paper ID cannot be empty")
        if not self.text.strip():
            raise ValueError("Text cannot be empty")
        if not self.section:
            raise ValueError("Section cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.page_number is not None and self.page_number < 1:
            raise ValueError("Page number must be >= 1")

    @classmethod
    def create_with_auto_id(
        cls,
        paper_id: str,
        element_type: Literal["claim", "finding", "method", "artifact"],
        text: str,
        section: str,
        confidence: float,
        evidence_type: Literal["quantitative", "qualitative", "theoretical", "unknown"],
        page_number: Optional[int] = None,
        supporting_evidence: Optional[str] = None,
        methodology_context: Optional[str] = None,
        study_population: Optional[str] = None,
        limitations: Optional[str] = None,
        surrounding_context: Optional[str] = None,
    ) -> "ExtractedElement":
        """Create an ExtractedElement with automatically generated UUID."""
        return cls(
            element_id=str(uuid.uuid4()),
            paper_id=paper_id,
            element_type=element_type,
            text=text,
            section=section,
            confidence=confidence,
            evidence_type=evidence_type,
            page_number=page_number,
            supporting_evidence=supporting_evidence,
            methodology_context=methodology_context,
            study_population=study_population,
            limitations=limitations,
            surrounding_context=surrounding_context,
        )


@dataclass(frozen=True)
class ExtractionResult:
    """Immutable representation of complete extraction results for a paper."""

    paper: Paper
    elements: tuple[ExtractedElement, ...]
    extraction_metadata: types.MappingProxyType[str, Any] = field(
        default_factory=lambda: types.MappingProxyType({})
    )
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate extraction result data."""
        if not isinstance(self.paper, Paper):
            raise ValueError("Paper must be a Paper instance")
        # Verify all elements belong to this paper
        for element in self.elements:
            if element.paper_id != self.paper.paper_id:
                raise ValueError(
                    f"Element {element.element_id} belongs to different paper"
                )

    @property
    def total_elements(self) -> int:
        """Return total number of extracted elements."""
        return len(self.elements)

    @property
    def elements_by_type(self) -> dict[str, int]:
        """Return count of elements by type."""
        counts = {"claim": 0, "finding": 0, "method": 0, "artifact": 0}
        for element in self.elements:
            counts[element.element_type] += 1
        return counts

    @property
    def elements_by_section(self) -> dict[str, int]:
        """Return count of elements by section."""
        counts: Dict[str, int] = {}
        for element in self.elements:
            counts[element.section] = counts.get(element.section, 0) + 1
        return counts

    @property
    def average_confidence(self) -> float:
        """Return average confidence score across all elements."""
        if not self.elements:
            return 0.0
        return sum(element.confidence for element in self.elements) / len(self.elements)

    def filter_by_confidence(self, min_confidence: float) -> "ExtractionResult":
        """Return new ExtractionResult with elements above confidence threshold."""
        filtered_elements = tuple(
            element for element in self.elements if element.confidence >= min_confidence
        )
        return ExtractionResult(
            paper=self.paper,
            elements=filtered_elements,
            extraction_metadata=self.extraction_metadata,
            created_at=self.created_at,
        )

    def filter_by_type(
        self,
        element_types: tuple[Literal["claim", "finding", "method", "artifact"], ...],
    ) -> "ExtractionResult":
        """Return new ExtractionResult with only specified element types."""
        filtered_elements = tuple(
            element
            for element in self.elements
            if element.element_type in element_types
        )
        return ExtractionResult(
            paper=self.paper,
            elements=filtered_elements,
            extraction_metadata=self.extraction_metadata,
            created_at=self.created_at,
        )
