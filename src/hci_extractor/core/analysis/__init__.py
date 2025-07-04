"""Core analysis pipeline for section detection, processing, and validation."""

from .section_detector import detect_sections
from .section_processor import (
    LLMSectionProcessor,
    SectionProcessor,
    process_sections_batch,
)
from .simple_extractor import (
    extract_multiple_papers,
    extract_paper_simple,
    extract_paper_sync,
)
from .simple_validator import quick_validation_stats, validate_extracted_elements

__all__ = [
    # Section Detection
    "detect_sections",
    # Section Processing
    "SectionProcessor",
    "LLMSectionProcessor",
    "process_sections_batch",
    # Simple Extraction
    "extract_paper_simple",
    "extract_paper_sync",
    "extract_multiple_papers",
    # Simple Validation
    "validate_extracted_elements",
    "quick_validation_stats",
]
