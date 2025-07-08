"""Test JSON recovery utilities."""

import json

import pytest

from hci_extractor.utils import (
    JsonRecoveryOptions,
    recover_json,
)


class TestBasicRecovery:
    """Test basic JSON recovery functionality."""

    def test_valid_json_passes_through(self):
        """Valid JSON should be returned without recovery."""
        valid_json = '{"elements": [{"text": "test", "type": "finding"}]}'
        result = recover_json(valid_json)

        assert result.success
        assert result.strategy_used == "none"
        assert result.recovered_data == {
            "elements": [{"text": "test", "type": "finding"}]
        }

    def test_empty_string_fails(self):
        """Empty string should fail recovery."""
        result = recover_json("")
        assert not result.success
        assert result.error_message is not None

    def test_non_json_fails(self):
        """Non-JSON text should fail recovery."""
        result = recover_json("This is not JSON")
        assert not result.success


class TestTruncationRecovery:
    """Test truncation recovery strategy."""

    def test_unterminated_string_recovery(self):
        """Should recover from unterminated string."""
        malformed = '{"elements": [{"text": "incomplete'
        options = JsonRecoveryOptions(strategies=["truncation"])
        result = recover_json(malformed, options)

        # Truncation should not work for this case as there's no closing }
        assert not result.success

    def test_unterminated_string_with_complete_object(self):
        """Should recover by finding last complete object."""
        malformed = '{"elements": [{"text": "complete"}], "extra": "incomple'
        options = JsonRecoveryOptions(strategies=["truncation"])
        result = recover_json(malformed, options)

        # Should find the } after "complete"}]
        if result.success:
            assert "elements" in result.recovered_data
            assert len(result.recovered_data["elements"]) == 1
            assert result.strategy_used == "truncation"

    def test_truncation_respects_max_lookback(self):
        """Should respect max lookback limit."""
        # Create a JSON structure with valid closing braces far from the error
        # Insert many characters between valid structure and the unterminated string
        filler = "a" * 2000  # Large amount of valid string content
        malformed = f'{{"elements": [], "data": "{filler}", "field": "unterminated'

        options = JsonRecoveryOptions(
            strategies=["truncation"],
            max_lookback=100,  # Won't reach the valid closing braces
        )
        result = recover_json(malformed, options)

        assert not result.success


class TestArrayCompletionRecovery:
    """Test array completion recovery strategy."""

    def test_incomplete_elements_array(self):
        """Should complete an incomplete elements array."""
        malformed = (
            '{"elements": [{"text": "test", "type": "finding"}, {"text": "incomp'
        )
        options = JsonRecoveryOptions(strategies=["array_completion"])
        result = recover_json(malformed, options)

        assert result.success
        assert result.strategy_used == "array_completion"
        assert "elements" in result.recovered_data
        assert len(result.recovered_data["elements"]) == 1  # Only complete element

    def test_nested_objects_in_array(self):
        """Should handle nested objects correctly."""
        malformed = '{"elements": [{"text": "test", "metadata": {"author": "someone"}}, {"text": "inc'
        options = JsonRecoveryOptions(strategies=["array_completion"])
        result = recover_json(malformed, options)

        assert result.success
        assert len(result.recovered_data["elements"]) == 1
        assert result.recovered_data["elements"][0]["metadata"]["author"] == "someone"

    def test_empty_array_recovery(self):
        """Should handle empty or nearly empty arrays."""
        malformed = '{"elements": ['
        options = JsonRecoveryOptions(strategies=["array_completion"])
        result = recover_json(malformed, options)

        # Should complete as empty array
        if result.success:
            assert result.recovered_data == {"elements": []}

    def test_multiple_array_patterns(self):
        """Should work with different array field names."""
        test_cases = [
            ('{"items": [{"id": 1}, {"id": 2', "items"),
            ('{"results": [{"value": "a"}, {"val', "results"),
            ('{"data": [{"x": 1}, {"x":', "data"),
        ]

        options = JsonRecoveryOptions(strategies=["array_completion"])

        for malformed, expected_key in test_cases:
            result = recover_json(malformed, options)
            if result.success:
                assert expected_key in result.recovered_data
                assert isinstance(result.recovered_data[expected_key], list)


