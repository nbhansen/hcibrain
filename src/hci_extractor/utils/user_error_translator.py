"""
User-friendly error message translation system.

This module converts technical errors into clear, actionable messages that help
users understand what went wrong and how to fix it.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import click

from hci_extractor.utils.error_classifier import (
    ErrorCategory,
    ErrorClassification,
    ErrorSeverity,
    classify_error,
)

logger = logging.getLogger(__name__)


class MessageSeverity(Enum):
    """Severity levels for user messages."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class UserErrorMessage:
    """User-friendly error message with formatting and actions."""

    title: str
    message: str
    severity: MessageSeverity
    remediation_steps: Tuple[str, ...]
    technical_details: Optional[str] = None
    quick_fixes: Tuple[str, ...] = ()
    related_docs: Tuple[str, ...] = ()


class UserErrorTranslator:
    """Translates technical errors into user-friendly messages."""

    def __init__(self) -> None:
        self._severity_mapping = {
            ErrorSeverity.LOW: MessageSeverity.WARNING,
            ErrorSeverity.MEDIUM: MessageSeverity.ERROR,
            ErrorSeverity.HIGH: MessageSeverity.ERROR,
            ErrorSeverity.CRITICAL: MessageSeverity.CRITICAL,
        }

        self._category_icons = {
            ErrorCategory.RETRIABLE: "🔄",
            ErrorCategory.CONFIGURATION: "⚙️",
            ErrorCategory.API_PROVIDER: "🌐",
            ErrorCategory.DOCUMENT_QUALITY: "📄",
            ErrorCategory.SYSTEM_RESOURCE: "💾",
            ErrorCategory.USER_INPUT: "📝",
            ErrorCategory.PERMANENT: "❌",
        }

    def translate_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> UserErrorMessage:
        """
        Translate a technical error into a user-friendly message.

        Args:
            error: The exception to translate
            context: Additional context about the error

        Returns:
            UserErrorMessage with clear explanation and guidance
        """
        # Get error classification
        classification = classify_error(error, context)

        # Generate user-friendly message
        user_message = self._create_user_message(error, classification, context)

        logger.debug(f"Translated error: {user_message.title}")
        return user_message

    def _create_user_message(
        self,
        error: Exception,
        classification: ErrorClassification,
        context: Optional[Dict[str, Any]],
    ) -> UserErrorMessage:
        """Create a comprehensive user error message."""

        # Get category-specific messaging
        category_info = self._get_category_messaging(classification.category)

        # Build title with icon
        icon = self._category_icons.get(classification.category, "⚠️")
        title = f"{icon} {category_info['title']}"

        # Build main message
        if classification.user_message:
            main_message = classification.user_message
        else:
            main_message = category_info["default_message"]

        # Add context-specific details
        context_details = self._add_context_details(main_message, context)

        # Get severity
        severity = self._severity_mapping.get(
            classification.severity, MessageSeverity.ERROR
        )

        # Build quick fixes
        quick_fixes = self._generate_quick_fixes(classification, context)

        # Build related documentation links
        related_docs = self._get_related_docs(classification.category)

        return UserErrorMessage(
            title=title,
            message=context_details,
            severity=severity,
            remediation_steps=tuple(classification.remediation_steps or []),
            technical_details=f"{type(error).__name__}: {str(error)}",
            quick_fixes=quick_fixes,
            related_docs=related_docs,
        )

    def _get_category_messaging(self, category: ErrorCategory) -> Dict[str, str]:
        """Get category-specific messaging templates."""

        messaging = {
            ErrorCategory.RETRIABLE: {
                "title": "Temporary Issue",
                "default_message": "A temporary issue occurred that should "
                "resolve automatically.",
            },
            ErrorCategory.CONFIGURATION: {
                "title": "Configuration Problem",
                "default_message": "There's an issue with your configuration settings.",
            },
            ErrorCategory.API_PROVIDER: {
                "title": "API Service Issue",
                "default_message": "The API service is experiencing difficulties.",
            },
            ErrorCategory.DOCUMENT_QUALITY: {
                "title": "Document Issue",
                "default_message": "There's an issue with the document that "
                "prevents processing.",
            },
            ErrorCategory.SYSTEM_RESOURCE: {
                "title": "System Resource Issue",
                "default_message": "Your system doesn't have enough resources "
                "to complete this operation.",
            },
            ErrorCategory.USER_INPUT: {
                "title": "Input Problem",
                "default_message": "There's an issue with the provided input.",
            },
            ErrorCategory.PERMANENT: {
                "title": "Processing Failed",
                "default_message": "This operation cannot be completed due to "
                "a permanent issue.",
            },
        }

        return messaging.get(
            category,
            {
                "title": "Unexpected Error",
                "default_message": "An unexpected error occurred during processing.",
            },
        )

    def _add_context_details(
        self, base_message: str, context: Optional[Dict[str, Any]]
    ) -> str:
        """Add context-specific details to the message."""

        if not context:
            return base_message

        details = []

        # Add operation context
        if "operation" in context:
            operation = context["operation"].replace("_", " ").title()
            details.append(f"During: {operation}")

        # Add file context
        if "file_path" in context:
            details.append(f"File: {context['file_path']}")

        # Add section context
        if "section_type" in context:
            details.append(f"Section: {context['section_type']}")

        # Add paper context
        if "paper_id" in context:
            details.append(f"Paper: {context['paper_id']}")

        if details:
            context_str = " | ".join(details)
            return f"{base_message}\n\nContext: {context_str}"

        return base_message

    def _generate_quick_fixes(
        self, classification: ErrorClassification, context: Optional[Dict[str, Any]]
    ) -> Tuple[str, ...]:
        """Generate quick fix suggestions based on error classification."""

        quick_fixes = []

        # Category-specific quick fixes
        if classification.category == ErrorCategory.CONFIGURATION:
            quick_fixes.extend(
                [
                    "Run 'hci-extractor diagnose' to check configuration",
                    "Verify environment variables are set correctly",
                    "Try 'hci-extractor config' to see available options",
                ]
            )

        elif classification.category == ErrorCategory.API_PROVIDER:
            quick_fixes.extend(
                [
                    "Check your internet connection",
                    "Verify API key is valid and has sufficient quota",
                    "Try again in a few minutes",
                ]
            )

        elif classification.category == ErrorCategory.DOCUMENT_QUALITY:
            quick_fixes.extend(
                [
                    "Try a different version of the PDF",
                    "Check if the file is corrupted or password-protected",
                    "Use 'hci-extractor validate' to check document",
                ]
            )

        elif classification.category == ErrorCategory.SYSTEM_RESOURCE:
            quick_fixes.extend(
                [
                    "Close other applications to free memory",
                    "Try processing a smaller document first",
                    "Reduce --chunk-size to use less memory",
                ]
            )

        elif classification.category == ErrorCategory.RETRIABLE:
            quick_fixes.extend(
                [
                    "This should resolve automatically with retry",
                    "If persistent, try reducing --max-concurrent",
                    "Check system resources and network connection",
                ]
            )

        # Context-specific quick fixes
        if context:
            if context.get("operation") == "batch_processing":
                quick_fixes.append(
                    "Try processing files individually to isolate the issue"
                )

            if "section_size" in context and context["section_size"] > 15000:
                quick_fixes.append("Large section detected - try reducing --chunk-size")

        return tuple(quick_fixes[:3])  # Limit to 3 most relevant fixes

    def _get_related_docs(self, category: ErrorCategory) -> Tuple[str, ...]:
        """Get related documentation links for the error category."""

        docs = {
            ErrorCategory.CONFIGURATION: (
                "Configuration Guide: hci-extractor config",
                "Environment Variables: Set HCI_* variables",
                "Profile Selection: hci-extractor profiles",
            ),
            ErrorCategory.API_PROVIDER: (
                "API Setup Guide: Getting your API key",
                "Rate Limits: Understanding API quotas",
                "Troubleshooting: Network and API issues",
            ),
            ErrorCategory.DOCUMENT_QUALITY: (
                "Supported Formats: PDF requirements",
                "Document Validation: hci-extractor validate",
                "Quality Issues: Common PDF problems",
            ),
            ErrorCategory.SYSTEM_RESOURCE: (
                "Performance Tuning: Optimizing memory usage",
                "Configuration: Reducing resource requirements",
                "System Requirements: Minimum specifications",
            ),
        }

        return docs.get(
            category, ("General Troubleshooting: Common issues and solutions",)
        )

    def format_for_cli(self, user_message: UserErrorMessage) -> str:
        """Format the user message for CLI display with colors and styling."""

        # Choose color based on severity
        color_map = {
            MessageSeverity.INFO: "blue",
            MessageSeverity.WARNING: "yellow",
            MessageSeverity.ERROR: "red",
            MessageSeverity.CRITICAL: "red",
        }

        color = color_map.get(user_message.severity, "red")

        # Build formatted message
        lines = []

        # Title with color
        lines.append(click.style(user_message.title, fg=color, bold=True))
        lines.append("")

        # Main message
        lines.append(user_message.message)
        lines.append("")

        # Remediation steps
        if user_message.remediation_steps:
            lines.append(click.style("🔧 How to fix:", bold=True, fg="green"))
            for i, step in enumerate(user_message.remediation_steps, 1):
                lines.append(f"  {i}. {step}")
            lines.append("")

        # Quick fixes
        if user_message.quick_fixes:
            lines.append(click.style("⚡ Quick fixes:", bold=True, fg="cyan"))
            for fix in user_message.quick_fixes:
                lines.append(f"  • {fix}")
            lines.append("")

        # Related docs
        if user_message.related_docs:
            lines.append(click.style("📚 Related help:", bold=True, fg="blue"))
            for doc in user_message.related_docs:
                lines.append(f"  • {doc}")
            lines.append("")

        # Technical details (only in verbose mode)
        if user_message.technical_details:
            lines.append(click.style("🔍 Technical details:", bold=True, fg="black"))
            lines.append(f"  {user_message.technical_details}")

        return "\n".join(lines)


