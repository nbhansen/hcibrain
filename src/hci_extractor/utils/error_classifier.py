"""
Error classification system for intelligent error handling and retry decisions.

This module provides comprehensive error classification to enable intelligent
retry strategies, user-friendly error messages, and graceful degradation.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from hci_extractor.core.models.exceptions import (
    ApiKeyError,
    ConfigurationError,
    ContentFilterError,
    CorruptedFileError,
    DataValidationError,
    DependencyError,
    ExtractionQualityError,
    LLMValidationError,
    ModelNotFoundError,
    NoTextLayerError,
    PasswordProtectedError,
    RateLimitError,
    SerializationError,
)

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for classification and handling."""

    RETRIABLE = "retriable"  # Errors that can be retried
    CONFIGURATION = "configuration"  # Configuration or environment issues
    API_PROVIDER = "api_provider"  # LLM provider API issues
    DOCUMENT_QUALITY = "document_quality"  # PDF/document quality issues
    SYSTEM_RESOURCE = "system_resource"  # System resource constraints
    USER_INPUT = "user_input"  # User input validation issues
    PERMANENT = "permanent"  # Permanent failures that shouldn't be retried


class ErrorSeverity(Enum):
    """Severity levels for error classification."""

    LOW = "low"  # Minor issues, processing can continue
    MEDIUM = "medium"  # Significant issues, may impact results
    HIGH = "high"  # Major issues, likely to cause failure
    CRITICAL = "critical"  # Critical failures, processing must stop


@dataclass(frozen=True)
class ErrorClassification:
    """Result of error classification analysis."""

    category: ErrorCategory
    severity: ErrorSeverity
    is_retriable: bool
    retry_strategy: Optional[str] = None
    user_message: Optional[str] = None
    remediation_steps: Optional[List[str]] = None
    confidence: float = 0.0  # 0.0-1.0 confidence in classification
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.remediation_steps is None:
            object.__setattr__(self, "remediation_steps", [])
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


