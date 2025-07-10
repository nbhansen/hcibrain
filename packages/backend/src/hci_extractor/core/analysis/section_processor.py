"""
Section processing interfaces and implementations following SOLID principles.

This module implements the Interface Segregation Principle (ISP) by defining
minimal, focused interfaces for section processing. It uses dependency
injection (DIP) to decouple from concrete LLM implementations.
"""

import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.events import (
    EventBus,
    ExtractionQualityAssessed,
    SectionProcessingCompleted,
    SectionProcessingStarted,
)
from hci_extractor.core.models import DetectedSection, ExtractedElement, LLMError, Paper
from hci_extractor.core.ports import LLMProviderPort

# Simple error handling - let the LLM handle the understanding
from hci_extractor.utils.json_recovery import JsonRecoveryOptions, recover_json
from hci_extractor.utils.retry_handler import RetryHandler, RetryPolicy, RetryStrategy

logger = logging.getLogger(__name__)


class SectionProcessor(ABC):
    """
    Abstract interface for section processing.

    Follows Interface Segregation Principle - minimal, focused interface
    that only defines what's needed for section processing.
    """

    @abstractmethod
    async def process_section(
        self,
        section: DetectedSection,
        paper: Paper,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ExtractedElement, ...]:
        """
        Process a section to extract academic elements.

        Args:
            section: Immutable detected section to process
            paper: Immutable paper metadata for context
            context: Optional additional context

        Returns:
            Immutable tuple of extracted elements

        Raises:
            LLMError: If processing fails
        """


