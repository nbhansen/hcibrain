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
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class JsonRecoveryStrategy(Enum):
    """Available JSON recovery strategies."""
    
    TRUNCATION = "truncation"
    ARRAY_COMPLETION = "array_completion"
    TRAILING_CONTENT = "trailing_content"
    QUOTE_ESCAPING = "quote_escaping"
    NUMBER_FORMAT = "number_format"
    ALL = "all"  # Try all strategies


@dataclass(frozen=True)
class JsonRecoveryOptions:
    """Configuration options for JSON recovery."""
    
    strategies: List[str] = field(default_factory=lambda: ["all"])
    expected_structure: Optional[Dict[str, type]] = None
    max_recovery_attempts: int = 3
    max_lookback: int = 1000  # Max chars to look back for recovery
    validate_structure: bool = True


@dataclass(frozen=True)
class JsonRecoveryResult:
    """Result of JSON recovery attempt."""
    
    success: bool
    recovered_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    strategy_used: Optional[str] = None
    original_error: Optional[json.JSONDecodeError] = None


def recover_json(
    text: str, 
    options: Optional[JsonRecoveryOptions] = None
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
            strategy_used="none"
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
            else:
                continue
            
            if result and result.success:
                # Validate structure if requested
                if options.validate_structure and options.expected_structure:
                    if _validate_structure(result.recovered_data, options.expected_structure):
                        return result
                    else:
                        logger.debug(f"Strategy {strategy.value} recovered JSON but structure validation failed")
                        continue
                else:
                    return result
                    
        except Exception as e:
            logger.debug(f"Strategy {strategy.value} failed: {e}")
            continue
    
    # All strategies failed
    return JsonRecoveryResult(
        success=False,
        error_message=f"All recovery strategies failed. Original error: {original_error}",
        original_error=original_error
    )


def _get_strategies_to_try(requested_strategies: List[str]) -> List[JsonRecoveryStrategy]:
    """Convert strategy names to enum values."""
    if "all" in requested_strategies:
        return [
            JsonRecoveryStrategy.TRUNCATION,
            JsonRecoveryStrategy.ARRAY_COMPLETION,
            JsonRecoveryStrategy.TRAILING_CONTENT,
            JsonRecoveryStrategy.QUOTE_ESCAPING,
            JsonRecoveryStrategy.NUMBER_FORMAT
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
    options: JsonRecoveryOptions
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by truncating at the error position.
    
    Useful for unterminated strings or incomplete JSON.
    """
    error_pos = getattr(error, 'pos', len(text))
    
    # Try to find valid JSON structures before the error
    # Look for both closing braces and closing brackets
    
    # Track nesting to find valid truncation points
    brace_stack = []
    bracket_stack = []
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
            elif char == '\\' and in_string:
                escape_next = True
                continue
        else:
            escape_next = False
            continue
        
        # Track nesting outside strings
        if not in_string:
            if char == '{':
                brace_stack.append(i)
            elif char == '}':
                if brace_stack:
                    brace_stack.pop()
                    # If all brackets and braces are balanced, this is a valid end point
                    if not brace_stack and not bracket_stack:
                        valid_end_positions.append(i)
            elif char == '[':
                bracket_stack.append(i)
            elif char == ']':
                if bracket_stack:
                    bracket_stack.pop()
    
    # Filter valid positions based on max_lookback from error position
    valid_positions_in_range = [
        pos for pos in valid_end_positions 
        if pos >= search_start
    ]
    
    # Try valid end positions in reverse order (most complete first)
    for end_pos in reversed(valid_positions_in_range[-10:]):  # Try last 10 valid positions
        truncated = text[:end_pos + 1]
        try:
            data = json.loads(truncated)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="truncation"
            )
        except json.JSONDecodeError:
            continue
    
    return None


def _try_array_completion_recovery(
    text: str,
    error: json.JSONDecodeError,
    options: JsonRecoveryOptions
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
        r'\{"data"\s*:\s*\['
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
        last_array_comma = -1
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
                elif char == '\\' and in_string:
                    escape_next = True
                    continue
            else:
                escape_next = False
                continue
            
            # Track nesting outside strings
            if not in_string:
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                elif char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    # Check if we completed an element within the array
                    if bracket_count == 0 and brace_count == 0:
                        last_complete_element = i
                elif char == ',' and bracket_count == 0 and brace_count == 0:
                    # Track commas at array level
                    last_array_comma = i
        
        # Build recovery candidates
        if last_complete_element > array_start:
            # Try to recover by including the last complete element
            recovered = text[:last_complete_element + 1] + ']}'  
            try:
                data = json.loads(recovered)
                return JsonRecoveryResult(
                    success=True,
                    recovered_data=data,
                    strategy_used="array_completion"
                )
            except json.JSONDecodeError:
                pass
        
        # If we found at least the array opening, try closing it empty
        if match:
            recovered = text[:match.end()] + ']}'  
            try:
                data = json.loads(recovered)
                return JsonRecoveryResult(
                    success=True,
                    recovered_data=data,
                    strategy_used="array_completion"
                )
            except json.JSONDecodeError:
                pass
    
    return None


def _try_trailing_content_recovery(
    text: str,
    options: JsonRecoveryOptions
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
            elif char == '\\' and in_string:
                escape_next = True
                continue
        else:
            escape_next = False
            continue
        
        # Track nesting outside strings
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and bracket_count == 0:
                    # Found potential end of valid JSON
                    try:
                        data = json.loads(text[:i + 1])
                        return JsonRecoveryResult(
                            success=True,
                            recovered_data=data,
                            strategy_used="trailing_content"
                        )
                    except json.JSONDecodeError:
                        continue
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
    
    return None


def _try_quote_escaping_recovery(
    text: str,
    options: JsonRecoveryOptions
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
    
    def replace_quotes(match):
        key = match.group(1)
        value_parts = [match.group(2), match.group(3), match.group(4)]
        # Escape the middle quotes
        fixed_value = f'"{value_parts[0]}\"{value_parts[1]}\"{value_parts[2]}"'
        return f'{key}: {fixed_value}'
    
    fixed_text = re.sub(pattern, replace_quotes, text)
    
    if fixed_text != text:
        try:
            data = json.loads(fixed_text)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="quote_escaping"
            )
        except json.JSONDecodeError:
            pass
    
    return None


def _try_number_format_recovery(
    text: str,
    options: JsonRecoveryOptions
) -> Optional[JsonRecoveryResult]:
    """
    Try to recover by fixing malformed numbers.
    
    Handles scientific notation, infinity, NaN, etc.
    """
    fixed_text = text
    
    # Replace Python-style infinity/NaN with JSON null
    fixed_text = re.sub(r'\binf\b', 'null', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\binfinity\b', 'null', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\bnan\b', 'null', fixed_text, flags=re.IGNORECASE)
    
    # Fix scientific notation issues (e.g., 1.23e+10 -> 1.23e10)
    fixed_text = re.sub(r'(\d+\.?\d*)[eE]\+(\d+)', r'\1e\2', fixed_text)
    
    # Fix multiple decimal points
    fixed_text = re.sub(r'(\d+)\.(\d+)\.(\d+)', r'\1.\2\3', fixed_text)
    
    if fixed_text != text:
        try:
            data = json.loads(fixed_text)
            return JsonRecoveryResult(
                success=True,
                recovered_data=data,
                strategy_used="number_format"
            )
        except json.JSONDecodeError:
            pass
    
    return None


def _validate_structure(
    data: Dict[str, Any],
    expected_structure: Dict[str, type]
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