"""
JSON recovery utilities for handling malformed JSON responses.

This module provides robust JSON parsing with multiple recovery strategies
for handling common issues in LLM-generated JSON responses.

Example usage:
    >>> from hci_extractor.utils.json_recovery import recover_json
    >>>
    >>> # Basic recovery
    >>> result = recover_json('{"elements": [{"text": "incomplete')
    >>> if result.success:
    ...     print(result.recovered_data)
    >>>
    >>> # With specific options
    >>> from hci_extractor.utils.json_recovery import JsonRecoveryOptions
    >>> options = JsonRecoveryOptions(
    ...     strategies=['truncation', 'array_completion'],
    ...     expected_structure={'elements': list}
    ... )
    >>> result = recover_json(malformed_json, options)
"""

import json
import logging
import re
import types
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class JsonRecoveryStrategy(Enum):
    """Available JSON recovery strategies."""

    TRUNCATION = "truncation"
    ARRAY_COMPLETION = "array_completion"
    TRAILING_CONTENT = "trailing_content"
    QUOTE_ESCAPING = "quote_escaping"
    NUMBER_FORMAT = "number_format"

    # New enhanced recovery strategies
    FIELD_COMPLETION = "field_completion"  # Complete missing required fields
    NESTED_STRUCTURE = "nested_structure"  # Fix malformed nested objects/arrays
    UNICODE_ESCAPE = "unicode_escape"  # Handle Unicode escape issues
    MIXED_QUOTES = "mixed_quotes"  # Fix mixed single/double quote issues
    INCOMPLETE_OBJECTS = "incomplete_objects"  # Complete partially written objects
    PROVIDER_SPECIFIC = "provider_specific"  # Provider-specific recovery patterns

    ALL = "all"  # Try all strategies


@dataclass(frozen=True)
class JsonRecoveryOptions:
    """Configuration options for JSON recovery."""

    strategies: tuple[str, ...] = ("all",)
    expected_structure: Optional[Dict[str, type]] = None
    max_recovery_attempts: int = 3
    max_lookback: int = 1000  # Max chars to look back for recovery
    validate_structure: bool = True
    provider_specific: Optional[str] = None  # LLM provider name for specific patterns


@dataclass(frozen=True)
class JsonRecoveryResult:
    """Result of JSON recovery attempt."""

    success: bool
    recovered_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    strategy_used: Optional[str] = None
    original_error: Optional[json.JSONDecodeError] = None
    confidence_score: float = 0.0  # 0.0-1.0 confidence in recovery quality
    recovery_metadata: Dict[str, Any] = field(
        default_factory=lambda: types.MappingProxyType({}),
    )  # Additional recovery info


def recover_json(
    text: str,
    options: Optional[JsonRecoveryOptions] = None,
) -> JsonRecoveryResult:
    """
    Attempt to recover valid JSON from malformed text.

    Args:
        text: Potentially malformed JSON text
        options: Recovery options and configuration

    Returns:
        JsonRecoveryResult with success status and recovered data if successful
    """
    if options is None:
        options = JsonRecoveryOptions()

    # First try normal parsing
    try:
        data = json.loads(text)
        return JsonRecoveryResult(
            success=True,
            recovered_data=data,
            strategy_used="none",
            confidence_score=1.0,
            recovery_metadata={"no_recovery_needed": True},
        )
    except json.JSONDecodeError as e:
        logger.debug(f"Initial JSON parse failed: {e}")
        original_error = e

    # Determine which strategies to try
    strategies_to_try = _get_strategies_to_try(options.strategies)

    # Try each strategy
    for strategy in strategies_to_try:
        try:
            if strategy == JsonRecoveryStrategy.TRUNCATION:
                result = _try_truncation_recovery(text, original_error, options)
            elif strategy == JsonRecoveryStrategy.ARRAY_COMPLETION:
                result = _try_array_completion_recovery(text, original_error, options)
            elif strategy == JsonRecoveryStrategy.TRAILING_CONTENT:
                result = _try_trailing_content_recovery(text, options)
            elif strategy == JsonRecoveryStrategy.QUOTE_ESCAPING:
                result = _try_quote_escaping_recovery(text, options)
            elif strategy == JsonRecoveryStrategy.NUMBER_FORMAT:
                result = _try_number_format_recovery(text, options)
            elif strategy == JsonRecoveryStrategy.FIELD_COMPLETION:
                result = _try_field_completion_recovery(text, options)
            elif strategy == JsonRecoveryStrategy.NESTED_STRUCTURE:
                result = _try_nested_structure_recovery(text, options)
            elif strategy == JsonRecoveryStrategy.UNICODE_ESCAPE:
                result = _try_unicode_escape_recovery(text, options)
            elif strategy == JsonRecoveryStrategy.MIXED_QUOTES:
                result = _try_mixed_quotes_recovery(text, options)
            elif strategy == JsonRecoveryStrategy.INCOMPLETE_OBJECTS:
                result = _try_incomplete_objects_recovery(text, options)
            elif strategy == JsonRecoveryStrategy.PROVIDER_SPECIFIC:
                result = _try_provider_specific_recovery(text, options)
            else:
                continue

            if result and result.success:
                # Validate structure if requested
                if options.validate_structure and options.expected_structure:
                    if result.recovered_data and _validate_structure(
                        result.recovered_data,
                        options.expected_structure,
                    ):
                        return result
                    logger.debug(
                        f"Strategy {strategy.value} recovered JSON but "
                        "structure validation failed",
                    )
                    continue
                return result

        except Exception as e:
            logger.debug(f"Strategy {strategy.value} failed: {e}")
            continue

    # All strategies failed
    return JsonRecoveryResult(
        success=False,
        error_message=f"All recovery strategies failed. Original error: "
        f"{original_error}",
        original_error=original_error,
    )


