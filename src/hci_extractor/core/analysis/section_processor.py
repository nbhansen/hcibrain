"""
Section processing interfaces and implementations following SOLID principles.

This module implements the Interface Segregation Principle (ISP) by defining
minimal, focused interfaces for section processing. It uses dependency 
injection (DIP) to decouple from concrete LLM implementations.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, List

from hci_extractor.core.models import DetectedSection, ExtractedElement, Paper, LLMError
from hci_extractor.providers.llm import LLMProvider

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
        context: Optional[Dict[str, Any]] = None
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
        pass


class LLMSectionProcessor(SectionProcessor):
    """
    LLM-based section processor implementation.
    
    Follows Dependency Inversion Principle - depends on LLMProvider abstraction,
    not concrete implementations. This allows any LLM provider to be used.
    """
    
    def __init__(
        self, 
        llm_provider: LLMProvider,
        max_retries: int = 2,
        timeout_seconds: float = 60.0,
        chunk_size: int = 10000,
        chunk_overlap: int = 500
    ):
        """
        Initialize with injected LLM provider.
        
        Args:
            llm_provider: Abstract LLM provider (DIP)
            max_retries: Maximum retry attempts for failed processing
            timeout_seconds: Timeout for processing operations
            chunk_size: Maximum characters per chunk for large sections
            chunk_overlap: Character overlap between chunks for context
        """
        self.llm_provider = llm_provider
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    async def process_section(
        self,
        section: DetectedSection,
        paper: Paper,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ExtractedElement, ...]:
        """
        Process section using LLM to extract academic elements.
        
        This is a pure function that returns new immutable objects
        without modifying inputs. Large sections are automatically chunked.
        """
        logger.info(
            f"Processing {section.section_type} section "
            f"({len(section.text)} chars) from paper {paper.paper_id}"
        )
        
        try:
            # Build context for LLM analysis
            analysis_context = self._build_analysis_context(paper, section, context)
            
            # Check if section needs chunking
            if len(section.text) > self.chunk_size:
                logger.info(
                    f"Large section ({len(section.text)} chars) detected, "
                    f"splitting into chunks of {self.chunk_size} chars"
                )
                return await self._process_section_chunked(section, analysis_context, paper)
            else:
                # Process normally for smaller sections
                elements_data = await self._process_with_retries(
                    section, analysis_context
                )
                
                # Convert LLM output to immutable ExtractedElement objects
                extracted_elements = self._create_extracted_elements(
                    elements_data, section, paper
                )
                
                logger.info(
                    f"Successfully extracted {len(extracted_elements)} elements "
                    f"from {section.section_type} section"
                )
                
                return extracted_elements
            
        except Exception as e:
            logger.error(
                f"Failed to process {section.section_type} section: {e}"
            )
            # Return empty tuple instead of raising - graceful degradation
            return ()
    
    async def _process_section_chunked(
        self,
        section: DetectedSection,
        analysis_context: Dict[str, Any],
        paper: Paper
    ) -> Tuple[ExtractedElement, ...]:
        """Process large section by splitting into chunks."""
        chunks = self._split_text_into_chunks(section.text)
        all_elements = []
        
        logger.info(f"Processing {len(chunks)} chunks for {section.section_type} section")
        
        for i, chunk_text in enumerate(chunks):
            try:
                # Create temporary section for this chunk
                chunk_section = DetectedSection(
                    section_id=f"{section.section_id}_chunk_{i}",
                    section_type=section.section_type,
                    title=f"{section.title} (chunk {i+1}/{len(chunks)})",
                    text=chunk_text,
                    start_page=section.start_page,
                    end_page=section.end_page,
                    confidence=section.confidence,
                    char_start=section.char_start,
                    char_end=section.char_end
                )
                
                # Process chunk with retries
                elements_data = await self._process_with_retries(
                    chunk_section, analysis_context
                )
                
                # Convert to ExtractedElement objects
                chunk_elements = self._create_extracted_elements(
                    elements_data, section, paper  # Use original section for metadata
                )
                
                all_elements.extend(chunk_elements)
                
                logger.info(
                    f"Processed chunk {i+1}/{len(chunks)}, "
                    f"extracted {len(chunk_elements)} elements"
                )
                
            except Exception as e:
                logger.warning(
                    f"Failed to process chunk {i+1}/{len(chunks)} "
                    f"of {section.section_type}: {e}"
                )
                continue
        
        logger.info(
            f"Chunked processing complete: {len(all_elements)} total elements "
            f"from {len(chunks)} chunks"
        )
        
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
                    text, max(start, end - self.chunk_overlap), end
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
            if i < len(text) - 1 and text[i:i+2] == '\n\n':
                return i + 2
        
        # Look for sentence endings
        sentence_endings = '.!?'
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
        additional_context: Optional[Dict[str, Any]]
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
            context["authors"] = paper.authors
        
        # Merge additional context
        if additional_context:
            context.update(additional_context)
        
        return context
    
    async def _process_with_retries(
        self,
        section: DetectedSection,
        context: Dict[str, Any]
    ) -> list[Dict[str, Any]]:
        """Process section with timeout and retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Apply timeout to prevent hanging
                elements_data = await asyncio.wait_for(
                    self.llm_provider.analyze_section(
                        section_text=section.text,
                        section_type=section.section_type,
                        context=context
                    ),
                    timeout=self.timeout_seconds
                )
                
                return elements_data
                
            except asyncio.TimeoutError as e:
                last_error = LLMError(f"Processing timeout after {self.timeout_seconds}s")
                logger.warning(
                    f"Timeout processing {section.section_type} section "
                    f"(attempt {attempt + 1}/{self.max_retries + 1})"
                )
                
            except LLMError as e:
                last_error = e
                logger.warning(
                    f"LLM error processing {section.section_type} section "
                    f"(attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )
                
                # Wait before retry with exponential backoff
                if attempt < self.max_retries:
                    wait_time = (2 ** attempt) * 2  # More aggressive backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
            
            except Exception as e:
                last_error = LLMError(f"Unexpected error: {e}")
                logger.error(
                    f"Unexpected error processing {section.section_type} section: {e}"
                )
                break  # Don't retry for unexpected errors
        
        # All retries exhausted
        logger.error(
            f"Failed to process {section.section_type} section after "
            f"{self.max_retries + 1} attempts"
        )
        raise last_error
    
    def _create_extracted_elements(
        self,
        elements_data: list[Dict[str, Any]],
        section: DetectedSection,
        paper: Paper
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
                valid_types = ["claim", "finding", "method", "artifact"]
                if element_type not in valid_types:
                    logger.warning(
                        f"Invalid element_type '{element_type}', defaulting to 'finding'"
                    )
                    element_type = "finding"
                
                # Create immutable extracted element
                element = ExtractedElement.create_with_auto_id(
                    paper_id=paper.paper_id,
                    element_type=element_type,
                    text=element_data.get("text", "").strip(),
                    section=section.section_type,
                    confidence=float(element_data.get("confidence", 0.0)),
                    evidence_type=element_data.get("evidence_type", "unknown"),
                    page_number=section.start_page  # Use section's start page
                )
                
                extracted_elements.append(element)
                
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(
                    f"Skipping invalid element data in {section.section_type}: {e}"
                )
                continue
        
        return tuple(extracted_elements)


async def process_sections_batch(
    sections: Tuple[DetectedSection, ...],
    paper: Paper,
    processor: SectionProcessor,
    context: Optional[Dict[str, Any]] = None,
    max_concurrent: int = 3
) -> Tuple[ExtractedElement, ...]:
    """
    Process multiple sections concurrently for efficiency.
    
    Pure function that returns new immutable objects without side effects.
    Follows the Open/Closed Principle - can work with any SectionProcessor.
    
    Args:
        sections: Immutable tuple of sections to process
        paper: Immutable paper metadata
        processor: Abstract processor (OCP/LSP compliance)
        context: Optional context for all sections
        max_concurrent: Maximum concurrent processing operations
        
    Returns:
        Immutable tuple of all extracted elements
    """
    if not sections:
        return ()
    
    logger.info(
        f"Processing {len(sections)} sections concurrently "
        f"(max_concurrent={max_concurrent})"
    )
    
    # Create semaphore to limit concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_single_section(section: DetectedSection) -> Tuple[ExtractedElement, ...]:
        """Process a single section with concurrency control."""
        async with semaphore:
            return await processor.process_section(section, paper, context)
    
    # Process all sections concurrently
    tasks = [process_single_section(section) for section in sections]
    section_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Flatten results and filter out errors
    all_elements = []
    successful_sections = 0
    
    for i, result in enumerate(section_results):
        if isinstance(result, Exception):
            logger.error(
                f"Failed to process section {sections[i].section_type}: {result}"
            )
        else:
            all_elements.extend(result)
            successful_sections += 1
    
    logger.info(
        f"Successfully processed {successful_sections}/{len(sections)} sections, "
        f"extracted {len(all_elements)} total elements"
    )
    
    return tuple(all_elements)