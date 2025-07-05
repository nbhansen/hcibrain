"""PDF extraction endpoints."""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from hci_extractor.core.analysis import extract_paper_simple
from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.events import EventBus
from hci_extractor.core.models import ExtractionResult
from hci_extractor.providers import LLMProvider
from hci_extractor.web.dependencies import (
    get_event_bus,
    get_extractor_config,
    get_llm_provider,
)
from hci_extractor.web.models.requests import PaperMetadata
from hci_extractor.web.models.responses import (
    ExtractionResponse,
    ExtractionSummary,
    ExtractedElement,
    PaperInfo,
)


router = APIRouter()


@router.post("/extract/simple", response_model=ExtractionResponse)
async def extract_pdf_simple(
    file: UploadFile = File(...),
    config: ExtractorConfig = Depends(get_extractor_config),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    event_bus: EventBus = Depends(get_event_bus),
) -> ExtractionResponse:
    """
    Simple PDF extraction endpoint - just upload a file.
    
    Args:
        file: PDF file to extract
        
    Returns:
        Extraction results with all detected elements
    """
    # Validate file
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Check file size
    if hasattr(file, "size") and file.size:
        max_size = config.extraction.max_file_size_mb * 1024 * 1024
        if file.size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {config.extraction.max_file_size_mb}MB",
            )
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = Path(temp_file.name)
    
    try:
        # Extract using existing business logic
        start_time = time.time()
        result = await extract_paper_simple(
            pdf_path=temp_file_path,
            llm_provider=llm_provider,
            config=config,
            event_bus=event_bus,
            paper_metadata={},  # Empty metadata
            progress_callback=None,
        )
        processing_time = time.time() - start_time
        
        # Convert to API response format
        response = _convert_extraction_result_to_response(
            result, processing_time, file.filename
        )
        
        return response
        
    finally:
        # Clean up temporary file
        try:
            temp_file_path.unlink()
        except OSError:
            pass  # File might have been already deleted


def _convert_extraction_result_to_response(
    result: ExtractionResult, processing_time: float, file_path: str
) -> ExtractionResponse:
    """
    Convert ExtractionResult domain object to API response model.

    Args:
        result: Domain extraction result
        processing_time: Processing time in seconds
        file_path: Uploaded file path

    Returns:
        ExtractionResponse for API
    """
    # Convert paper info
    paper_info = PaperInfo(
        paper_id=result.paper.paper_id,
        title=result.paper.title,
        authors=list(result.paper.authors),
        venue=result.paper.venue,
        year=result.paper.year,
        file_path=file_path,
    )

    # Initialize counters
    elements_by_type: Dict[str, int] = {}
    elements_by_section: Dict[str, int] = {}
    average_confidence = 0.0

    # Calculate summary statistics
    if result.elements:
        # Group by type
        for element in result.elements:
            element_type = element.element_type
            elements_by_type[element_type] = elements_by_type.get(element_type, 0) + 1

            # Group by section
            section = element.section
            elements_by_section[section] = elements_by_section.get(section, 0) + 1

        # Calculate average confidence
        total_confidence = sum(element.confidence for element in result.elements)
        average_confidence = total_confidence / len(result.elements)

    # Create extraction summary
    extraction_summary = ExtractionSummary(
        total_elements=len(result.elements),
        elements_by_type=elements_by_type,
        elements_by_section=elements_by_section,
        average_confidence=average_confidence,
        processing_time_seconds=processing_time,
        created_at=result.created_at.isoformat(),
        paper_summary=None,  # Could be added in future
        paper_summary_confidence=None,
    )

    # Convert extracted elements
    extracted_elements = []
    for element in result.elements:
        api_element = ExtractedElement(
            element_id=element.element_id,
            element_type=element.element_type,
            text=element.text,
            section=element.section,
            confidence=element.confidence,
            evidence_type=element.evidence_type,
            page_number=element.page_number,
            supporting_evidence=getattr(element, "supporting_evidence", None),
            methodology_context=getattr(element, "methodology_context", None),
            study_population=getattr(element, "study_population", None),
            limitations=getattr(element, "limitations", None),
            surrounding_context=getattr(element, "surrounding_context", None),
        )
        extracted_elements.append(api_element)

    return ExtractionResponse(
        paper=paper_info,
        extraction_summary=extraction_summary,
        extracted_elements=extracted_elements,
    )


@router.post("/extract", response_model=ExtractionResponse)
async def extract_pdf(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    authors: Optional[str] = Form(None),
    venue: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    config: ExtractorConfig = Depends(get_extractor_config),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    event_bus: EventBus = Depends(get_event_bus),
) -> ExtractionResponse:
    """
    Extract structured content from a PDF file.

    Args:
        file: PDF file upload
        title: Optional paper title
        authors: Optional comma-separated list of authors
        venue: Optional publication venue
        year: Optional publication year
        config: Extractor configuration
        llm_provider: LLM provider for extraction
        event_bus: Event bus for progress tracking

    Returns:
        Extraction results with paper info, summary, and extracted elements

    Raises:
        HTTPException: If file is invalid or processing fails
    """
    # Validate file
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Check file size
    if hasattr(file, "size") and file.size:
        max_size = config.extraction.max_file_size_mb * 1024 * 1024
        if file.size > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {config.extraction.max_file_size_mb}MB",
            )

    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = Path(temp_file.name)

    try:
        # Prepare paper metadata
        metadata: Dict[str, Any] = {}
        if title:
            metadata["title"] = title
        if authors:
            # Convert comma-separated string to list
            metadata["authors"] = [a.strip() for a in authors.split(",")]
        if venue:
            metadata["venue"] = venue
        if year:
            metadata["year"] = year

        # Extract using existing business logic
        start_time = time.time()
        result = await extract_paper_simple(
            pdf_path=temp_file_path,
            llm_provider=llm_provider,
            config=config,
            event_bus=event_bus,
            paper_metadata=metadata,
            progress_callback=None,
        )
        processing_time = time.time() - start_time

        # Convert to API response format
        response = _convert_extraction_result_to_response(
            result, processing_time, file.filename
        )

        return response

    finally:
        # Clean up temporary file
        try:
            temp_file_path.unlink()
        except OSError:
            pass  # File might have been already deleted
