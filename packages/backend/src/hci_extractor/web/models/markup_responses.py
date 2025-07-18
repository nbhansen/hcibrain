"""Pydantic response models for markup-based extraction."""

from typing import Dict, List, Union

from pydantic import BaseModel, Field


class MarkupExtractionResponse(BaseModel):
    """Response for markup-based extraction."""

    paper_full_text_with_markup: str = Field(
        ...,
        description="Complete paper text with HTML markup for highlights",
    )
    paper_info: Dict[str, Union[str, List[str]]] = Field(
        ...,
        description="Basic paper information",
    )
    plain_language_summary: str = Field(
        ...,
        description="Plain language summary for non-researchers",
    )
    processing_time_seconds: float = Field(..., description="Total processing time")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "paper_full_text_with_markup": (
                    "This paper presents <goal confidence='0.95'>a novel approach to speech "
                    "recognition</goal> using <method confidence='0.87'>deep neural networks "
                    "with attention mechanisms</method> which achieves <result confidence='0.92'>"
                    "15% improvement in accuracy</result>."
                ),
                "paper_info": {
                    "title": "Deep Speech Recognition",
                    "authors": ["Smith, J.", "Doe, A."],
                    "paper_id": "12345",
                },
                "plain_language_summary": (
                    "Researchers developed a new way to help computers understand human speech "
                    "better. They used advanced artificial intelligence techniques called deep "
                    "neural networks with special attention features. Their approach made speech "
                    "recognition 15% more accurate than previous methods."
                ),
                "processing_time_seconds": 45.2,
            },
        }
