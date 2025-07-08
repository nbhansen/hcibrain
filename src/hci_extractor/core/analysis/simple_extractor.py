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
import time
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.events import (
    BatchProcessingCompleted,
    BatchProcessingStarted,
    EventBus,
    ExtractionCompleted,
    ExtractionFailed,
    ExtractionStarted,
    PaperProcessingCompleted,
    PaperProcessingStarted,
    ProgressUpdate,
    SectionDetected,
)
from hci_extractor.core.extraction import PdfExtractor
from hci_extractor.core.models import (
    ExtractionResult,
    LLMError,
    Paper,
    PdfError,
)
from hci_extractor.providers import LLMProvider

from .section_detector import detect_sections
from .section_processor import LLMSectionProcessor, process_sections_batch

logger = logging.getLogger(__name__)


async def extract_paper_simple(
    pdf_path: Path,
    llm_provider: LLMProvider,
    config: ExtractorConfig,
    event_bus: EventBus,
    paper_metadata: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Any] = None,
) -> ExtractionResult:
    """
    Extract academic elements from a PDF - simple version that just works!

    Args:
        pdf_path: Path to PDF file
        llm_provider: LLM provider for text extraction
        config: Configuration object (required)
        event_bus: Event bus for publishing events (required)
        paper_metadata: Optional metadata (title, authors, etc.)

    Returns:
        ExtractionResult with all extracted elements

    Raises:
        PdfError: If PDF cannot be processed
        LLMError: If LLM processing fails
    """
    logger.info(f"Starting simple extraction for {pdf_path}")

    # Use injected event bus
    start_time = time.time()

    # Create paper metadata early for event tracking
    paper = _create_paper_from_metadata(pdf_path, paper_metadata)

    # Get file size for events
    try:
        file_size = pdf_path.stat().st_size
    except (OSError, AttributeError):
        file_size = 0

    # Publish paper processing started event
    event_bus.publish(
        PaperProcessingStarted(
            paper_id=paper.paper_id,
            paper_title=paper.title,
            file_path=str(pdf_path),
            file_size_bytes=file_size,
        ),
    )

    # Publish extraction started event (for backward compatibility)
    event_bus.publish(
        ExtractionStarted(
            pdf_path=str(pdf_path), paper_id=paper.paper_id, file_size_bytes=file_size,
        ),
    )

    try:
        # Step 1: Extract PDF content
        if progress_callback:
            progress_callback.update_section("pdf_extraction")

        # Publish progress update
        event_bus.publish(
            ProgressUpdate(
                operation_type="paper",
                operation_id=paper.paper_id,
                current_step=1,
                total_steps=4,
                step_name="pdf_extraction",
                percentage_complete=25.0,
            ),
        )

        logger.info("📄 Extracting PDF content...")
        pdf_extractor = PdfExtractor(config)
        pdf_content = pdf_extractor.extract_content(pdf_path)
        logger.info(
            f"✅ Extracted {pdf_content.total_pages} pages, "
            f"{pdf_content.total_chars} characters",
        )

        if progress_callback:
            progress_callback.complete_section()

        # Step 2: Paper metadata already created above
        logger.info(f"📋 Created paper: {paper.title}")

        # Step 3: Detect sections
        if progress_callback:
            progress_callback.update_section("section_detection")

        # Publish progress update
        event_bus.publish(
            ProgressUpdate(
                operation_type="paper",
                operation_id=paper.paper_id,
                current_step=2,
                total_steps=4,
                step_name="section_detection",
                percentage_complete=50.0,
            ),
        )

        logger.info("🔍 Detecting paper sections...")
        sections = detect_sections(pdf_content, config)
        logger.info(
            f"✅ Detected {len(sections)} sections: "
            f"{[s.section_type for s in sections]}",
        )

        # Publish section detected event
        event_bus.publish(
            SectionDetected(
                paper_id=paper.paper_id,
                section_count=len(sections),
                section_types=tuple(s.section_type for s in sections),
            ),
        )

        if progress_callback:
            progress_callback.complete_section()

        if not sections:
            logger.warning("No sections detected - returning empty result")
            if progress_callback:
                progress_callback.complete_paper(0)
                progress_callback.finish()
            return ExtractionResult(
                paper=paper,
                elements=(),
                extraction_metadata=types.MappingProxyType({
                    "pdf_pages": pdf_content.total_pages,
                    "sections_found": 0,
                    "elements_extracted": 0,
                    "processing_status": "no_sections",
                }),
            )

        # Step 3.5: Generate paper summary from abstract and introduction
        paper_summary = await _generate_paper_summary(
            sections, llm_provider, paper.paper_id,
        )

        # Step 4: Process sections with LLM
        if progress_callback:
            progress_callback.update_section("llm_analysis")

        # Publish progress update
        event_bus.publish(
            ProgressUpdate(
                operation_type="paper",
                operation_id=paper.paper_id,
                current_step=3,
                total_steps=4,
                step_name="llm_analysis",
                percentage_complete=75.0,
            ),
        )

        logger.info("🤖 Processing sections with LLM...")
        processor = LLMSectionProcessor(llm_provider, config, event_bus)

        all_elements = await process_sections_batch(
            sections=sections,
            paper=paper,
            processor=processor,
            config=config,
            max_concurrent=3,  # Conservative for reliability
        )

        logger.info(f"✅ Extracted {len(all_elements)} total elements")

        if progress_callback:
            progress_callback.complete_section()

        # Step 5: Create final result
        extraction_metadata = {
            "pdf_pages": pdf_content.total_pages,
            "sections_found": len(sections),
            "elements_extracted": len(all_elements),
            "processing_status": "success",
            "sections_processed": [s.section_type for s in sections],
        }

        # Add paper summary to metadata if generated
        if paper_summary:
            extraction_metadata.update(paper_summary)

        result = ExtractionResult(
            paper=paper,
            elements=all_elements,
            extraction_metadata=types.MappingProxyType(extraction_metadata),
        )

        if progress_callback:
            progress_callback.complete_paper(len(all_elements))
            progress_callback.finish()

        # Calculate final duration
        total_duration = time.time() - start_time

        # Publish final progress update
        event_bus.publish(
            ProgressUpdate(
                operation_type="paper",
                operation_id=paper.paper_id,
                current_step=4,
                total_steps=4,
                step_name="completed",
                percentage_complete=100.0,
            ),
        )

        # Publish paper processing completed event
        event_bus.publish(
            PaperProcessingCompleted(
                paper_id=paper.paper_id,
                paper_title=paper.title,
                elements_extracted=len(all_elements),
                sections_processed=len(sections),
                duration_seconds=total_duration,
                success=True,
            ),
        )

        # Publish extraction completed event (for backward compatibility)
        event_bus.publish(
            ExtractionCompleted(
                paper_id=paper.paper_id,
                pages_extracted=pdf_content.total_pages,
                characters_extracted=pdf_content.total_chars,
                duration_seconds=total_duration,
            ),
        )

        logger.info(
            f"🎉 Extraction complete! Found {len(all_elements)} elements "
            f"from {len(sections)} sections",
        )
        return result

    except PdfError as e:
        logger.exception("PDF processing failed")

        # Publish paper processing completed with failure
        event_bus.publish(
            PaperProcessingCompleted(
                paper_id=paper.paper_id,
                paper_title=paper.title,
                elements_extracted=0,
                sections_processed=0,
                duration_seconds=time.time() - start_time,
                success=False,
                error_message=str(e),
            ),
        )

        # Publish extraction failed event (for backward compatibility)
        event_bus.publish(
            ExtractionFailed(
                pdf_path=str(pdf_path), error_type="PdfError", error_message=str(e),
            ),
        )
        raise
    except LLMError as e:
        logger.exception("LLM processing failed")

        # Publish paper processing completed with failure
        event_bus.publish(
            PaperProcessingCompleted(
                paper_id=paper.paper_id,
                paper_title=paper.title,
                elements_extracted=0,
                sections_processed=0,
                duration_seconds=time.time() - start_time,
                success=False,
                error_message=str(e),
            ),
        )

        # Publish extraction failed event (for backward compatibility)
        event_bus.publish(
            ExtractionFailed(
                pdf_path=str(pdf_path), error_type="LLMError", error_message=str(e),
            ),
        )
        raise
    except Exception as e:
        logger.exception("Unexpected error during extraction")

        # Publish paper processing completed with failure
        event_bus.publish(
            PaperProcessingCompleted(
                paper_id=paper.paper_id,
                paper_title=paper.title,
                elements_extracted=0,
                sections_processed=0,
                duration_seconds=time.time() - start_time,
                success=False,
                error_message=str(e),
            ),
        )

        # Publish extraction failed event (for backward compatibility)
        event_bus.publish(
            ExtractionFailed(
                pdf_path=str(pdf_path),
                error_type=type(e).__name__,
                error_message=str(e),
            ),
        )
        raise LLMError(f"Extraction failed: {e}")