class ErrorClassifier:
    """Intelligent error classification system."""

    def __init__(self) -> None:
        self._classification_rules = self._build_classification_rules()
        self._pattern_matchers = self._build_pattern_matchers()

    def classify_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> ErrorClassification:
        """
        Classify an error for intelligent handling.

        Args:
            error: The exception to classify
            context: Additional context about the error occurrence

        Returns:
            ErrorClassification with recommended handling strategy
        """
        if context is None:
            context = {}

        # Start with exception type classification
        base_classification = self._classify_by_type(error)

        # Enhance with message pattern analysis
        message_classification = self._classify_by_message(error, context)

        # Combine and refine classifications
        final_classification = self._combine_classifications(
            base_classification, message_classification, error, context
        )

        logger.debug(
            f"Error classified as {final_classification.category.value} "
            f"(severity: {final_classification.severity.value}, "
            f"retriable: {final_classification.is_retriable})"
        )

        return final_classification

    def _classify_by_type(self, error: Exception) -> ErrorClassification:
        """Classify error based on exception type."""
        error_type = type(error)

        # Check direct type matches first
        if error_type in self._classification_rules:
            return self._classification_rules[error_type]

        # Check inheritance hierarchy
        for exception_type, classification in self._classification_rules.items():
            if isinstance(error, exception_type):
                return classification

        # Default classification for unknown errors
        return ErrorClassification(
            category=ErrorCategory.SYSTEM_RESOURCE,
            severity=ErrorSeverity.MEDIUM,
            is_retriable=True,
            retry_strategy="exponential_backoff",
            user_message="An unexpected error occurred during processing",
            remediation_steps=["Check system resources and try again"],
            confidence=0.3,
            metadata={"error_type": error_type.__name__},
        )

    def _classify_by_message(
        self, error: Exception, context: Dict[str, Any]
    ) -> Optional[ErrorClassification]:
        """Classify error based on error message patterns."""
        message = str(error).lower()

        for pattern, classification_func in self._pattern_matchers.items():
            if re.search(pattern, message, re.IGNORECASE):
                return classification_func(error, message, context)

        return None

    def _combine_classifications(
        self,
        base: ErrorClassification,
        message: Optional[ErrorClassification],
        error: Exception,
        context: Dict[str, Any],
    ) -> ErrorClassification:
        """Combine type-based and message-based classifications."""

        if message is None:
            return base

        # Message classification takes precedence for specific patterns
        if message.confidence > base.confidence:
            return message

        # Combine information from both classifications
        combined_metadata = {**(base.metadata or {}), **(message.metadata or {})}
        combined_steps = list(
            set((base.remediation_steps or []) + (message.remediation_steps or []))
        )

        return ErrorClassification(
            category=message.category if message.confidence > 0.7 else base.category,
            severity=max(base.severity, message.severity, key=lambda x: x.value),
            is_retriable=base.is_retriable and message.is_retriable,
            retry_strategy=message.retry_strategy or base.retry_strategy,
            user_message=message.user_message or base.user_message,
            remediation_steps=combined_steps,
            confidence=max(base.confidence, message.confidence),
            metadata=combined_metadata,
        )

    def _build_classification_rules(self) -> Dict[Type[Exception], ErrorClassification]:
        """Build classification rules based on exception types."""
        return {
            # PDF Processing Errors
            PasswordProtectedError: ErrorClassification(
                category=ErrorCategory.USER_INPUT,
                severity=ErrorSeverity.HIGH,
                is_retriable=False,
                user_message="PDF is password protected",
                remediation_steps=[
                    "Provide the PDF password if available",
                    "Try a different version of the PDF",
                    "Contact the document owner for access",
                ],
                confidence=0.95,
                metadata={"pdf_issue": "password_protected"},
            ),
            CorruptedFileError: ErrorClassification(
                category=ErrorCategory.DOCUMENT_QUALITY,
                severity=ErrorSeverity.HIGH,
                is_retriable=False,
                user_message="PDF file is corrupted or unreadable",
                remediation_steps=[
                    "Try re-downloading the PDF",
                    "Verify the file is not corrupted",
                    "Use a different version of the document",
                ],
                confidence=0.95,
                metadata={"pdf_issue": "corrupted"},
            ),
            NoTextLayerError: ErrorClassification(
                category=ErrorCategory.DOCUMENT_QUALITY,
                severity=ErrorSeverity.HIGH,
                is_retriable=False,
                user_message="PDF contains only images with no extractable text",
                remediation_steps=[
                    "Use OCR software to extract text first",
                    "Try a text-searchable version of the PDF",
                    "Consider manual text extraction",
                ],
                confidence=0.95,
                metadata={"pdf_issue": "no_text_layer"},
            ),
            ExtractionQualityError: ErrorClassification(
                category=ErrorCategory.DOCUMENT_QUALITY,
                severity=ErrorSeverity.MEDIUM,
                is_retriable=True,
                retry_strategy="linear_backoff",
                user_message="Extracted text quality is below acceptable threshold",
                remediation_steps=[
                    "Try with different extraction settings",
                    "Verify PDF quality and readability",
                    "Consider preprocessing the document",
                ],
                confidence=0.9,
                metadata={"pdf_issue": "low_quality"},
            ),
            # LLM Provider Errors
            RateLimitError: ErrorClassification(
                category=ErrorCategory.API_PROVIDER,
                severity=ErrorSeverity.MEDIUM,
                is_retriable=True,
                retry_strategy="exponential_backoff",
                user_message="API rate limit exceeded, will retry with delay",
                remediation_steps=[
                    "Wait for rate limit reset",
                    "Reduce concurrent requests",
                    "Consider upgrading API plan",
                ],
                confidence=0.98,
                metadata={"api_issue": "rate_limit"},
            ),
            ApiKeyError: ErrorClassification(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.CRITICAL,
                is_retriable=False,
                user_message="API key is invalid or missing",
                remediation_steps=[
                    "Verify API key is correctly set",
                    "Check API key permissions",
                    "Regenerate API key if needed",
                ],
                confidence=0.98,
                metadata={"config_issue": "api_key"},
            ),
            ModelNotFoundError: ErrorClassification(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                is_retriable=False,
                user_message="Requested model is not available",
                remediation_steps=[
                    "Check model name spelling",
                    "Verify model is available with your API key",
                    "Try a different model",
                ],
                confidence=0.95,
                metadata={"config_issue": "model_not_found"},
            ),
            ContentFilterError: ErrorClassification(
                category=ErrorCategory.DOCUMENT_QUALITY,
                severity=ErrorSeverity.MEDIUM,
                is_retriable=False,
                user_message="Content blocked by safety filters",
                remediation_steps=[
                    "Review document content for sensitive material",
                    "Try with different extraction settings",
                    "Consider content preprocessing",
                ],
                confidence=0.9,
                metadata={"api_issue": "content_filter"},
            ),
            LLMValidationError: ErrorClassification(
                category=ErrorCategory.RETRIABLE,
                severity=ErrorSeverity.MEDIUM,
                is_retriable=True,
                retry_strategy="immediate",
                user_message="LLM response validation failed, will retry",
                remediation_steps=[
                    "Automatic retry with JSON recovery",
                    "Consider adjusting temperature settings",
                    "Check prompt formatting",
                ],
                confidence=0.85,
                metadata={"llm_issue": "validation_failed"},
            ),
            # Configuration and System Errors
            ConfigurationError: ErrorClassification(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                is_retriable=False,
                user_message="Configuration error detected",
                remediation_steps=[
                    "Check configuration settings",
                    "Verify environment variables",
                    "Review configuration documentation",
                ],
                confidence=0.9,
                metadata={"config_issue": "general"},
            ),
            DependencyError: ErrorClassification(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.CRITICAL,
                is_retriable=False,
                user_message="Required dependency is missing or incompatible",
                remediation_steps=[
                    "Install required dependencies",
                    "Check dependency versions",
                    "Review installation instructions",
                ],
                confidence=0.95,
                metadata={"config_issue": "dependencies"},
            ),
            # Data Processing Errors
            DataValidationError: ErrorClassification(
                category=ErrorCategory.RETRIABLE,
                severity=ErrorSeverity.MEDIUM,
                is_retriable=True,
                retry_strategy="immediate",
                user_message="Data validation failed, will retry",
                remediation_steps=[
                    "Automatic retry with data recovery",
                    "Check data format requirements",
                    "Review input data quality",
                ],
                confidence=0.8,
                metadata={"data_issue": "validation"},
            ),
            SerializationError: ErrorClassification(
                category=ErrorCategory.RETRIABLE,
                severity=ErrorSeverity.MEDIUM,
                is_retriable=True,
                retry_strategy="immediate",
                user_message="Data serialization failed, will retry",
                remediation_steps=[
                    "Automatic retry with format recovery",
                    "Check output format settings",
                    "Verify data structure compatibility",
                ],
                confidence=0.8,
                metadata={"data_issue": "serialization"},
            ),
        }

    def _build_pattern_matchers(
        self,
    ) -> Dict[str, Callable[[Exception, str, Dict[str, Any]], ErrorClassification]]:
        """Build pattern matchers for message-based classification."""
        return {
            # Network and connectivity issues
            r"connection.*(?:timeout|refused|reset|failed)": self._classify_network_error,
            r"(?:network|socket|ssl).*error": self._classify_network_error,
            r"dns.*(?:resolution|lookup).*failed": self._classify_network_error,
            # Memory and resource issues
            r"memory.*(?:error|allocation|insufficient)": self._classify_memory_error,
            r"out of memory|memory exhausted": self._classify_memory_error,
            r"disk.*(?:full|space|quota)": self._classify_disk_error,
            r"too many open files": self._classify_resource_error,
            # API specific patterns
            r"quota.*(?:exceeded|exhausted)": self._classify_quota_error,
            r"unauthorized|authentication.*failed": self._classify_auth_error,
            r"forbidden|access.*denied": self._classify_permission_error,
            r"service.*unavailable|502|503|504": self._classify_service_error,
            # File system issues
            r"permission.*denied|access.*denied": self._classify_permission_error,
            r"file.*not.*found|no such file": self._classify_file_error,
            r"directory.*not.*found": self._classify_file_error,
            r"file.*(?:locked|in use)": self._classify_file_lock_error,
            # JSON and parsing issues
            r"json.*(?:decode|parse).*error": self._classify_json_error,
            r"invalid.*json|malformed.*json": self._classify_json_error,
            r"unexpected.*(?:token|character)": self._classify_parsing_error,
            # Timeout issues
            r"timeout|timed out": self._classify_timeout_error,
            r"request.*(?:timeout|exceeded)": self._classify_timeout_error,
        }

    def _classify_network_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify network-related errors."""
        return ErrorClassification(
            category=ErrorCategory.RETRIABLE,
            severity=ErrorSeverity.MEDIUM,
            is_retriable=True,
            retry_strategy="exponential_backoff",
            user_message="Network connection issue, will retry",
            remediation_steps=[
                "Check internet connection",
                "Verify API endpoint availability",
                "Try again in a few moments",
            ],
            confidence=0.9,
            metadata={"network_issue": True, "pattern_match": "network"},
        )

    def _classify_memory_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify memory-related errors."""
        return ErrorClassification(
            category=ErrorCategory.SYSTEM_RESOURCE,
            severity=ErrorSeverity.HIGH,
            is_retriable=False,
            user_message="Insufficient memory for processing",
            remediation_steps=[
                "Try processing smaller documents",
                "Close other applications",
                "Consider increasing system memory",
            ],
            confidence=0.95,
            metadata={"resource_issue": "memory", "pattern_match": "memory"},
        )

    def _classify_disk_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify disk space errors."""
        return ErrorClassification(
            category=ErrorCategory.SYSTEM_RESOURCE,
            severity=ErrorSeverity.HIGH,
            is_retriable=False,
            user_message="Insufficient disk space",
            remediation_steps=[
                "Free up disk space",
                "Choose a different output directory",
                "Clean up temporary files",
            ],
            confidence=0.95,
            metadata={"resource_issue": "disk", "pattern_match": "disk"},
        )

    def _classify_resource_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify general resource errors."""
        return ErrorClassification(
            category=ErrorCategory.SYSTEM_RESOURCE,
            severity=ErrorSeverity.MEDIUM,
            is_retriable=True,
            retry_strategy="linear_backoff",
            user_message="System resource constraints, will retry",
            remediation_steps=[
                "Close unnecessary applications",
                "Reduce concurrent processing",
                "Try again with fewer resources",
            ],
            confidence=0.8,
            metadata={"resource_issue": "general", "pattern_match": "resource"},
        )

    def _classify_quota_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify API quota errors."""
        return ErrorClassification(
            category=ErrorCategory.API_PROVIDER,
            severity=ErrorSeverity.HIGH,
            is_retriable=False,
            user_message="API quota exceeded",
            remediation_steps=[
                "Wait for quota reset",
                "Upgrade API plan",
                "Consider alternative providers",
            ],
            confidence=0.95,
            metadata={"api_issue": "quota", "pattern_match": "quota"},
        )

    def _classify_auth_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify authentication errors."""
        return ErrorClassification(
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            is_retriable=False,
            user_message="Authentication failed",
            remediation_steps=[
                "Verify API credentials",
                "Check authentication configuration",
                "Regenerate API keys if needed",
            ],
            confidence=0.95,
            metadata={"config_issue": "authentication", "pattern_match": "auth"},
        )

    def _classify_permission_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify permission errors."""
        return ErrorClassification(
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            is_retriable=False,
            user_message="Permission denied",
            remediation_steps=[
                "Check file/directory permissions",
                "Verify API key permissions",
                "Run with appropriate privileges",
            ],
            confidence=0.9,
            metadata={"config_issue": "permissions", "pattern_match": "permission"},
        )

    def _classify_service_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify service availability errors."""
        return ErrorClassification(
            category=ErrorCategory.API_PROVIDER,
            severity=ErrorSeverity.MEDIUM,
            is_retriable=True,
            retry_strategy="exponential_backoff",
            user_message="Service temporarily unavailable, will retry",
            remediation_steps=[
                "Wait for service recovery",
                "Check service status page",
                "Try alternative providers",
            ],
            confidence=0.9,
            metadata={"api_issue": "service_unavailable", "pattern_match": "service"},
        )

    def _classify_file_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify file system errors."""
        return ErrorClassification(
            category=ErrorCategory.USER_INPUT,
            severity=ErrorSeverity.HIGH,
            is_retriable=False,
            user_message="File not found or inaccessible",
            remediation_steps=[
                "Verify file path is correct",
                "Check file exists and is readable",
                "Ensure proper file permissions",
            ],
            confidence=0.9,
            metadata={"file_issue": True, "pattern_match": "file"},
        )

    def _classify_file_lock_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify file lock errors."""
        return ErrorClassification(
            category=ErrorCategory.SYSTEM_RESOURCE,
            severity=ErrorSeverity.MEDIUM,
            is_retriable=True,
            retry_strategy="linear_backoff",
            user_message="File is locked or in use, will retry",
            remediation_steps=[
                "Close applications using the file",
                "Wait for file to be released",
                "Try with a different file",
            ],
            confidence=0.85,
            metadata={"file_issue": "locked", "pattern_match": "file_lock"},
        )

    def _classify_json_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify JSON parsing errors."""
        return ErrorClassification(
            category=ErrorCategory.RETRIABLE,
            severity=ErrorSeverity.MEDIUM,
            is_retriable=True,
            retry_strategy="immediate",
            user_message="JSON parsing failed, will retry with recovery",
            remediation_steps=[
                "Automatic JSON recovery attempt",
                "Check JSON format requirements",
                "Review data structure",
            ],
            confidence=0.85,
            metadata={"data_issue": "json", "pattern_match": "json"},
        )

    def _classify_parsing_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify general parsing errors."""
        return ErrorClassification(
            category=ErrorCategory.RETRIABLE,
            severity=ErrorSeverity.MEDIUM,
            is_retriable=True,
            retry_strategy="immediate",
            user_message="Parsing error, will retry with recovery",
            remediation_steps=[
                "Automatic parsing recovery attempt",
                "Check data format",
                "Review input structure",
            ],
            confidence=0.8,
            metadata={"data_issue": "parsing", "pattern_match": "parsing"},
        )

    def _classify_timeout_error(
        self, error: Exception, message: str, context: Dict[str, Any]
    ) -> ErrorClassification:
        """Classify timeout errors."""
        return ErrorClassification(
            category=ErrorCategory.RETRIABLE,
            severity=ErrorSeverity.MEDIUM,
            is_retriable=True,
            retry_strategy="exponential_backoff",
            user_message="Request timed out, will retry",
            remediation_steps=[
                "Automatic retry with longer timeout",
                "Check network connectivity",
                "Try with smaller requests",
            ],
            confidence=0.9,
            metadata={"timeout_issue": True, "pattern_match": "timeout"},
        )