# Global translator instance
_error_translator = UserErrorTranslator()


def translate_error(
    error: Exception, context: Optional[Dict[str, Any]] = None
) -> UserErrorMessage:
    """
    Translate a technical error into a user-friendly message.

    Args:
        error: The exception to translate
        context: Additional context about the error

    Returns:
        UserErrorMessage with clear explanation and guidance
    """
    return _error_translator.translate_error(error, context)


def format_error_for_cli(
    error: Exception, context: Optional[Dict[str, Any]] = None, verbose: bool = False
) -> str:
    """
    Format an error for CLI display with colors and helpful guidance.

    Args:
        error: The exception to format
        context: Additional context about the error
        verbose: Whether to include technical details

    Returns:
        Formatted error message string
    """
    user_message = translate_error(error, context)

    # Remove technical details if not verbose
    if not verbose:
        user_message = UserErrorMessage(
            title=user_message.title,
            message=user_message.message,
            severity=user_message.severity,
            remediation_steps=user_message.remediation_steps,
            technical_details=None,
            quick_fixes=user_message.quick_fixes,
            related_docs=user_message.related_docs,
        )

    return _error_translator.format_for_cli(user_message)


def create_user_friendly_exception(
    error: Exception, context: Optional[Dict[str, Any]] = None
) -> click.ClickException:
    """
    Create a Click exception with user-friendly formatting.

    Args:
        error: The original exception
        context: Additional context about the error

    Returns:
        ClickException with formatted user message
    """
    formatted_message = format_error_for_cli(error, context, verbose=False)
    return click.ClickException(formatted_message)
