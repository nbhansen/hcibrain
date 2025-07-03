"""
Simple extraction pipeline - the minimal version that just works!

This is the simplest possible implementation:
1. Extract PDF content
2. Detect sections  
3. Process sections with LLM
4. Return text snippets

No complex validation, no statistical analysis, just text discovery.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..extractors import PdfExtractor
from ..models import Paper, ExtractedElement, ExtractionResult, PdfError, LLMError
from ..llm import LLMProvider
from .section_detector import detect_sections
from .section_processor import LLMSectionProcessor, process_sections_batch

logger = logging.getLogger(__name__)


async def extract_paper_simple(
    pdf_path: Path,
    llm_provider: LLMProvider,
    paper_metadata: Optional[Dict[str, Any]] = None
) -> ExtractionResult:
    """
    Extract academic elements from a PDF - simple version that just works!
    
    Args:
        pdf_path: Path to PDF file
        llm_provider: LLM provider for text extraction
        paper_metadata: Optional metadata (title, authors, etc.)
        
    Returns:
        ExtractionResult with all extracted elements
        
    Raises:
        PdfError: If PDF cannot be processed
        LLMError: If LLM processing fails
    """
    logger.info(f"Starting simple extraction for {pdf_path}")
    
    try:
        # Step 1: Extract PDF content
        logger.info("📄 Extracting PDF content...")
        pdf_extractor = PdfExtractor()
        pdf_content = pdf_extractor.extract_content(pdf_path)
        logger.info(f"✅ Extracted {pdf_content.total_pages} pages, {pdf_content.total_chars} characters")
        
        # Step 2: Create paper metadata
        paper = _create_paper_from_metadata(pdf_path, paper_metadata)
        logger.info(f"📋 Created paper: {paper.title}")
        
        # Step 3: Detect sections
        logger.info("🔍 Detecting paper sections...")
        sections = detect_sections(pdf_content)
        logger.info(f"✅ Detected {len(sections)} sections: {[s.section_type for s in sections]}")
        
        if not sections:
            logger.warning("No sections detected - returning empty result")
            return ExtractionResult(
                paper=paper,
                elements=(),
                extraction_metadata={
                    "pdf_pages": pdf_content.total_pages,
                    "sections_found": 0,
                    "elements_extracted": 0,
                    "processing_status": "no_sections"
                }
            )
        
        # Step 4: Process sections with LLM
        logger.info("🤖 Processing sections with LLM...")
        processor = LLMSectionProcessor(llm_provider=llm_provider)
        
        all_elements = await process_sections_batch(
            sections=sections,
            paper=paper,
            processor=processor,
            max_concurrent=3  # Conservative for reliability
        )
        
        logger.info(f"✅ Extracted {len(all_elements)} total elements")
        
        # Step 5: Create final result
        result = ExtractionResult(
            paper=paper,
            elements=all_elements,
            extraction_metadata={
                "pdf_pages": pdf_content.total_pages,
                "sections_found": len(sections),
                "elements_extracted": len(all_elements),
                "processing_status": "success",
                "sections_processed": [s.section_type for s in sections]
            }
        )
        
        logger.info(f"🎉 Extraction complete! Found {len(all_elements)} elements from {len(sections)} sections")
        return result
        
    except PdfError as e:
        logger.error(f"PDF processing failed: {e}")
        raise
    except LLMError as e:
        logger.error(f"LLM processing failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}")
        raise LLMError(f"Extraction failed: {e}")


def _create_paper_from_metadata(pdf_path: Path, metadata: Optional[Dict[str, Any]]) -> Paper:
    """Create Paper object from metadata or defaults."""
    if metadata:
        title = metadata.get("title", pdf_path.stem)
        authors = metadata.get("authors", ())
        if isinstance(authors, (list, tuple)):
            authors = tuple(str(a) for a in authors)
        else:
            authors = (str(authors),) if authors else ()
        
        return Paper.create_with_auto_id(
            title=title,
            authors=authors,
            venue=metadata.get("venue"),
            year=metadata.get("year"),
            doi=metadata.get("doi"),
            file_path=str(pdf_path)
        )
    else:
        # Default paper from filename
        return Paper.create_with_auto_id(
            title=pdf_path.stem.replace("_", " ").replace("-", " ").title(),
            authors=("Unknown",),
            file_path=str(pdf_path)
        )


async def extract_multiple_papers(
    pdf_paths: List[Path],
    llm_provider: LLMProvider,
    papers_metadata: Optional[List[Dict[str, Any]]] = None
) -> List[ExtractionResult]:
    """
    Extract from multiple papers - simple batch processing.
    
    Args:
        pdf_paths: List of PDF file paths
        llm_provider: LLM provider for processing
        papers_metadata: Optional list of metadata dicts
        
    Returns:
        List of ExtractionResults, one per paper
    """
    logger.info(f"Starting batch extraction for {len(pdf_paths)} papers")
    
    results = []
    
    for i, pdf_path in enumerate(pdf_paths):
        try:
            # Get metadata for this paper
            paper_metadata = None
            if papers_metadata and i < len(papers_metadata):
                paper_metadata = papers_metadata[i]
            
            # Extract this paper
            result = await extract_paper_simple(
                pdf_path=pdf_path,
                llm_provider=llm_provider,
                paper_metadata=paper_metadata
            )
            
            results.append(result)
            logger.info(f"✅ Completed paper {i+1}/{len(pdf_paths)}: {result.paper.title}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process paper {i+1}/{len(pdf_paths)} ({pdf_path}): {e}")
            # Continue with other papers - don't let one failure stop the batch
            continue
    
    logger.info(f"🎉 Batch extraction complete: {len(results)}/{len(pdf_paths)} papers processed")
    return results


def extract_paper_sync(
    pdf_path: Path,
    llm_provider: LLMProvider,
    paper_metadata: Optional[Dict[str, Any]] = None
) -> ExtractionResult:
    """
    Synchronous wrapper for simple extraction (for non-async environments).
    
    Args:
        pdf_path: Path to PDF file
        llm_provider: LLM provider for processing
        paper_metadata: Optional paper metadata
        
    Returns:
        ExtractionResult with extracted elements
    """
    return asyncio.run(extract_paper_simple(pdf_path, llm_provider, paper_metadata))