# Global error classifier instance
_error_classifier = ErrorClassifier()


def classify_error(
    error: Exception, context: Optional[Dict[str, Any]] = None
) -> ErrorClassification:
    """
    Classify an error for intelligent handling.

    Args:
        error: The exception to classify
        context: Additional context about the error occurrence

    Returns:
        ErrorClassification with recommended handling strategy
    """
    return _error_classifier.classify_error(error, context)


def is_retriable_error(
    error: Exception, context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Check if an error should be retried.

    Args:
        error: The exception to check
        context: Additional context about the error occurrence

    Returns:
        True if the error should be retried
    """
    classification = classify_error(error, context)
    return classification.is_retriable


def get_retry_strategy(
    error: Exception, context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Get the recommended retry strategy for an error.

    Args:
        error: The exception to analyze
        context: Additional context about the error occurrence

    Returns:
        Recommended retry strategy name, or None if not retriable
    """
    classification = classify_error(error, context)
    return classification.retry_strategy if classification.is_retriable else None


def get_user_friendly_message(
    error: Exception, context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get a user-friendly error message.

    Args:
        error: The exception to translate
        context: Additional context about the error occurrence

    Returns:
        User-friendly error message
    """
    classification = classify_error(error, context)
    return classification.user_message or str(error)


def get_remediation_steps(
    error: Exception, context: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Get remediation steps for an error.

    Args:
        error: The exception to analyze
        context: Additional context about the error occurrence

    Returns:
        List of remediation steps
    """
    classification = classify_error(error, context)
    return classification.remediation_steps or []