def _create_paper_from_metadata(
    pdf_path: Path, metadata: Optional[Dict[str, Any]],
) -> Paper:
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
            file_path=str(pdf_path),
        )
    # Default paper from filename
    return Paper.create_with_auto_id(
        title=pdf_path.stem.replace("_", " ").replace("-", " ").title(),
        authors=("Unknown",),
        file_path=str(pdf_path),
    )


async def extract_multiple_papers(
    pdf_paths: List[Path],
    llm_provider: LLMProvider,
    config: ExtractorConfig,
    event_bus: EventBus,
    papers_metadata: Optional[List[Dict[str, Any]]] = None,
    progress_callback: Optional[Any] = None,
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

    # Use injected event bus and publish batch started event
    batch_start_time = time.time()

    event_bus.publish(
        BatchProcessingStarted(
            total_papers=len(pdf_paths),
            input_directory="multiple_paths",  # Could be enhanced to detect common directory
            output_directory="memory",  # In-memory results
            max_concurrent=1,  # Sequential processing for simplicity
            filter_pattern="*.pdf",
        ),
    )

    results = []
    successful_count = 0
    failed_count = 0

    for i, pdf_path in enumerate(pdf_paths):
        try:
            # Get metadata for this paper
            paper_metadata = None
            if papers_metadata and i < len(papers_metadata):
                paper_metadata = papers_metadata[i]

            # Publish batch progress update
            event_bus.publish(
                ProgressUpdate(
                    operation_type="batch",
                    operation_id="batch_extraction",
                    current_step=i + 1,
                    total_steps=len(pdf_paths),
                    step_name=f"processing_{pdf_path.stem}",
                    percentage_complete=((i + 1) / len(pdf_paths)) * 100.0,
                ),
            )

            # Extract this paper
            result = await extract_paper_simple(
                pdf_path=pdf_path,
                llm_provider=llm_provider,
                config=config,
                event_bus=event_bus,
                paper_metadata=paper_metadata,
                progress_callback=progress_callback,
            )

            results.append(result)
            successful_count += 1
            logger.info(
                f"✅ Completed paper {i+1}/{len(pdf_paths)}: {result.paper.title}",
            )

        except Exception as e:
            failed_count += 1
            logger.exception(
                f"❌ Failed to process paper {i+1}/{len(pdf_paths)} ({pdf_path})",
            )
            # Continue with other papers - don't let one failure stop the batch
            continue

    # Calculate batch statistics
    total_duration = time.time() - batch_start_time
    average_elements = (
        sum(len(result.elements) for result in results) / len(results)
        if results
        else 0.0
    )

    # Publish batch processing completed event
    event_bus.publish(
        BatchProcessingCompleted(
            total_papers=len(pdf_paths),
            successful_papers=successful_count,
            failed_papers=failed_count,
            duration_seconds=total_duration,
            average_elements_per_paper=average_elements,
        ),
    )

    logger.info(f"🎉 Batch complete: {len(results)}/{len(pdf_paths)} papers processed")
    return results


async def _generate_paper_summary(
    sections: tuple[Any, ...], llm_provider: LLMProvider, paper_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Generate paper summary from abstract and introduction sections.

    Args:
        sections: List of detected sections
        llm_provider: LLM provider for summary generation
        paper_id: Paper ID for logging

    Returns:
        Dictionary with paper summary data or None if generation fails
    """
    try:
        # Find abstract and introduction sections
        abstract_text = ""
        introduction_text = ""

        for section in sections:
            if section.section_type.lower() == "abstract":
                abstract_text = section.text
            elif section.section_type.lower() in ["introduction", "intro"]:
                introduction_text = section.text

        # Skip if we don't have abstract or introduction
        if not abstract_text.strip() and not introduction_text.strip():
            logger.debug(
                f"No abstract or introduction found for paper {paper_id} - "
                "skipping summary",
            )
            return None

        logger.info("📝 Generating paper summary...")

        # Generate summary using LLM provider
        summary_data = await llm_provider.generate_paper_summary(
            abstract_text=abstract_text,
            introduction_text=introduction_text,
            context={"paper_id": paper_id},
        )

        # Validate the summary
        if summary_data and summary_data.get("summary", "").strip():
            confidence = summary_data.get("confidence", 0.0)
            logger.info(f"✅ Generated paper summary (confidence: {confidence:.2f})")
            return {
                "paper_summary": summary_data.get("summary", ""),
                "paper_summary_confidence": summary_data.get("confidence", 0.0),
                "paper_summary_sources": summary_data.get("source_sections", []),
            }
        logger.warning(f"Empty summary generated for paper {paper_id}")
        return None

    except Exception as e:
        logger.warning(f"Failed to generate paper summary for {paper_id}: {e}")
        # Don't fail the entire extraction if summary generation fails
        return None


def extract_paper_sync(
    pdf_path: Path,
    llm_provider: LLMProvider,
    config: ExtractorConfig,
    event_bus: EventBus,
    paper_metadata: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Any] = None,
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
    return asyncio.run(
        extract_paper_simple(
            pdf_path, llm_provider, config, event_bus, paper_metadata, progress_callback,
        ),
    )
