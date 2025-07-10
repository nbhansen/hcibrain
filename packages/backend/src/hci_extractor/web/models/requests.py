"""Pydantic request models for web API."""

from typing import Optional

from pydantic import BaseModel, Field


class PaperMetadata(BaseModel):
    """Optional metadata that can be provided with a PDF upload."""

    title: Optional[str] = Field(None, description="Paper title")
    authors: Optional[str] = Field(None, description="Comma-separated author names")
    venue: Optional[str] = Field(None, description="Publication venue")
    year: Optional[int] = Field(None, ge=1900, le=2030, description="Publication year")


class ExtractionRequest(BaseModel):
    """Request model for PDF extraction with optional metadata."""

    paper_metadata: Optional[PaperMetadata] = Field(
        None,
        description="Optional paper metadata",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "paper_metadata": {
                    "title": "Example HCI Paper",
                    "authors": "Smith, J., Doe, A.",
                    "venue": "CHI 2025",
                    "year": 2025,
                },
            },
        }