class LLMSectionProcessor(SectionProcessor):
    """
    LLM-based section processor implementation.

    Follows Dependency Inversion Principle - depends on LLMProvider abstraction,
    not concrete implementations. This allows any LLM provider to be used.
    """

    def __init__(
        self,
        llm_provider: LLMProviderPort,
        config: ExtractorConfig,
        event_bus: EventBus,
        chunk_size: int = 8000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize with injected dependencies.

        Args:
            llm_provider: Abstract LLM provider (DIP)
            config: Configuration object (required)
            event_bus: Event bus for publishing events
            chunk_size: Maximum size of text chunks for processing
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.config = config
        self.llm_provider = llm_provider
        self.event_bus = event_bus
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.timeout_seconds = config.analysis.section_timeout_seconds

        # Initialize retry handler for section processing
        self._retry_policy = RetryPolicy(
            max_attempts=self.config.retry.max_attempts,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=2.0,
            backoff_multiplier=2.0,
            max_delay_seconds=60.0,
            timeout_seconds=self.config.analysis.section_timeout_seconds,
            retryable_exceptions=(LLMError, asyncio.TimeoutError),
            non_retryable_exceptions=(ValueError, TypeError),
        )
        self._retry_handler = RetryHandler(
            policy=self._retry_policy,
            operation_name="section_processing",
            publish_events=True,
            event_bus=self.event_bus,
        )

    async def process_section(
        self,
        section: DetectedSection,
        paper: Paper,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ExtractedElement, ...]:
        """
        Process section using LLM to extract academic elements.

        This is a pure function that returns new immutable objects
        without modifying inputs. Large sections are automatically chunked.
        """
        logger.info(
            f"Processing {section.section_type} section "
            f"({len(section.text)} chars) from paper {paper.paper_id}",
        )

        # Get event bus
        event_bus = self.event_bus
        start_time = time.time()

        # Calculate chunk count for event
        chunk_count = 1
        if len(section.text) > self.chunk_size:
            chunk_count = len(self._split_text_into_chunks(section.text))

        # Publish section processing started event
        event_bus.publish(
            SectionProcessingStarted(
                paper_id=paper.paper_id,
                section_type=section.section_type,
                section_size_chars=len(section.text),
                chunk_count=chunk_count,
            ),
        )

        try:
            # Build context for LLM analysis
            analysis_context = self._build_analysis_context(paper, section, context)

            # Check if section needs chunking
            if len(section.text) > self.chunk_size:
                logger.info(
                    f"Large section ({len(section.text)} chars) detected, "
                    f"splitting into chunks of {self.chunk_size} chars",
                )
                extracted_elements = await self._process_section_chunked(
                    section,
                    analysis_context,
                    paper,
                )

                # Assess and publish extraction quality
                self._assess_and_publish_quality(extracted_elements, paper, section)

                # Publish section processing completed event
                event_bus.publish(
                    SectionProcessingCompleted(
                        paper_id=paper.paper_id,
                        section_type=section.section_type,
                        elements_extracted=len(extracted_elements),
                        duration_seconds=time.time() - start_time,
                    ),
                )

                return extracted_elements
            # Process normally for smaller sections
            elements_data = await self._process_with_retries(
                section,
                analysis_context,
            )

            # Convert LLM output to immutable ExtractedElement objects
            extracted_elements = self._create_extracted_elements(
                elements_data,
                section,
                paper,
            )

            logger.info(
                f"Successfully extracted {len(extracted_elements)} elements "
                f"from {section.section_type} section",
            )

            # Assess and publish extraction quality
            self._assess_and_publish_quality(extracted_elements, paper, section)

            # Publish section processing completed event
            event_bus.publish(
                SectionProcessingCompleted(
                    paper_id=paper.paper_id,
                    section_type=section.section_type,
                    elements_extracted=len(extracted_elements),
                    duration_seconds=time.time() - start_time,
                ),
            )

            return extracted_elements

        except Exception as e:
            # Simple error handling - let the LLM figure out the understanding
            logger.exception(
                f"Failed to process {section.section_type} section: {e!s}",
            )

            # Try basic partial extraction as fallback
            partial_elements = await self._attempt_partial_extraction(section, paper, e)

            # Publish completion event even for failures
            event_bus.publish(
                SectionProcessingCompleted(
                    paper_id=paper.paper_id,
                    section_type=section.section_type,
                    elements_extracted=len(partial_elements),
                    duration_seconds=time.time() - start_time,
                ),
            )

            # Publish quality assessment for failed/partial extraction
            event_bus.publish(
                ExtractionQualityAssessed(
                    paper_id=paper.paper_id,
                    section_type=section.section_type,
                    elements_extracted=len(partial_elements),
                    average_confidence=(
                        0.0
                        if not partial_elements
                        else sum(elem.confidence for elem in partial_elements)
                        / len(partial_elements)
                    ),
                    quality_score=0.1 if partial_elements else 0.0,
                    quality_issues=("extraction_failed",)
                    + (("partial_recovery_attempted",) if partial_elements else ()),
                ),
            )

            # Return partial elements or empty tuple - graceful degradation
            return partial_elements

    async def _process_section_chunked(
        self,
        section: DetectedSection,
        analysis_context: Dict[str, Any],
        paper: Paper,
    ) -> Tuple[ExtractedElement, ...]:
        """Process large section by splitting into chunks."""
        chunks = self._split_text_into_chunks(section.text)
        all_elements: List[ExtractedElement] = []

        logger.info(
            f"Processing {len(chunks)} chunks for {section.section_type} section",
        )

        for i, chunk_text in enumerate(chunks):
            try:
                # Create temporary section for this chunk
                chunk_section = DetectedSection(
                    section_id=f"{section.section_id}_chunk_{i}",
                    section_type=section.section_type,
                    title=f"{section.title} (chunk {i + 1}/{len(chunks)})",
                    text=chunk_text,
                    start_page=section.start_page,
                    end_page=section.end_page,
                    confidence=section.confidence,
                    char_start=section.char_start,
                    char_end=section.char_end,
                )

                # Process chunk with retries
                elements_data = await self._process_with_retries(
                    chunk_section,
                    analysis_context,
                )

                # Convert to ExtractedElement objects
                chunk_elements = self._create_extracted_elements(
                    elements_data,
                    section,
                    paper,  # Use original section for metadata
                )

                all_elements.extend(chunk_elements)

                logger.info(
                    f"Processed chunk {i + 1}/{len(chunks)}, "
                    f"extracted {len(chunk_elements)} elements",
                )

            except Exception as e:
                # Simple error handling for chunk processing
                logger.warning(
                    f"Failed to process chunk {i + 1}/{len(chunks)} "
                    f"of {section.section_type}: {e}",
                )

                # Try basic text extraction as fallback
                try:
                    basic_elements = self._extract_basic_elements_from_text(
                        chunk_text,
                        section,
                        paper,
                    )
                    if basic_elements:
                        all_elements.extend(basic_elements)
                        logger.info(
                            f"Recovered {len(basic_elements)} basic elements "
                            "from failed chunk",
                        )
                except Exception as fallback_error:
                    logger.debug(
                        f"Fallback extraction also failed: {fallback_error}",
                    )

                continue

        logger.info(
            f"Chunked processing complete: {len(all_elements)} total elements "
            f"from {len(chunks)} chunks",
        )

        # Note: For chunked processing, the completion event is published
        # in the main process_section method, not here

        return tuple(all_elements)

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks for processing."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size

            # If this is not the last chunk, try to break at word boundary
            if end < len(text):
                # Look for sentence or paragraph boundary within overlap range
                break_point = self._find_good_break_point(
                    text,
                    max(start, end - self.chunk_overlap),
                    end,
                )
                if break_point > start:
                    end = break_point

            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)

            # Move start position with overlap
            start = max(start + 1, end - self.chunk_overlap)

            # Prevent infinite loop
            if start >= len(text):
                break

        return chunks

    def _find_good_break_point(self, text: str, min_pos: int, max_pos: int) -> int:
        """Find a good place to break text (sentence or paragraph end)."""
        # Look for paragraph breaks first
        for i in range(max_pos - 1, min_pos - 1, -1):
            if i < len(text) - 1 and text[i : i + 2] == "\n\n":
                return i + 2

        # Look for sentence endings
        sentence_endings = ".!?"
        for i in range(max_pos - 1, min_pos - 1, -1):
            if i < len(text) and text[i] in sentence_endings:
                # Check if it's followed by whitespace or end of text
                if i + 1 >= len(text) or text[i + 1].isspace():
                    return i + 1

        # Look for any whitespace
        for i in range(max_pos - 1, min_pos - 1, -1):
            if i < len(text) and text[i].isspace():
                return i + 1

        # If no good break point found, use max_pos
        return max_pos

    def _build_analysis_context(
        self,
        paper: Paper,
        section: DetectedSection,
        additional_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build context dictionary for LLM analysis."""
        context = {
            "paper_title": paper.title,
            "paper_venue": paper.venue,
            "paper_year": paper.year,
            "section_type": section.section_type,
            "section_title": section.title,
        }

        # Add authors if available
        if paper.authors:
            context["authors"] = (
                paper.authors
                if isinstance(paper.authors, str)
                else ", ".join(paper.authors)
            )

        # Merge additional context
        if additional_context:
            context.update(additional_context)

        return context

    async def _process_with_retries(
        self,
        section: DetectedSection,
        context: Dict[str, Any],
    ) -> list[Dict[str, Any]]:
        """Process section using unified retry handler with timeout and JSON \
recovery."""

        async def section_analysis_operation() -> List[Dict[str, Any]]:
            """Wrapper for section analysis with timeout and JSON recovery."""
            raw_result = await asyncio.wait_for(
                self.llm_provider.analyze_section(
                    section_text=section.text,
                    section_type=section.section_type,
                    context=context,
                ),
                timeout=self.timeout_seconds,
            )

            # If the result is already parsed, return it
            if isinstance(raw_result, list):
                return raw_result

            # If it's a dict with elements, extract the elements
            if isinstance(raw_result, dict) and "elements" in raw_result:
                return raw_result["elements"]

            # If it's a string (shouldn't happen with current providers, but for safety)
            if isinstance(raw_result, str):
                logger.warning(
                    "Received string response from LLM provider, attempting JSON "
                    "recovery",
                )
                recovery_options = JsonRecoveryOptions(
                    strategies=["all"],
                    expected_structure={"elements": list},
                    validate_structure=True,
                )

                recovery_result = recover_json(raw_result, recovery_options)
                if recovery_result.success:
                    logger.info(
                        f"Successfully recovered JSON using strategy: "
                        f"{recovery_result.strategy_used}",
                    )
                    if (
                        isinstance(recovery_result.recovered_data, dict)
                        and "elements" in recovery_result.recovered_data
                    ):
                        return recovery_result.recovered_data["elements"]
                    return []
                logger.error(
                    f"Failed to recover JSON from LLM response: "
                    f"{recovery_result.error_message}",
                )
                raise LLMError(
                    f"Failed to parse LLM response as JSON: "
                    f"{recovery_result.error_message}",
                )

            # Fallback - return empty list if we can't parse
            logger.warning(
                f"Unexpected response format from LLM provider: {type(raw_result)}",
            )
            return []

        # Use unified retry handler
        result = await self._retry_handler.execute_with_retry(
            section_analysis_operation,
        )

        if result.success:
            return result.value  # type: ignore[no-any-return]
        # Convert retry handler error to LLMError for backward compatibility
        error_msg = f"Failed to process {section.section_type} section after "
        f"{result.attempts_made} attempts"
        if result.error:
            logger.error(f"{error_msg}: {result.error}")
            raise LLMError(error_msg) from result.error
        logger.error(error_msg)
        raise LLMError(error_msg)

    def _create_extracted_elements(
        self,
        elements_data: list[Dict[str, Any]],
        section: DetectedSection,
        paper: Paper,
    ) -> Tuple[ExtractedElement, ...]:
        """
        Convert LLM output to immutable ExtractedElement objects.

        This is a pure function that creates new immutable objects.
        """
        extracted_elements = []

        for element_data in elements_data:
            try:
                # Map LLM output to our data model
                element_type = element_data.get("element_type", "unknown")

                # Ensure element_type is valid for our model
                valid_types = ["goal", "method", "result"]
                if element_type not in valid_types:
                    logger.warning(
                        f"Invalid element_type '{element_type}', "
                        "defaulting to 'result'",
                    )
                    element_type = "result"

                # Create immutable extracted element
                element = ExtractedElement.create_with_auto_id(
                    paper_id=paper.paper_id,
                    element_type=element_type,
                    text=element_data.get("text", "").strip(),
                    section=section.section_type,
                    confidence=float(element_data.get("confidence", 0.0)),
                    evidence_type=element_data.get("evidence_type", "unknown"),
                    page_number=section.start_page,  # Use section's start page
                    # Optional context fields (only included if present)
                    supporting_evidence=element_data.get("supporting_evidence"),
                    methodology_context=element_data.get("methodology_context"),
                    study_population=element_data.get("study_population"),
                    limitations=element_data.get("limitations"),
                    surrounding_context=element_data.get("surrounding_context"),
                )

                extracted_elements.append(element)

            except (ValueError, KeyError, TypeError) as e:
                logger.warning(
                    f"Skipping invalid element data in {section.section_type}: {e}",
                )
                continue

        return tuple(extracted_elements)

    def _assess_and_publish_quality(
        self,
        extracted_elements: Tuple[ExtractedElement, ...],
        paper: Paper,
        section: DetectedSection,
    ) -> None:
        """Assess extraction quality and publish quality metrics event."""
        if not extracted_elements:
            # Publish quality assessment for empty extractions
            event_bus = self.event_bus
            event_bus.publish(
                ExtractionQualityAssessed(
                    paper_id=paper.paper_id,
                    section_type=section.section_type,
                    elements_extracted=0,
                    average_confidence=0.0,
                    quality_score=0.0,
                    quality_issues=("no_elements_extracted",),
                ),
            )
            return

        # Calculate quality metrics
        confidences = [elem.confidence for elem in extracted_elements]
        average_confidence = sum(confidences) / len(confidences)

        # Identify quality issues
        quality_issues = []

        # Check for low confidence elements
        low_confidence_count = sum(1 for conf in confidences if conf < 0.5)
        if low_confidence_count > 0:
            quality_issues.append(f"low_confidence_elements_{low_confidence_count}")

        # Check for very short extractions
        short_extractions = sum(1 for elem in extracted_elements if len(elem.text) < 20)
        if short_extractions > 0:
            quality_issues.append(f"short_extractions_{short_extractions}")

        # Check for element type diversity
        element_types = {elem.element_type for elem in extracted_elements}
        if len(element_types) == 1 and len(extracted_elements) > 3:
            quality_issues.append("low_element_type_diversity")

        # Check extraction density (elements per 1000 characters)
        extraction_density = len(extracted_elements) / (len(section.text) / 1000)
        if extraction_density < 0.5:
            quality_issues.append("low_extraction_density")
        elif extraction_density > 10:
            quality_issues.append("high_extraction_density")

        # Calculate overall quality score (0-1)
        quality_score = average_confidence

        # Penalty for quality issues
        if quality_issues:
            penalty = min(0.3, len(quality_issues) * 0.1)
            quality_score = max(0.0, quality_score - penalty)

        # Bonus for good extraction density
        if 1.0 <= extraction_density <= 5.0:
            quality_score = min(1.0, quality_score + 0.1)

        # Publish quality assessment event
        event_bus = self.event_bus
        event_bus.publish(
            ExtractionQualityAssessed(
                paper_id=paper.paper_id,
                section_type=section.section_type,
                elements_extracted=len(extracted_elements),
                average_confidence=average_confidence,
                quality_score=quality_score,
                quality_issues=tuple(quality_issues),
            ),
        )

    async def _attempt_partial_extraction(
        self,
        section: DetectedSection,
        paper: Paper,
        original_error: Exception,
    ) -> Tuple[ExtractedElement, ...]:
        """
        Attempt partial extraction when full processing fails.

        This implements graceful degradation by trying simpler extraction
        methods when the main LLM processing fails.
        """
        logger.info(f"Attempting partial extraction for {section.section_type} section")

        try:
            # Try basic text-based extraction
            basic_elements = self._extract_basic_elements_from_text(
                section.text,
                section,
                paper,
            )

            if basic_elements:
                logger.info(
                    f"Partial extraction recovered {len(basic_elements)} basic elements"
                )
                return basic_elements

            # If basic extraction fails, try to extract at least some key phrases
            key_phrase_elements = self._extract_key_phrases_as_elements(
                section.text,
                section,
                paper,
            )

            if key_phrase_elements:
                logger.info(
                    f"Key phrase extraction recovered "
                    f"{len(key_phrase_elements)} elements",
                )
                return key_phrase_elements

        except Exception as e:
            logger.debug(f"Partial extraction also failed: {e}")

        return ()

    def _extract_basic_elements_from_text(
        self,
        text: str,
        section: DetectedSection,
        paper: Paper,
    ) -> Tuple[ExtractedElement, ...]:
        """
        Extract basic elements using simple text analysis patterns.

        This is a fallback method that doesn't rely on LLM processing.
        """
        elements = []

        # Look for common academic patterns
        patterns = {
            "finding": [
                r"we found that\s+([^.]{20,200})",
                r"results show that\s+([^.]{20,200})",
                r"our findings indicate\s+([^.]{20,200})",
                r"the analysis revealed\s+([^.]{20,200})",
            ],
            "claim": [
                r"we argue that\s+([^.]{20,200})",
                r"we propose that\s+([^.]{20,200})",
                r"our hypothesis is\s+([^.]{20,200})",
                r"we suggest that\s+([^.]{20,200})",
            ],
            "method": [
                r"we used\s+([^.]{20,200})",
                r"methodology\s*:?\s+([^.]{20,200})",
                r"our approach\s+([^.]{20,200})",
                r"the procedure\s+([^.]{20,200})",
            ],
        }

        for element_type, type_patterns in patterns.items():
            for pattern in type_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches[:3]:  # Limit to 3 per pattern
                    clean_text = match.strip()
                    if len(clean_text) >= 20:  # Minimum length filter
                        element = ExtractedElement.create_with_auto_id(
                            paper_id=paper.paper_id,
                            element_type=element_type,  # type: ignore[arg-type]
                            text=clean_text,
                            section=section.section_type,
                            confidence=0.3,  # Low confidence for pattern matching
                            evidence_type="unknown",
                            page_number=section.start_page,
                            # No optional context fields for pattern matching
                        )
                        elements.append(element)

        return tuple(elements)

    def _extract_key_phrases_as_elements(
        self,
        text: str,
        section: DetectedSection,
        paper: Paper,
    ) -> Tuple[ExtractedElement, ...]:
        """
        Extract key phrases as a last resort when other methods fail.

        This provides minimal extraction to maintain some value from failed sections.
        """
        elements = []

        # Split into sentences and look for substantive content
        sentences = re.split(r"[.!?]+", text)

        for sentence in sentences:
            sentence = sentence.strip()

            # Filter for substantive sentences (academic indicators)
            if len(sentence) >= 50 and any(
                keyword in sentence.lower()
                for keyword in [
                    "significant",
                    "analysis",
                    "study",
                    "research",
                    "findings",
                    "results",
                    "conclusion",
                    "evidence",
                    "data",
                    "participants",
                ]
            ):
                element = ExtractedElement.create_with_auto_id(
                    paper_id=paper.paper_id,
                    element_type="finding",  # Default to finding for key phrases
                    text=sentence,
                    section=section.section_type,
                    confidence=0.2,  # Very low confidence for key phrases
                    evidence_type="unknown",
                    page_number=section.start_page,
                    # No optional context fields for key phrase fallback
                )
                elements.append(element)

                # Limit to avoid noise
                if len(elements) >= 2:
                    break

        return tuple(elements)


async def process_sections_batch(
    sections: Tuple[DetectedSection, ...],
    paper: Paper,
    processor: SectionProcessor,
    config: ExtractorConfig,
    context: Optional[Dict[str, Any]] = None,
    max_concurrent: Optional[int] = None,
) -> Tuple[ExtractedElement, ...]:
    """
    Process multiple sections concurrently for efficiency.

    Pure function that returns new immutable objects without side effects.
    Follows the Open/Closed Principle - can work with any SectionProcessor.

    Args:
        sections: Immutable tuple of sections to process
        paper: Immutable paper metadata
        processor: Abstract processor (OCP/LSP compliance)
        config: Configuration object (required)
        context: Optional context for all sections
        max_concurrent: Maximum concurrent processing operations override

    Returns:
        Immutable tuple of all extracted elements
    """
    max_concurrent = (
        max_concurrent
        if max_concurrent is not None
        else config.analysis.max_concurrent_sections
    )
    if not sections:
        return ()

    logger.info(
        f"Processing {len(sections)} sections concurrently "
        f"(max_concurrent={max_concurrent})",
    )

    # Create semaphore to limit concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_single_section(
        section: DetectedSection,
    ) -> Tuple[ExtractedElement, ...]:
        """Process a single section with concurrency control."""
        async with semaphore:
            return await processor.process_section(section, paper, context)

    # Process all sections concurrently
    tasks = [process_single_section(section) for section in sections]
    section_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten results and filter out errors
    all_elements: List[ExtractedElement] = []
    successful_sections = 0

    for i, result in enumerate(section_results):
        if isinstance(result, Exception):
            # Simple error handling for batch processing
            logger.error(
                f"Failed to process section {sections[i].section_type}: {result}",
            )

            # For batch processing, continue even on individual failures
            # This implements graceful degradation at the batch level
            logger.info(
                f"Continuing batch processing despite "
                f"{sections[i].section_type} failure",
            )
        else:
            if isinstance(result, tuple):
                all_elements.extend(result)
            else:
                logger.warning(f"Unexpected result type: {type(result)}")
            successful_sections += 1

    logger.info(
        f"Successfully processed {successful_sections}/{len(sections)} sections, "
        f"extracted {len(all_elements)} total elements",
    )

    return tuple(all_elements)