def _get_strategies_to_try(
    requested_strategies: tuple[str, ...],
) -> List[JsonRecoveryStrategy]:
    """Convert strategy names to enum values."""
    if "all" in requested_strategies:
        return [
            JsonRecoveryStrategy.TRUNCATION,
            JsonRecoveryStrategy.ARRAY_COMPLETION,
            JsonRecoveryStrategy.TRAILING_CONTENT,
            JsonRecoveryStrategy.QUOTE_ESCAPING,
            JsonRecoveryStrategy.NUMBER_FORMAT,
            JsonRecoveryStrategy.FIELD_COMPLETION,
            JsonRecoveryStrategy.NESTED_STRUCTURE,
            JsonRecoveryStrategy.UNICODE_ESCAPE,
            JsonRecoveryStrategy.MIXED_QUOTES,
            JsonRecoveryStrategy.INCOMPLETE_OBJECTS,
            JsonRecoveryStrategy.PROVIDER_SPECIFIC,
        ]

    strategies = []
    for name in requested_strategies:
        try:
            strategies.append(JsonRecoveryStrategy(name))
        except ValueError:
            logger.warning(f"Unknown recovery strategy: {name}")

    return strategies


def _try_truncation_recovery(
    text: str,
    error: json.JSONDecodeError,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by truncating at the error position.

    Useful for unterminated strings or incomplete JSON.
    """
    error_pos = getattr(error, "pos", len(text))

    # Try to find valid JSON structures before the error
    # Look for both closing braces and closing brackets

    # Track nesting to find valid truncation points
    brace_stack = []
    bracket_stack: list[int] = []
    valid_end_positions = []
    in_string = False
    escape_next = False

    # Limit search based on max_lookback
    search_start = max(0, error_pos - options.max_lookback)

    for i in range(search_start, min(error_pos, len(text))):
        char = text[i]

        # Handle string context
        if not escape_next:
            if char == '"' and not in_string:
                in_string = True
            elif char == '"' and in_string:
                in_string = False
            elif char == "\\" and in_string:
                escape_next = True
                continue
        else:
            escape_next = False
            continue

        # Track nesting outside strings
        if not in_string:
            if char == "{":
                brace_stack.append(i)
            elif char == "}":
                if brace_stack:
                    brace_stack.pop()
                    # If all brackets and braces are balanced, this is a valid end point
                    if not brace_stack and not bracket_stack:
                        valid_end_positions.append(i)
            elif char == "[":
                bracket_stack.append(i)
            elif char == "]" and bracket_stack:
                bracket_stack.pop()

    # Filter valid positions based on max_lookback from error position
    valid_positions_in_range = [
        pos for pos in valid_end_positions if pos >= search_start
    ]

    # Try valid end positions in reverse order (most complete first)
    for end_pos in reversed(
        valid_positions_in_range[-10:],
    ):  # Try last 10 valid positions
        truncated = text[: end_pos + 1]
        try:
            data = json.loads(truncated)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="truncation",
                confidence_score=0.8,
                recovery_metadata={
                    "truncation_position": end_pos,
                    "characters_removed": len(text) - end_pos - 1,
                },
            )
        except json.JSONDecodeError:
            continue

    return None


def _try_array_completion_recovery(
    text: str,
    error: json.JSONDecodeError,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by completing an incomplete array structure.

    Specifically handles cases like {"elements": [{"text": "incomplete
    """
    # Look for common array patterns
    patterns = [
        r'\{"elements"\s*:\s*\[',
        r'\{"items"\s*:\s*\[',
        r'\{"results"\s*:\s*\[',
        r'\{"data"\s*:\s*\[',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        array_start = match.end()  # Position after '['

        # Track bracket/brace nesting WITHIN the array
        bracket_count = 0
        brace_count = 0
        last_complete_element = -1
        in_string = False
        escape_next = False

        for i in range(array_start, len(text)):
            if i >= len(text):
                break

            char = text[i]

            # Handle string context
            if not escape_next:
                if char == '"' and not in_string:
                    in_string = True
                elif char == '"' and in_string:
                    in_string = False
                elif char == "\\" and in_string:
                    escape_next = True
                    continue
            else:
                escape_next = False
                continue

            # Track nesting outside strings
            if not in_string:
                if char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                elif char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    # Check if we completed an element within the array
                    if bracket_count == 0 and brace_count == 0:
                        last_complete_element = i
                elif char == "," and bracket_count == 0 and brace_count == 0:
                    # Track commas at array level
                    pass

        # Build recovery candidates
        if last_complete_element > array_start:
            # Try to recover by including the last complete element
            recovered = text[: last_complete_element + 1] + "]}"
            try:
                data = json.loads(recovered)
                return JsonRecoveryResult(
                    success=True,
                    recovered_data=data,
                    strategy_used="array_completion",
                    confidence_score=0.7,
                    recovery_metadata={
                        "array_pattern": pattern,
                        "last_complete_element": last_complete_element,
                        "recovery_method": "complete_element_preservation",
                    },
                )
            except json.JSONDecodeError:
                pass

        # If we found at least the array opening, try closing it empty
        if match:
            recovered = text[: match.end()] + "]}"
            try:
                data = json.loads(recovered)
                return JsonRecoveryResult(
                    success=True,
                    recovered_data=data,
                    strategy_used="array_completion",
                    confidence_score=0.5,
                    recovery_metadata={
                        "array_pattern": pattern,
                        "recovery_method": "empty_array_completion",
                    },
                )
            except json.JSONDecodeError:
                pass

    return None


def _try_trailing_content_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by removing trailing non-JSON content.

    Useful when valid JSON is followed by garbage.
    """
    # Try to find where valid JSON ends
    brace_count = 0
    bracket_count = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text):
        # Handle string context
        if not escape_next:
            if char == '"' and not in_string:
                in_string = True
            elif char == '"' and in_string:
                in_string = False
            elif char == "\\" and in_string:
                escape_next = True
                continue
        else:
            escape_next = False
            continue

        # Track nesting outside strings
        if not in_string:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0 and bracket_count == 0:
                    # Found potential end of valid JSON
                    try:
                        data = json.loads(text[: i + 1])
                        return JsonRecoveryResult(
                            success=True,
                            recovered_data=data,
                            strategy_used="trailing_content",
                            confidence_score=0.85,
                            recovery_metadata={
                                "truncation_position": i + 1,
                                "trailing_chars_removed": len(text) - i - 1,
                            },
                        )
                    except json.JSONDecodeError:
                        continue
            elif char == "[":
                bracket_count += 1
            elif char == "]":
                bracket_count -= 1

    return None


def _try_quote_escaping_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by fixing unescaped quotes in strings.

    This is a heuristic approach and may not always work correctly.
    """
    # This is a simplified implementation
    # A full implementation would need more sophisticated parsing

    # Try to fix common quote issues
    # Look for patterns like: "text": "something with "quotes" inside"
    fixed_text = text

    # Simple approach: escape quotes that appear to be inside string values
    # This is very basic and would need refinement for production use
    pattern = r'("(?:[^"\\]|\\.)*"):\s*"([^"]*)"([^"]*)"([^"]*)"'

    def replace_quotes(match: Any) -> str:
        key = match.group(1)
        value_parts = [match.group(2), match.group(3), match.group(4)]
        # Escape the middle quotes
        fixed_value = f'"{value_parts[0]}"{value_parts[1]}"{value_parts[2]}"'
        return f"{key}: {fixed_value}"

    fixed_text = re.sub(pattern, replace_quotes, text)

    if fixed_text != text:
        try:
            data = json.loads(fixed_text)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="quote_escaping",
                confidence_score=0.6,
                recovery_metadata={"quote_fixes_applied": True, "text_modified": True},
            )
        except json.JSONDecodeError:
            pass

    return None


def _try_number_format_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by fixing malformed numbers.

    Handles scientific notation, infinity, NaN, etc.
    """
    fixed_text = text

    # Replace Python-style infinity/NaN with JSON null
    fixed_text = re.sub(r"\binf\b", "null", fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r"\binfinity\b", "null", fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r"\bnan\b", "null", fixed_text, flags=re.IGNORECASE)

    # Fix scientific notation issues (e.g., 1.23e+10 -> 1.23e10)
    fixed_text = re.sub(r"(\d+\.?\d*)[eE]\+(\d+)", r"\1e\2", fixed_text)

    # Fix multiple decimal points
    fixed_text = re.sub(r"(\d+)\.(\d+)\.(\d+)", r"\1.\2\3", fixed_text)

    if fixed_text != text:
        try:
            data = json.loads(fixed_text)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="number_format",
                confidence_score=0.75,
                recovery_metadata={
                    "number_fixes_applied": True,
                    "infinity_replaced": "inf" in text.lower(),
                    "nan_replaced": "nan" in text.lower(),
                },
            )
        except json.JSONDecodeError:
            pass

    return None


def _validate_structure(
    data: Dict[str, Any],
    expected_structure: Dict[str, type],
) -> bool:
    """
    Validate that recovered JSON matches expected structure.

    Args:
        data: Recovered JSON data
        expected_structure: Expected keys and their types

    Returns:
        True if structure matches expectations
    """
    if not isinstance(data, dict):
        return False

    for key, expected_type in expected_structure.items():
        if key not in data:
            return False
        if not isinstance(data[key], expected_type):
            return False

    return True


def _try_field_completion_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by completing missing required fields.

    This strategy attempts to add missing fields that are commonly required
    in extraction results, such as empty elements arrays or default values.
    """
    # Check if we have expected structure to guide completion
    if not options.expected_structure:
        return None

    # Try to parse what we have so far
    try:
        # First, try to get valid JSON by truncation
        # Try to get valid JSON by truncation - create a dummy error for the function
        import json

        try:
            json.loads(text + "}")  # This will likely fail but give us an error
        except json.JSONDecodeError as dummy_error:
            truncated_result = _try_truncation_recovery(text, dummy_error, options)
        else:
            truncated_result = None
        if (
            truncated_result
            and truncated_result.success
            and truncated_result.recovered_data
        ):
            data = truncated_result.recovered_data

            # Check which expected fields are missing and add them
            modified = False
            for field_name, field_type in options.expected_structure.items():
                if field_name not in data:
                    if field_type is list:
                        data[field_name] = []
                    elif field_type is dict:
                        data[field_name] = {}
                    elif field_type is str:
                        data[field_name] = ""
                    elif field_type is int:
                        data[field_name] = 0
                    elif field_type is float:
                        data[field_name] = 0.0
                    elif field_type is bool:
                        data[field_name] = False
                    else:
                        data[field_name] = None
                    modified = True

            if modified:
                return JsonRecoveryResult(
                    success=True,
                    recovered_data=data,
                    strategy_used="field_completion",
                    confidence_score=0.7,
                    recovery_metadata={
                        "fields_added": list(options.expected_structure.keys()),
                        "base_strategy": "truncation",
                    },
                )

    except Exception as e:
        logger.debug(f"Field completion recovery failed: {e}")

    return None


def _try_nested_structure_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by fixing malformed nested objects and arrays.

    Handles cases where nested structures are incomplete or malformed.
    """
    # Look for incomplete nested structures
    fixed_text = text

    # Fix unmatched opening brackets/braces at the end
    brace_count = 0
    bracket_count = 0
    in_string = False

    for char in text:
        if char == '"' and not in_string:
            in_string = True
        elif char == '"' and in_string:
            in_string = False
        elif not in_string:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
            elif char == "[":
                bracket_count += 1
            elif char == "]":
                bracket_count -= 1

    # Add missing closing brackets/braces
    if brace_count > 0 or bracket_count > 0:
        fixed_text = text
        fixed_text += "]" * bracket_count  # Close arrays first
        fixed_text += "}" * brace_count  # Then close objects

        try:
            data = json.loads(fixed_text)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="nested_structure",
                confidence_score=0.8,
                recovery_metadata={
                    "braces_added": brace_count,
                    "brackets_added": bracket_count,
                },
            )
        except json.JSONDecodeError:
            pass

    return None


def _try_unicode_escape_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by fixing Unicode escape sequence issues.

    Handles malformed Unicode escapes and encoding issues.
    """
    fixed_text = text

    # Fix common Unicode escape issues
    # Replace malformed Unicode escapes with safe alternatives
    fixed_text = re.sub(
        r"\\u(?![0-9a-fA-F]{4})",
        r"\\u0020",
        fixed_text,
    )  # Replace incomplete escapes
    fixed_text = re.sub(
        r"\\x([0-9a-fA-F]{2})",
        r"\\u00\1",
        fixed_text,
    )  # Convert hex escapes

    # Fix common encoding issues
    fixed_text = (
        fixed_text.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
    )

    # Remove or fix invalid control characters
    fixed_text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", fixed_text)

    if fixed_text != text:
        try:
            data = json.loads(fixed_text)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="unicode_escape",
                confidence_score=0.6,
                recovery_metadata={
                    "unicode_fixes_applied": True,
                    "original_length": len(text),
                    "fixed_length": len(fixed_text),
                },
            )
        except json.JSONDecodeError:
            pass

    return None


