"""Extraction pipeline components following SOLID principles."""

from .section_detector import detect_sections
from .section_processor import SectionProcessor, LLMSectionProcessor, process_sections_batch
from .simple_validator import validate_extracted_elements, quick_validation_stats

__all__ = [
    # Core components
    "detect_sections",
    "SectionProcessor",
    "LLMSectionProcessor", 
    "process_sections_batch",
    # Optional validation
    "validate_extracted_elements",
    "quick_validation_stats",
]

# Try to import simple extractor (requires PDF dependencies)
try:
    from .simple_extractor import extract_paper_simple, extract_multiple_papers, extract_paper_sync
    __all__.extend([
        "extract_paper_simple",
        "extract_multiple_papers", 
        "extract_paper_sync",
    ])
except ImportError:
    # Simple extractor requires PyMuPDF - gracefully handle missing dependency
    pass