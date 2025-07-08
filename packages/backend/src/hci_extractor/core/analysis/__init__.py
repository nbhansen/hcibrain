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
    "LLMSectionProcessor",
    # Section Processing
    "SectionProcessor",
    # Section Detection
    "detect_sections",
    "extract_multiple_papers",
    # Simple Extraction
    "extract_paper_simple",
    "extract_paper_sync",
    "process_sections_batch",
    "quick_validation_stats",
    # Simple Validation
    "validate_extracted_elements",
]