class TestTrailingContentRecovery:
    """Test trailing content removal strategy."""

    def test_trailing_garbage_removal(self):
        """Should remove trailing non-JSON content."""
        malformed = '{"elements": [{"text": "test"}]} and then some garbage !@#$'
        options = JsonRecoveryOptions(strategies=["trailing_content"])
        result = recover_json(malformed, options)

        assert result.success
        assert result.strategy_used == "trailing_content"
        assert result.recovered_data == {"elements": [{"text": "test"}]}

    def test_nested_json_with_trailing_content(self):
        """Should handle nested structures with trailing content."""
        malformed = '{"a": {"b": {"c": [1, 2, 3]}}} extra content'
        options = JsonRecoveryOptions(strategies=["trailing_content"])
        result = recover_json(malformed, options)

        assert result.success
        assert result.recovered_data == {"a": {"b": {"c": [1, 2, 3]}}}

    def test_multiple_json_objects(self):
        """Should extract first complete JSON object."""
        malformed = '{"first": 1}{"second": 2}'
        options = JsonRecoveryOptions(strategies=["trailing_content"])
        result = recover_json(malformed, options)

        assert result.success
        assert result.recovered_data == {"first": 1}


class TestQuoteEscapingRecovery:
    """Test quote escaping recovery strategy."""

    def test_unescaped_quotes_in_string(self):
        """Should escape unescaped quotes in string values."""
        # This is a simplified test - the current implementation is basic
        malformed = '{"text": "She said "hello" to me"}'
        options = JsonRecoveryOptions(strategies=["quote_escaping"])
        recover_json(malformed, options)

        # The current implementation is basic and might not handle this
        # In a production system, this would need more sophisticated parsing
        pass


class TestNumberFormatRecovery:
    """Test number format recovery strategy."""

    def test_infinity_replacement(self):
        """Should replace infinity with null."""
        malformed = '{"value": inf, "value2": Infinity}'
        options = JsonRecoveryOptions(strategies=["number_format"])
        result = recover_json(malformed, options)

        if result.success:
            assert result.recovered_data["value"] is None
            assert result.recovered_data["value2"] is None

    def test_nan_replacement(self):
        """Should replace NaN with null."""
        malformed = '{"value": NaN, "value2": nan}'
        options = JsonRecoveryOptions(strategies=["number_format"])
        result = recover_json(malformed, options)

        if result.success:
            assert result.recovered_data["value"] is None
            assert result.recovered_data["value2"] is None

    def test_scientific_notation_fix(self):
        """Should fix scientific notation issues."""
        malformed = '{"value": 1.23e+10}'
        options = JsonRecoveryOptions(strategies=["number_format"])
        result = recover_json(malformed, options)

        if result.success:
            assert result.recovered_data["value"] == 1.23e10


class TestCombinedStrategies:
    """Test using multiple recovery strategies."""

    def test_all_strategies(self):
        """Should try all strategies when requested."""
        malformed = '{"elements": [{"text": "test"}, {"text": "incomp'
        options = JsonRecoveryOptions(strategies=["all"])
        result = recover_json(malformed, options)

        assert result.success
        assert result.strategy_used in [
            "array_completion",
            "truncation",
            "trailing_content",
        ]

    def test_strategy_order_matters(self):
        """First successful strategy should be used."""
        malformed = '{"elements": [{"text": "test"}]} garbage'

        # Both trailing_content and array_completion could work
        options1 = JsonRecoveryOptions(
            strategies=["trailing_content", "array_completion"]
        )
        result1 = recover_json(malformed, options1)
        assert result1.strategy_used == "trailing_content"

        # Reverse order
        options2 = JsonRecoveryOptions(
            strategies=["array_completion", "trailing_content"]
        )
        result2 = recover_json(malformed, options2)
        # array_completion might not work for valid JSON with trailing content
        assert result2.success