def _try_mixed_quotes_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by fixing mixed single/double quote issues.

    More sophisticated than the basic quote_escaping strategy.
    """
    fixed_text = text

    # Replace single quotes with double quotes, but be careful about apostrophes
    # This is a heuristic approach - match patterns that look like JSON keys/values

    # Replace single quotes around what looks like keys
    fixed_text = re.sub(r"'([a-zA-Z_][a-zA-Z0-9_]*)'\s*:", r'"\1":', fixed_text)

    # Replace single quotes around string values (but not containing apostrophes)
    fixed_text = re.sub(r":\s*'([^']*)'(?=\s*[,}\]])", r': "\1"', fixed_text)

    # Handle arrays with single-quoted strings
    fixed_text = re.sub(r"\[\s*'([^']*)'(?=\s*[,\]])", r'["\1"', fixed_text)
    fixed_text = re.sub(r",\s*'([^']*)'(?=\s*[,\]])", r', "\1"', fixed_text)

    if fixed_text != text:
        try:
            data = json.loads(fixed_text)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="mixed_quotes",
                confidence_score=0.75,
                recovery_metadata={
                    "quote_fixes_applied": True,
                    "original_has_single_quotes": "'" in text,
                },
            )
        except json.JSONDecodeError:
            pass

    return None


def _try_incomplete_objects_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by completing partially written objects.

    Handles cases where objects are incomplete mid-field.
    """
    # Look for incomplete field declarations
    patterns = [
        # Incomplete string field: "field_name": "incomplete_value
        (r'"([^"]+)"\s*:\s*"([^"]*?)$', r'"\1": "\2"'),
        # Incomplete number field: "field_name": 123.
        (r'"([^"]+)"\s*:\s*(\d+\.)$', r'"\1": \20'),
        # Incomplete array field: "field_name": [
        (r'"([^"]+)"\s*:\s*\[$', r'"\1": []'),
        # Incomplete object field: "field_name": {
        (r'"([^"]+)"\s*:\s*\{$', r'"\1": {}'),
        # Incomplete boolean: "field_name": tru
        (r'"([^"]+)"\s*:\s*tru$', r'"\1": true'),
        (r'"([^"]+)"\s*:\s*fals$', r'"\1": false'),
        # Incomplete null: "field_name": nul
        (r'"([^"]+)"\s*:\s*nul$', r'"\1": null'),
    ]

    fixed_text = text
    modifications = []

    for pattern, replacement in patterns:
        if re.search(pattern, fixed_text):
            fixed_text = re.sub(pattern, replacement, fixed_text)
            modifications.append(pattern)

    # Try to close any unclosed braces/brackets
    if modifications:
        # Count unclosed structures
        brace_count = bracket_count = 0
        in_string = False

        for char in fixed_text:
            if char == '"' and not in_string:
                in_string = True
            elif char == '"' and in_string:
                in_string = False
            elif not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                elif char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1

        # Close unclosed structures
        if brace_count > 0 or bracket_count > 0:
            fixed_text += "]" * bracket_count + "}" * brace_count

        try:
            data = json.loads(fixed_text)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="incomplete_objects",
                confidence_score=0.65,
                recovery_metadata={
                    "patterns_matched": len(modifications),
                    "modifications": modifications,
                    "structures_closed": brace_count + bracket_count > 0,
                },
            )
        except json.JSONDecodeError:
            pass

    return None


