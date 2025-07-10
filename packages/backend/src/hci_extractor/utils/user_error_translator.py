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

# Simplified error translation - no complex classification needed

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
        self._default_icon = "⚠️"

    def translate_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> UserErrorMessage:
        """
        Translate a technical error into a user-friendly message.

        Args:
            error: The exception to translate
            context: Additional context about the error

        Returns:
            UserErrorMessage with clear explanation and guidance
        """
        # Simplified error handling - create basic user message
        user_message = self._create_simple_user_message(error, context)

        logger.debug(f"Translated error: {user_message.title}")
        return user_message

    def _create_simple_user_message(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]],
    ) -> UserErrorMessage:
        """Create a simple user error message."""

        # Determine basic error info from exception type and message
        (
            title,
            message,
            severity,
            remediation_steps,
            quick_fixes,
        ) = self._analyze_error(error)

        # Add context-specific details
        context_details = self._add_context_details(message, context)

        return UserErrorMessage(
            title=f"{self._default_icon} {title}",
            message=context_details,
            severity=severity,
            remediation_steps=tuple(remediation_steps),
            technical_details=f"{type(error).__name__}: {error!s}",
            quick_fixes=tuple(quick_fixes),
            related_docs=self._get_basic_docs(),
        )

    def _analyze_error(
        self,
        error: Exception,
    ) -> tuple[str, str, MessageSeverity, list[str], list[str]]:
        """Analyze error to determine basic info."""
        error_message = str(error).lower()

        # Basic pattern matching for common error types
        if "timeout" in error_message or "timed out" in error_message:
            return (
                "Request Timeout",
                "The request took too long to complete.",
                MessageSeverity.WARNING,
                ["Try again in a few moments", "Check your network connection"],
                ["Retry the operation", "Check network connectivity"],
            )

        if "connection" in error_message or "network" in error_message:
            return (
                "Network Issue",
                "There was a problem connecting to the service.",
                MessageSeverity.WARNING,
                ["Check your internet connection", "Try again in a few moments"],
                ["Verify network connectivity", "Retry the operation"],
            )

        if "permission" in error_message or "access" in error_message:
            return (
                "Permission Error",
                "Access to the resource was denied.",
                MessageSeverity.ERROR,
                ["Check file permissions", "Verify access rights"],
                ["Check permissions", "Contact administrator"],
            )

        if "memory" in error_message or "out of memory" in error_message:
            return (
                "Memory Issue",
                "Insufficient memory to complete the operation.",
                MessageSeverity.ERROR,
                ["Close other applications", "Try with smaller files"],
                ["Free memory", "Use smaller data sets"],
            )

        if "file not found" in error_message or "no such file" in error_message:
            return (
                "File Not Found",
                "The specified file could not be found.",
                MessageSeverity.ERROR,
                ["Check file path", "Verify file exists"],
                ["Verify file path", "Check file existence"],
            )

        if "api" in error_message or "authentication" in error_message:
            return (
                "API Error",
                "There was an issue with the API service.",
                MessageSeverity.ERROR,
                ["Check API credentials", "Verify service availability"],
                ["Check API key", "Verify service status"],
            )

        return (
            "Processing Error",
            "An error occurred during processing.",
            MessageSeverity.ERROR,
            ["Try again", "Check input data"],
            ["Retry operation", "Verify input"],
        )

    def _add_context_details(
        self,
        base_message: str,
        context: Optional[Dict[str, Any]],
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

    def _get_basic_docs(self) -> tuple[str, ...]:
        """Get basic documentation references."""
        return (
            "General Troubleshooting: Common issues and solutions",
            "Configuration Guide: Setup and configuration",
            "API Documentation: Service usage and limits",
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


# Error translator will be managed via DI container - no global instance


def translate_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> UserErrorMessage:
    """
    Translate a technical error into a user-friendly message.

    Args:
        error: The exception to translate
        context: Additional context about the error

    Returns:
        UserErrorMessage with clear explanation and guidance
    """
    # Create new instance instead of using global state
    error_translator = UserErrorTranslator()
    return error_translator.translate_error(error, context)


def format_error_for_cli(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
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

    # Create translator instance instead of using global reference
    translator = UserErrorTranslator()
    return translator.format_for_cli(user_message)


def create_user_friendly_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
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
