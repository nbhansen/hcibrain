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



class ProcessingError(HciExtractorError):
    """Issues during document or data processing.

    Base class for all processing-related errors including PDF extraction,
    text normalization, and LLM analysis.
    """



# PDF Processing Exceptions
class PdfError(ProcessingError):
    """PDF-specific processing issues.

    Base class for all PDF-related errors during extraction and analysis.
    """

    def __init__(self, message: str = "PDF processing error"):
        super().__init__(message)


class PasswordProtectedError(PdfError):
    """PDF requires password for access.

    Raised when attempting to process a password-protected PDF without
    providing the correct password.
    """

    def __init__(self, message: str = "PDF requires password"):
        super().__init__(message)


class CorruptedFileError(PdfError):
    """PDF file is corrupted or unreadable.

    Raised when the PDF file cannot be opened or read due to corruption
    or invalid file format.
    """

    def __init__(self, message: str = "PDF file is corrupted"):
        super().__init__(message)


class NoTextLayerError(PdfError):
    """PDF contains only images, no extractable text.

    Raised when the PDF appears to be scanned images without a text layer
    that can be extracted programmatically.
    """

    def __init__(self, message: str = "PDF has no extractable text layer"):
        super().__init__(message)


class ExtractionQualityError(PdfError):
    """Extracted text quality below acceptable threshold.

    Raised when PDF extraction succeeds but the resulting text is too short,
    garbled, or otherwise of insufficient quality for analysis.
    """

    def __init__(self, message: str = "PDF extraction quality insufficient"):
        super().__init__(message)


# LLM Processing Exceptions
class LLMError(ProcessingError):
    """LLM-specific processing issues.

    Base class for all errors related to LLM providers, API calls,
    and response processing.
    """



class RateLimitError(LLMError):
    """LLM rate limit exceeded.

    Raised when the LLM provider's rate limits are exceeded and requests
    need to be retried after a delay.
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[float] = None):
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

    def __init__(self, message: str = "LLM validation failed"):
        super().__init__(message)


# Element Validation Exceptions
class ElementValidationError(LLMValidationError):
    """Element validation failed."""

    def __init__(self, message: str = "Element validation failed"):
        super().__init__(message)


class ElementFormatError(ElementValidationError):
    """Element format is invalid."""

    def __init__(self, message: str = "Invalid element format"):
        super().__init__(message)


class MissingRequiredFieldError(ElementValidationError):
    """Required field is missing."""

    def __init__(self, message: str = "Missing required field"):
        super().__init__(message)


class InvalidElementTypeError(ElementValidationError):
    """Element type is invalid."""

    def __init__(self, message: str = "Invalid element type"):
        super().__init__(message)


class InvalidEvidenceTypeError(ElementValidationError):
    """Evidence type is invalid."""

    def __init__(self, message: str = "Invalid evidence type"):
        super().__init__(message)


class InvalidConfidenceError(ElementValidationError):
    """Confidence value is invalid."""

    def __init__(self, message: str = "Invalid confidence value"):
        super().__init__(message)


class InvalidTextError(ElementValidationError):
    """Text field is invalid."""

    def __init__(self, message: str = "Invalid text field"):
        super().__init__(message)


# Response Validation Exceptions
class ResponseFormatError(LLMValidationError):
    """Response format is invalid."""

    def __init__(self, message: str = "Invalid response format"):
        super().__init__(message)


class ResponseFieldError(LLMValidationError):
    """Response field is missing or invalid."""

    def __init__(self, message: str = "Invalid response field"):
        super().__init__(message)


class ApiKeyError(LLMError):
    """LLM API key authentication failed.

    Raised when the provided API key is invalid, expired, or missing
    required permissions.
    """

    def __init__(self, message: str = "API key authentication failed"):
        super().__init__(message)


# Provider Configuration Exceptions
class ProviderConfigurationError(LLMError):
    """Provider configuration error."""

    def __init__(self, message: str = "Provider configuration error"):
        super().__init__(message)


class MissingApiKeyError(ProviderConfigurationError):
    """API key is missing."""

    def __init__(self, message: str = "API key not found"):
        super().__init__(message)


class ProviderInitializationError(ProviderConfigurationError):
    """Provider initialization failed."""

    def __init__(self, message: str = "Provider initialization failed"):
        super().__init__(message)


# API Response Exceptions
class EmptyResponseError(LLMError):
    """API returned empty response."""

    def __init__(self, message: str = "Empty response from API"):
        super().__init__(message)


class ContentFilterError(LLMError):
    """Content blocked by LLM safety filters.

    Raised when the LLM provider's safety filters prevent processing
    of the submitted content.
    """



class GeminiAuthenticationError(ApiKeyError):
    """Gemini authentication error."""

    def __init__(self, message: str = "Gemini authentication failed"):
        super().__init__(message)


class GeminiSafetyFilterError(ContentFilterError):
    """Gemini safety filter triggered."""

    def __init__(self, message: str = "Content blocked by safety filter"):
        super().__init__(message)


class GeminiApiError(LLMError):
    """General Gemini API error."""

    def __init__(self, message: str = "Gemini API error"):
        super().__init__(message)


class ModelNotFoundError(LLMError):
    """Requested LLM model is not available.

    Raised when the specified model name is not found or not accessible
    with the current API key.
    """



# Data Processing Exceptions
class DataError(ProcessingError):
    """Data validation and integrity issues.

    Base class for errors related to data model validation,
    serialization, and integrity checks.
    """



class SerializationError(DataError):
    """Data serialization/deserialization failed.

    Raised when converting data to/from JSON, CSV, or other formats fails.
    """



class DataValidationError(DataError):
    """Data validation failed.

    Raised when data doesn't meet required format, type, or business rules.
    """



# PDF Model Validation Exceptions
class PdfModelValidationError(DataValidationError):
    """PDF model validation failed.

    Base class for all PDF data model validation errors.
    """



class InvalidCharacterPosition(PdfModelValidationError):
    """Character position data is invalid."""

    def __init__(self, message: str = "Invalid character position"):
        super().__init__(message)


class InvalidPageNumber(PdfModelValidationError):
    """Page number is invalid."""

    def __init__(self, message: str = "Invalid page number"):
        super().__init__(message)


class InvalidBoundingBox(PdfModelValidationError):
    """Bounding box coordinates are invalid."""

    def __init__(self, message: str = "Invalid bounding box"):
        super().__init__(message)


class InvalidDimensions(PdfModelValidationError):
    """Page dimensions are invalid."""

    def __init__(self, message: str = "Invalid dimensions"):
        super().__init__(message)


class TextLengthMismatch(PdfModelValidationError):
    """Text length doesn't match character count."""

    def __init__(self, message: str = "Text length mismatch"):
        super().__init__(message)


