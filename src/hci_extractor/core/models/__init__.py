"""Immutable data models for PDF content extraction."""

from .exceptions import (
    # Base exceptions
    HciExtractorError,
    ProcessingError,
    ConfigurationError,
    DataError,
    # PDF exceptions
    PdfError,
    PasswordProtectedError,
    CorruptedFileError,
    NoTextLayerError,
    ExtractionQualityError,
    # LLM exceptions
    LLMError,
    RateLimitError,
    LLMValidationError,
    ApiKeyError,
    ModelNotFoundError,
    ContentFilterError,
    # Data exceptions
    SerializationError,
    DataValidationError,
    DependencyError,
)
from .pdf_models import (
    CharacterPosition,
    DetectedSection,
    ExtractedElement,
    ExtractionResult,
    Paper,
    PdfContent,
    PdfPage,
    TextTransformation,
)

__all__ = [
    # Data models
    "CharacterPosition",
    "DetectedSection",
    "PdfPage",
    "PdfContent",
    "TextTransformation",
    "Paper",
    "ExtractedElement",
    "ExtractionResult",
    # Exceptions
    "HciExtractorError",
    "ProcessingError",
    "ConfigurationError",
    "DataError",
    "PdfError",
    "PasswordProtectedError",
    "CorruptedFileError",
    "NoTextLayerError",
    "ExtractionQualityError",
    "LLMError",
    "RateLimitError",
    "LLMValidationError",
    "ApiKeyError",
    "ModelNotFoundError",
    "ContentFilterError",
    "SerializationError",
    "DataValidationError",
    "DependencyError",
]