def _try_provider_specific_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover using provider-specific patterns.

    Different LLM providers have different common failure patterns.
    """
    if not options.provider_specific:
        return None

    provider = options.provider_specific.lower()

    if provider == "gemini":
        return _try_gemini_specific_recovery(text, options)
    if provider == "openai":
        return _try_openai_specific_recovery(text, options)
    if provider == "anthropic":
        return _try_anthropic_specific_recovery(text, options)

    return None


def _try_gemini_specific_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Gemini-specific recovery patterns.

    Gemini sometimes generates responses with specific formatting issues.
    """
    fixed_text = text

    # Gemini sometimes adds markdown code blocks
    if "```json" in fixed_text:
        # Extract JSON from markdown code block
        match = re.search(r"```json\s*(.+?)```", fixed_text, re.DOTALL)
        if match:
            fixed_text = match.group(1).strip()

    # Gemini sometimes adds explanatory text after JSON
    if "}" in fixed_text:
        # Find the last complete JSON object
        last_brace = fixed_text.rfind("}")
        if last_brace != -1:
            candidate = fixed_text[: last_brace + 1]
            try:
                data = json.loads(candidate)
                return JsonRecoveryResult(
                    success=True,
                    recovered_data=data,
                    strategy_used="provider_specific",
                    confidence_score=0.8,
                    recovery_metadata={
                        "provider": "gemini",
                        "recovery_method": "trailing_text_removal",
                    },
                )
            except json.JSONDecodeError:
                pass

    return None


