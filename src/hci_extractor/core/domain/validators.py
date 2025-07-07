"""Domain validators for HCI extractor - pure business logic validation."""

from typing import Any, Dict

from hci_extractor.core.models.exceptions import (
    ElementFormatError,
    InvalidConfidenceError,
    InvalidElementTypeError,
    InvalidEvidenceTypeError,
    InvalidTextError,
    LLMValidationError,
    MissingRequiredFieldError,
    ResponseFieldError,
    ResponseFormatError,
)


class ElementValidator:
    """Validates extracted elements according to domain rules."""

    # Domain constants for valid values
    VALID_ELEMENT_TYPES = frozenset(["claim", "finding", "method", "artifact"])
    VALID_EVIDENCE_TYPES = frozenset(
        ["quantitative", "qualitative", "theoretical", "mixed", "unknown"]
    )
    MIN_TEXT_LENGTH = 10

    @classmethod
    def validate_element(cls, element: Dict[str, Any], index: int) -> None:
        """
        Validate a single element according to domain rules.

        Args:
            element: The element to validate
            index: Element index for error messages

        Raises:
            LLMValidationError: If validation fails
        """
        if not isinstance(element, dict):
            raise ElementFormatError()

        # Check required fields
        required_fields = ["element_type", "text", "evidence_type", "confidence"]
        for field in required_fields:
            if field not in element:
                raise MissingRequiredFieldError()

        # Validate element_type
        if element["element_type"] not in cls.VALID_ELEMENT_TYPES:
            raise InvalidElementTypeError()

        # Validate evidence_type
        if element["evidence_type"] not in cls.VALID_EVIDENCE_TYPES:
            raise InvalidEvidenceTypeError()

        # Validate confidence
        if not isinstance(element["confidence"], (int, float)):
            raise InvalidConfidenceError()

        if not 0.0 <= element["confidence"] <= 1.0:
            raise InvalidConfidenceError()

        # Validate text
        if not isinstance(element["text"], str) or not element["text"].strip():
            raise InvalidTextError()

    @classmethod
    def validate_response(cls, response: Dict[str, Any]) -> None:
        """
        Validate the complete LLM response structure.

        Args:
            response: Raw response from LLM

        Raises:
            LLMValidationError: If validation fails
        """
        if not isinstance(response, dict):
            raise ResponseFormatError()

        if "elements" not in response:
            raise ResponseFieldError()

        elements = response["elements"]
        if not isinstance(elements, list):
            raise ResponseFieldError()

        # Validate each element
        for i, element in enumerate(elements):
            cls.validate_element(element, i)

    @classmethod
    def is_valid_element_for_inclusion(cls, element: Dict[str, Any]) -> bool:
        """
        Check if element meets criteria for inclusion in results.

        Args:
            element: The element to check

        Returns:
            True if element should be included, False otherwise
        """
        # Skip empty or very short extractions
        return len(element.get("text", "")) >= cls.MIN_TEXT_LENGTH


class SummaryValidator:
    """Validates paper summary responses according to domain rules."""

    @classmethod
    def validate_summary(cls, response: Dict[str, Any]) -> None:
        """
        Validate paper summary response structure and content.

        Args:
            response: Summary response to validate

        Raises:
            LLMValidationError: If validation fails
        """
        if not isinstance(response, dict):
            raise ResponseFormatError()

        # Check required fields
        required_fields = ["summary", "confidence", "source_sections"]
        for field in required_fields:
            if field not in response:
                raise MissingRequiredFieldError()

        # Validate summary text
        if not isinstance(response["summary"], str):
            raise InvalidTextError()

        # Validate confidence
        if not isinstance(response["confidence"], (int, float)):
            raise InvalidConfidenceError()

        if not 0.0 <= response["confidence"] <= 1.0:
            raise InvalidConfidenceError()

        # Validate source sections
        if not isinstance(response["source_sections"], list):
            raise ResponseFieldError()
