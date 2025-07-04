"""Unified exception hierarchy for HCI Paper Extractor.

This module provides a consistent exception hierarchy for all components
of the HCI extractor system, replacing fragmented exception patterns.
"""

from typing import Optional


class HciExtractorError(Exception):
    """Base exception for all HCI extractor operations.

    All exceptions in the HCI extractor system inherit from this base class
    to provide consistent error handling patterns.
    """

    pass


class ProcessingError(HciExtractorError):
    """Issues during document or data processing.

    Base class for all processing-related errors including PDF extraction,
    text normalization, and LLM analysis.
    """

    pass


# PDF Processing Exceptions
class PdfError(ProcessingError):
    """PDF-specific processing issues.

    Base class for all PDF-related errors during extraction and analysis.
    """

    pass


class PasswordProtectedError(PdfError):
    """PDF requires password for access.

    Raised when attempting to process a password-protected PDF without
    providing the correct password.
    """

    pass


class CorruptedFileError(PdfError):
    """PDF file is corrupted or unreadable.

    Raised when the PDF file cannot be opened or read due to corruption
    or invalid file format.
    """

    pass


class NoTextLayerError(PdfError):
    """PDF contains only images, no extractable text.

    Raised when the PDF appears to be scanned images without a text layer
    that can be extracted programmatically.
    """

    pass


class ExtractionQualityError(PdfError):
    """Extracted text quality below acceptable threshold.

    Raised when PDF extraction succeeds but the resulting text is too short,
    garbled, or otherwise of insufficient quality for analysis.
    """

    pass


# LLM Processing Exceptions
class LLMError(ProcessingError):
    """LLM-specific processing issues.

    Base class for all errors related to LLM providers, API calls,
    and response processing.
    """

    pass


class RateLimitError(LLMError):
    """LLM rate limit exceeded.

    Raised when the LLM provider's rate limits are exceeded and requests
    need to be retried after a delay.
    """

    def __init__(self, message: str, retry_after: Optional[float] = None):
        """Initialize with optional retry delay information.

        Args:
            message: Error description
            retry_after: Suggested delay in seconds before retry
        """
        super().__init__(message)
        self.retry_after = retry_after


class LLMValidationError(LLMError):
    """LLM response validation failed.

    Raised when the LLM response format is invalid, cannot be parsed,
    or doesn't match expected structure.
    """

    pass


class ApiKeyError(LLMError):
    """LLM API key authentication failed.

    Raised when the provided API key is invalid, expired, or missing
    required permissions.
    """

    pass


class ModelNotFoundError(LLMError):
    """Requested LLM model is not available.

    Raised when the specified model name is not found or not accessible
    with the current API key.
    """

    pass


class ContentFilterError(LLMError):
    """Content blocked by LLM safety filters.

    Raised when the LLM provider's safety filters prevent processing
    of the submitted content.
    """

    pass


# Data Processing Exceptions
class DataError(ProcessingError):
    """Data validation and integrity issues.

    Base class for errors related to data model validation,
    serialization, and integrity checks.
    """

    pass


class SerializationError(DataError):
    """Data serialization/deserialization failed.

    Raised when converting data to/from JSON, CSV, or other formats fails.
    """

    pass


class DataValidationError(DataError):
    """Data validation failed.

    Raised when data doesn't meet required format, type, or business rules.
    """

    pass


# Configuration and Environment Exceptions
class ConfigurationError(HciExtractorError):
    """Configuration or environment setup issues.

    Raised when required configuration is missing, invalid, or
    environment setup is incomplete.
    """

    pass


class DependencyError(ConfigurationError):
    """Required dependency is missing or incompatible.

    Raised when optional dependencies are required for specific functionality
    but are not installed or are incompatible versions.
    """

    pass