def _try_openai_specific_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    OpenAI-specific recovery patterns.

    OpenAI models sometimes have specific formatting quirks.
    """
    fixed_text = text

    # OpenAI sometimes generates trailing commas in JSON
    fixed_text = re.sub(r",\s*}", "}", fixed_text)
    fixed_text = re.sub(r",\s*]", "]", fixed_text)

    # OpenAI sometimes uses JavaScript-style comments
    fixed_text = re.sub(r"//[^\n]*\n", "\n", fixed_text)
    fixed_text = re.sub(r"/\*.*?\*/", "", fixed_text, flags=re.DOTALL)

    if fixed_text != text:
        try:
            data = json.loads(fixed_text)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="provider_specific",
                confidence_score=0.8,
                recovery_metadata={
                    "provider": "openai",
                    "recovery_method": "trailing_comma_removal",
                },
            )
        except json.JSONDecodeError:
            pass

    return None


def _try_anthropic_specific_recovery(
    text: str,
    options: JsonRecoveryOptions,
) -> Optional[JsonRecoveryResult]:
    """
    Anthropic-specific recovery patterns.

    Anthropic models may have their own specific formatting patterns.
    """
    fixed_text = text

    # Anthropic sometimes adds thinking text before JSON
    if "{" in fixed_text:
        # Find the first JSON object
        first_brace = fixed_text.find("{")
        if first_brace > 0:
            candidate = fixed_text[first_brace:]
            try:
                data = json.loads(candidate)
                return JsonRecoveryResult(
                    success=True,
                    recovered_data=data,
                    strategy_used="provider_specific",
                    confidence_score=0.8,
                    recovery_metadata={
                        "provider": "anthropic",
                        "recovery_method": "leading_text_removal",
                    },
                )
            except json.JSONDecodeError:
                pass

    return None