class InvalidElementData(PdfModelValidationError):
    """PDF element data is invalid."""

    def __init__(self, message: str = "Invalid element data"):
        super().__init__(message)


class InvalidElementType(PdfModelValidationError):
    """PDF element type is invalid."""

    def __init__(self, message: str = "Invalid element type"):
        super().__init__(message)


class InvalidConfidenceScore(PdfModelValidationError):
    """Confidence score is outside valid range."""

    def __init__(self, message: str = "Invalid confidence score"):
        super().__init__(message)


# Configuration and Environment Exceptions
class ConfigurationError(HciExtractorError):
    """Configuration or environment setup issues.

    Raised when required configuration is missing, invalid, or
    environment setup is incomplete.
    """



class DependencyError(ConfigurationError):
    """Required dependency is missing or incompatible.

    Raised when optional dependencies are required for specific functionality
    but are not installed or are incompatible versions.
    """



# Additional PDF Processing Exceptions
class FileNotFoundError(PdfError):
    """PDF file not found."""

    def __init__(self, message: str = "PDF file not found"):
        super().__init__(message)


class InvalidFileTypeError(PdfError):
    """File is not a valid PDF."""

    def __init__(self, message: str = "File is not a valid PDF"):
        super().__init__(message)


# CLI-specific Exceptions
class CliError(HciExtractorError):
    """CLI command error."""

    def __init__(self, message: str = "CLI command failed"):
        super().__init__(message)


class InvalidProfileError(CliError):
    """Invalid profile specified."""

    def __init__(self, message: str = "Invalid profile specified"):
        super().__init__(message)


class InvalidParameterError(CliError):
    """Invalid parameter value."""

    def __init__(self, message: str = "Invalid parameter value"):
        super().__init__(message)


# Click-compatible CLI Exceptions (for CLI commands)
try:
    import click

    class ClickProfileError(click.ClickException):
        """Invalid profile for click commands."""

        def __init__(self, message: str = "Unknown profile"):
            super().__init__(message)

    class ClickParameterError(click.ClickException):
        """Invalid parameter for click commands."""

        def __init__(self, message: str = "Invalid parameter"):
            super().__init__(message)

except ImportError:
    # If click is not available, create dummy classes
    class ClickProfileErrorDummy(CliError):
        def __init__(self, message: str = "Unknown profile"):
            super().__init__(message)

    class ClickParameterErrorDummy(CliError):
        def __init__(self, message: str = "Invalid parameter"):
            super().__init__(message)

    # Assign to the same names for compatibility
    ClickProfileError = ClickProfileErrorDummy
    ClickParameterError = ClickParameterErrorDummy