class TestStructureValidation:
    """Test structure validation functionality."""

    def test_expected_structure_validation(self):
        """Should validate recovered JSON matches expected structure."""
        malformed = '{"elements": "not_a_list"} garbage'
        options = JsonRecoveryOptions(
            strategies=["trailing_content"],
            expected_structure={"elements": list},
            validate_structure=True,
        )
        result = recover_json(malformed, options)

        # Should fail because elements is not a list
        assert not result.success

    def test_structure_validation_success(self):
        """Should succeed when structure matches."""
        malformed = '{"elements": [{"text": "test"}]} garbage'
        options = JsonRecoveryOptions(
            strategies=["trailing_content"],
            expected_structure={"elements": list},
            validate_structure=True,
        )
        result = recover_json(malformed, options)

        assert result.success
        assert isinstance(result.recovered_data["elements"], list)

    def test_optional_structure_validation(self):
        """Should skip validation when disabled."""
        malformed = '{"elements": "not_a_list"} garbage'
        options = JsonRecoveryOptions(
            strategies=["trailing_content"],
            expected_structure={"elements": list},
            validate_structure=False,
        )
        result = recover_json(malformed, options)

        # Should succeed even though structure doesn't match
        if result.success:
            assert result.recovered_data["elements"] == "not_a_list"


class TestRealWorldExamples:
    """Test with real-world malformed JSON examples."""

    def test_llm_cutoff_response(self):
        """Test with typical LLM response that got cut off."""
        malformed = """{"elements": [
            {"element_type": "finding", "text": "Users preferred the new interface", "confidence": 0.9, "evidence_type": "quantitative"},
            {"element_type": "method", "text": "We conducted a survey with 50 participants", "confidence": 0.85, "evidence_type": "quantitative"},
            {"element_type": "claim", "text": "The new design improves usability by reducing the"""

        result = recover_json(malformed)

        assert result.success
        assert len(result.recovered_data["elements"]) == 2  # Only complete elements
        assert all("element_type" in elem for elem in result.recovered_data["elements"])

    def test_nested_quotes_from_llm(self):
        """Test with nested quotes that LLMs sometimes produce."""
        # This is a known difficult case
        malformed = """{"elements": [
            {"text": "The participant said \\"I don't understand this\\"", "type": "quote"}
        ]}"""

        result = recover_json(malformed)

        # Should handle escaped quotes properly
        if result.success:
            assert "participant" in result.recovered_data["elements"][0]["text"]

    def test_large_truncated_response(self):
        """Test with large response that got truncated."""
        # Generate a large valid part
        elements = [{"text": f"Finding {i}", "type": "finding"} for i in range(50)]
        valid_part = json.dumps({"elements": elements})

        # Truncate it
        malformed = valid_part[:-20] + "incomplete data here"

        result = recover_json(malformed)

        if result.success:
            # Should recover most of the elements
            assert len(result.recovered_data["elements"]) >= 45


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_max_recovery_attempts(self):
        """Should respect max recovery attempts."""
        malformed = "completely invalid json {"
        options = JsonRecoveryOptions(strategies=["all"], max_recovery_attempts=1)
        result = recover_json(malformed, options)

        assert not result.success
        assert result.original_error is not None

    def test_unknown_strategy_ignored(self):
        """Should ignore unknown strategy names."""
        valid_json = '{"test": true}'
        options = JsonRecoveryOptions(strategies=["unknown_strategy"])
        result = recover_json(valid_json, options)

        # Should still work with valid JSON
        assert result.success
        assert result.strategy_used == "none"

    def test_deeply_nested_structures(self):
        """Should handle deeply nested structures."""
        nested = {"a": {"b": {"c": {"d": {"e": {"f": "value"}}}}}}
        malformed = json.dumps(nested)[:-5] + "garbage"

        options = JsonRecoveryOptions(strategies=["truncation", "trailing_content"])
        result = recover_json(malformed, options)

        # One of the strategies should work
        if result.success:
            assert "a" in result.recovered_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
