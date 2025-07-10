"""PDF extraction endpoints."""

import logging
import re
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.extraction.pdf_extractor import PdfExtractor
from hci_extractor.core.ports.llm_provider_port import LLMProviderPort
from hci_extractor.web.dependencies import (
    get_extractor_config,
    get_llm_provider,
    get_pdf_extractor,
)
from hci_extractor.web.models.markup_responses import MarkupExtractionResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_summary_from_response(text: str) -> str:
    """Extract plain language summary from LLM response.

    Args:
        text: The full LLM response containing summary tags

    Returns:
        The extracted summary text, or empty string if not found
    """
    summary_match = re.search(r"<summary>(.*?)</summary>", text, re.DOTALL)
    if summary_match:
        return summary_match.group(1).strip()
    return ""


@router.post("/extract/markup", response_model=MarkupExtractionResponse)
async def extract_pdf_markup(
    file: UploadFile = File(...),
    config: ExtractorConfig = Depends(get_extractor_config),
    llm_provider: LLMProviderPort = Depends(get_llm_provider),
    pdf_extractor: PdfExtractor = Depends(get_pdf_extractor),
) -> MarkupExtractionResponse:
    """
    Extract PDF and return full text with HTML markup for highlights.

    This endpoint bypasses JSON parsing entirely and asks the LLM to return
    the complete text with HTML tags for goals, methods, and results.

    Args:
        file: PDF file upload
        config: Extractor configuration
        llm_provider: LLM provider for markup generation

    Returns:
        Full text with HTML markup for highlighting
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
        start_time = time.time()

        # Extract PDF content
        pdf_content = pdf_extractor.extract_content(temp_file_path)

        # DEBUG: Log PDF extraction results
        logger.info(
            f"🔍 EXTRACT DEBUG - PDF extracted: {len(pdf_content.full_text)} chars",
        )
        logger.info(
            f"🔍 EXTRACT DEBUG - First 500 chars: {pdf_content.full_text[:500]!r}",
        )

        # Generate markup using LLM (no JSON parsing!)
        marked_up_text = await llm_provider.generate_markup(pdf_content.full_text)

        # Extract summary from the LLM response
        summary = _extract_summary_from_response(marked_up_text)

        # Remove summary tags from the main text to avoid duplication
        cleaned_text = re.sub(
            r"<summary>.*?</summary>",
            "",
            marked_up_text,
            flags=re.DOTALL,
        )

        processing_time = time.time() - start_time

        return MarkupExtractionResponse(
            paper_full_text_with_markup=cleaned_text,
            paper_info={
                "title": "Extracted Paper",
                "authors": [],
                "paper_id": str(uuid.uuid4())[:8],
            },
            plain_language_summary=summary,
            processing_time_seconds=processing_time,
        )

    finally:
        # Clean up temporary file
        try:
            temp_file_path.unlink()
        except OSError:
            pass
