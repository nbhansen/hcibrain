"""Pydantic response models for web API."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ElementCoordinates(BaseModel):
    """Coordinate information for highlighting extracted elements."""

    page_number: int = Field(..., ge=1, description="Page number (1-based)")
    x: float = Field(..., ge=0, description="X coordinate on page")
    y: float = Field(..., ge=0, description="Y coordinate on page")
    width: float = Field(..., gt=0, description="Width of the highlight box")
    height: float = Field(..., gt=0, description="Height of the highlight box")
    char_start: int = Field(..., ge=0, description="Starting character index")
    char_end: int = Field(..., ge=0, description="Ending character index")


class PaperInfo(BaseModel):
    """Paper information in extraction response."""

    paper_id: str = Field(..., description="Unique paper identifier")
    title: str = Field(..., description="Paper title (extracted or provided)")
    authors: List[str] = Field(..., description="List of authors")
    venue: Optional[str] = Field(None, description="Publication venue")
    year: Optional[int] = Field(None, description="Publication year")
    file_path: str = Field(..., description="Uploaded file path")


class ExtractionSummary(BaseModel):
    """Summary statistics for extraction results."""

    total_elements: int = Field(..., description="Total number of elements extracted")
    elements_by_type: Dict[str, int] = Field(
        ...,
        description="Count of elements by type",
    )
    elements_by_section: Dict[str, int] = Field(
        ...,
        description="Count of elements by section",
    )
    average_confidence: float = Field(..., description="Average confidence score")
    processing_time_seconds: float = Field(..., description="Total processing time")
    created_at: str = Field(..., description="Extraction timestamp")
    paper_summary: Optional[str] = Field(None, description="AI-generated paper summary")
    paper_summary_confidence: Optional[float] = Field(
        None,
        description="Summary confidence score",
    )


class ExtractedElement(BaseModel):
    """Individual extracted element from the paper."""

    element_id: str = Field(..., description="Unique element identifier")
    element_type: str = Field(
        ...,
        description="Type: goal, method, or result",
    )
    text: str = Field(..., description="Verbatim extracted text")
    section: str = Field(..., description="Paper section where element was found")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score",
    )
    evidence_type: str = Field(
        ...,
        description="Evidence type: quantitative, qualitative, etc.",
    )
    page_number: Optional[int] = Field(
        None,
        description="Page number where element appears",
    )
    coordinates: Optional[ElementCoordinates] = Field(
        None,
        description="Coordinate information for highlighting",
    )
    supporting_evidence: Optional[str] = Field(
        None,
        description="Supporting evidence mentioned",
    )
    methodology_context: Optional[str] = Field(
        None,
        description="Methodological context",
    )
    study_population: Optional[str] = Field(None, description="Study population info")
    limitations: Optional[str] = Field(None, description="Limitations mentioned")
    surrounding_context: Optional[str] = Field(
        None,
        description="Context before/after element",
    )


class ExtractionResponse(BaseModel):
    """Complete response from PDF extraction."""

    paper: PaperInfo = Field(..., description="Paper information")
    extraction_summary: ExtractionSummary = Field(
        ...,
        description="Extraction summary statistics",
    )
    extracted_elements: List[ExtractedElement] = Field(
        ...,
        description="All extracted elements",
    )
    paper_full_text: Optional[str] = Field(
        None,
        description="Full text content of the PDF for text-based rendering",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "paper": {
                    "paper_id": "uuid-string",
                    "title": "Example HCI Paper",
                    "authors": ["Smith, J.", "Doe, A."],
                    "venue": "CHI 2025",
                    "year": 2025,
                    "file_path": "uploaded_paper.pdf",
                },
                "extraction_summary": {
                    "total_elements": 91,
                    "elements_by_type": {"claim": 44, "finding": 35, "method": 12},
                    "elements_by_section": {"abstract": 3, "introduction": 8},
                    "average_confidence": 0.93,
                    "processing_time_seconds": 30.5,
                    "created_at": "2025-07-04T20:22:30.140596",
                },
                "extracted_elements": [
                    {
                        "element_id": "uuid-string",
                        "element_type": "claim",
                        "text": "Example verbatim extracted text",
                        "section": "abstract",
                        "confidence": 0.95,
                        "evidence_type": "quantitative",
                        "page_number": 1,
                    },
                ],
            },
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional error details")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "error": "PdfError",
                "message": "Unable to extract text from PDF",
                "detail": "The PDF file appears to be corrupted or password-protected",
            },
        }
