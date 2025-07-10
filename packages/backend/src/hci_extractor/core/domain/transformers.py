"""Domain transformers for HCI extractor - pure data transformation logic."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from hci_extractor.core.domain.validators import ElementValidator, SummaryValidator
from hci_extractor.core.models import LLMValidationError
from hci_extractor.utils import JsonRecoveryOptions, recover_json

logger = logging.getLogger(__name__)


class ElementTransformer:
    """Transforms and cleans extracted elements according to domain rules."""

    # Optional fields that may be present in elements
    OPTIONAL_FIELDS = frozenset(
        [
            "supporting_evidence",
            "methodology_context",
            "study_population",
            "limitations",
            "surrounding_context",
        ],
    )

    @classmethod
    def transform_element(cls, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a single element to clean format.

        Args:
            element: Raw element from LLM response

        Returns:
            Cleaned element dict or None if should be skipped
        """
        # Create base cleaned element with required fields
        cleaned = {
            "element_type": element["element_type"],
            "text": element["text"].strip(),
            "evidence_type": element["evidence_type"],
            "confidence": float(element["confidence"]),
        }

        # Add optional fields if present and non-empty
        for field in cls.OPTIONAL_FIELDS:
            if element.get(field):
                value = (
                    element[field].strip()
                    if isinstance(element[field], str)
                    else element[field]
                )
                if value:
                    cleaned[field] = value

        # Check if element should be included
        if not ElementValidator.is_valid_element_for_inclusion(cleaned):
            logger.debug(f"Skipping short extraction: {cleaned['text']}")
            return None

        return cleaned

    @classmethod
    def transform_elements(
        cls,
        elements: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], ...]:
        """
        Transform a list of elements to immutable tuple of cleaned elements.

        Args:
            elements: List of raw elements from LLM

        Returns:
            Immutable tuple of cleaned elements
        """
        # Use generator expression for immutable transformation
        return tuple(
            cleaned_element
            for element in elements
            if (cleaned_element := cls.transform_element(element)) is not None
        )

    @classmethod
    def transform_summary(cls, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform summary response to clean format.

        Args:
            response: Raw summary response

        Returns:
            Cleaned summary dict
        """
        return {
            "summary": response["summary"].strip(),
            "confidence": float(response["confidence"]),
            "source_sections": tuple(response["source_sections"]),  # Make immutable
        }


class ResponseParser:
    """Parses LLM responses with error recovery."""

    @classmethod
    def parse_json_response(
        cls,
        response_text: str,
        expected_structure: Optional[Dict[str, type]] = None,
    ) -> Dict[str, Any]:
        """
        Parse JSON response with automatic error recovery.

        Args:
            response_text: Raw text response from LLM
            expected_structure: Expected JSON structure for recovery

        Returns:
            Parsed JSON as dictionary

        Raises:
            LLMValidationError: If parsing fails after recovery attempts
        """
        try:
            result = json.loads(response_text)
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError as e:
            # Try to recover from common JSON issues
            recovery_options = JsonRecoveryOptions(
                strategies=["truncation", "array_completion"],
                expected_structure=expected_structure or {"elements": list},
            )
            recovery_result = recover_json(response_text, recovery_options)

            if recovery_result.success and recovery_result.recovered_data:
                logger.warning(
                    f"Recovered from JSON error using "
                    f"{recovery_result.strategy_used}: {e}",
                )
                return recovery_result.recovered_data
            raise LLMValidationError(f"Invalid JSON response: {e}")

    @classmethod
    def parse_analysis_response(cls, response_text: str) -> Dict[str, Any]:
        """
        Parse section analysis response.

        Args:
            response_text: Raw response text

        Returns:
            Parsed and validated response
        """
        response_data = cls.parse_json_response(
            response_text,
            expected_structure={"elements": list},
        )

        # Validate before returning
        ElementValidator.validate_response(response_data)

        return response_data

    @classmethod
    def parse_summary_response(cls, response_text: str) -> Dict[str, Any]:
        """
        Parse paper summary response.

        Args:
            response_text: Raw response text

        Returns:
            Parsed and validated response
        """
        response_data = cls.parse_json_response(
            response_text,
            expected_structure={
                "summary": str,
                "confidence": float,
                "source_sections": list,
            },
        )

        # Validate before returning
        SummaryValidator.validate_summary(response_data)

        return response_data
