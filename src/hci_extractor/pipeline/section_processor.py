"""
Section processing interfaces and implementations following SOLID principles.

This module implements the Interface Segregation Principle (ISP) by defining
minimal, focused interfaces for section processing. It uses dependency 
injection (DIP) to decouple from concrete LLM implementations.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional

from ..models import DetectedSection, ExtractedElement, Paper, LLMError
from ..llm import LLMProvider

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
        timeout_seconds: float = 30.0
    ):
        """
        Initialize with injected LLM provider.
        
        Args:
            llm_provider: Abstract LLM provider (DIP)
            max_retries: Maximum retry attempts for failed processing
            timeout_seconds: Timeout for processing operations
        """
        self.llm_provider = llm_provider
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
    
    async def process_section(
        self,
        section: DetectedSection,
        paper: Paper,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ExtractedElement, ...]:
        """
        Process section using LLM to extract academic elements.
        
        This is a pure function that returns new immutable objects
        without modifying inputs.
        """
        logger.info(
            f"Processing {section.section_type} section "
            f"({len(section.text)} chars) from paper {paper.paper_id}"
        )
        
        try:
            # Build context for LLM analysis
            analysis_context = self._build_analysis_context(paper, section, context)
            
            # Process with timeout and retries
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
                    wait_time = 2 ** attempt
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
                valid_types = ["claim", "finding", "method"]
                if element_type not in valid_types:
                    # Map "artifact" from new prompts to "method" for now
                    if element_type == "artifact":
                        element_type = "method"
                    else:
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