"""Text normalization with reversible transformations for academic content."""

import re
from typing import List, Tuple

from hci_extractor.core.models import TextTransformation


class TextNormalizer:
    """Clean PDF text while maintaining verbatim validation capability."""

    def __init__(self):
        """Initialize with academic-aware cleaning rules."""
        # Patterns to preserve during cleaning
        self.citation_patterns = [
            r"\[[0-9,\s-]+\]",  # [1, 2, 3] or [1-5]
            r"\([^)]*et al\.[^)]*\)",  # (Smith et al., 2023)
            r"\([^)]*[0-9]{4}[^)]*\)",  # (Author, 2023)
        ]

        # Mathematical notation to preserve
        self.math_patterns = [
            r"[α-ωΑ-Ω]",  # Greek letters
            r"[≤≥≠≈±∑∏∫∂∇]",  # Math symbols
            r"[₀₁₂₃₄₅₆₇₈₉]",  # Subscripts
            r"[⁰¹²³⁴⁵⁶⁷⁸⁹]",  # Superscripts
        ]

    def normalize(self, raw_text: str) -> TextTransformation:
        """Apply cleaning transformations while maintaining verbatim traceability."""
        if not raw_text:
            return TextTransformation(
                original_text=raw_text,
                cleaned_text=raw_text,
                transformations=(),
                char_mapping={},
            )

        transformations = []
        char_mapping = {}
        current_text = raw_text

        # Track original positions through transformations
        position_map = list(range(len(raw_text)))

        # 1. Fix hyphenated words
        current_text, position_map = self._fix_hyphenation(
            current_text, position_map, transformations
        )

        # 2. Normalize whitespace
        current_text, position_map = self._normalize_whitespace(
            current_text, position_map, transformations
        )

        # 3. Remove headers/footers (conservative approach)
        current_text, position_map = self._remove_headers_footers(
            current_text, position_map, transformations
        )

        # Build final character mapping
        for i, orig_pos in enumerate(position_map):
            if orig_pos != -1:  # -1 indicates deleted character
                char_mapping[i] = orig_pos

        return TextTransformation(
            original_text=raw_text,
            cleaned_text=current_text,
            transformations=tuple(transformations),
            char_mapping=char_mapping,
        )

    def _fix_hyphenation(
        self, text: str, position_map: List[int], transformations: List[str]
    ) -> Tuple[str, List[int]]:
        """Fix hyphenated words split across lines."""
        # Pattern: word- \n word -> word word
        pattern = r"(\w+)-\s*\n\s*(\w+)"

        def replace_hyphen(match):
            return f"{match.group(1)}{match.group(2)}"

        new_text = ""
        new_position_map = []
        last_end = 0

        for match in re.finditer(pattern, text):
            # Add text before match
            new_text += text[last_end : match.start()]
            new_position_map.extend(position_map[last_end : match.start()])

            # Add the dehyphenated word
            replacement = replace_hyphen(match)
            new_text += replacement

            # Map positions for the replacement
            # Keep positions for first word, skip hyphen/whitespace/newline,
            # continue with second word
            word1_end = match.start() + len(match.group(1))
            word2_start = match.end() - len(match.group(2))

            # Add positions for first word
            new_position_map.extend(position_map[match.start() : word1_end])
            # Add positions for second word
            new_position_map.extend(position_map[word2_start : match.end()])

            last_end = match.end()

        # Add remaining text
        new_text += text[last_end:]
        new_position_map.extend(position_map[last_end:])

        if len(new_text) != len(text):
            transformations.append("fix_hyphenation")

        return new_text, new_position_map

    def _normalize_whitespace(
        self, text: str, position_map: List[int], transformations: List[str]
    ) -> Tuple[str, List[int]]:
        """Normalize excessive whitespace while preserving structure."""
        # Replace multiple spaces with single space
        # But preserve paragraph breaks (double newlines)

        # First preserve important whitespace patterns
        protected_ranges = []

        # Protect citations and math
        all_patterns = self.citation_patterns + self.math_patterns
        for pattern in all_patterns:
            for match in re.finditer(pattern, text):
                protected_ranges.append((match.start(), match.end()))

        # Sort and merge overlapping ranges
        protected_ranges.sort()
        merged_ranges = []
        for start, end in protected_ranges:
            if merged_ranges and start <= merged_ranges[-1][1]:
                merged_ranges[-1] = (
                    merged_ranges[-1][0],
                    max(merged_ranges[-1][1], end),
                )
            else:
                merged_ranges.append((start, end))

        new_text = ""
        new_position_map = []
        last_pos = 0

        # Process text between protected ranges
        for start, end in merged_ranges + [(len(text), len(text))]:
            if last_pos < start:
                # Normalize whitespace in unprotected section
                section = text[last_pos:start]
                section_positions = position_map[last_pos:start]

                normalized_section, normalized_positions = (
                    self._normalize_section_whitespace(section, section_positions)
                )

                new_text += normalized_section
                new_position_map.extend(normalized_positions)

            if start < len(text):
                # Add protected section as-is
                new_text += text[start:end]
                new_position_map.extend(position_map[start:end])
                last_pos = end

        if len(new_text) != len(text):
            transformations.append("normalize_whitespace")

        return new_text, new_position_map

    def _normalize_section_whitespace(
        self, section: str, positions: List[int]
    ) -> Tuple[str, List[int]]:
        """Normalize whitespace in a text section."""
        # Multiple spaces -> single space
        # Multiple newlines -> preserve paragraph breaks

        result = ""
        result_positions = []
        i = 0

        while i < len(section):
            char = section[i]

            if char == " ":
                # Collapse multiple spaces
                result += " "
                result_positions.append(positions[i])
                # Skip additional spaces
                while i + 1 < len(section) and section[i + 1] == " ":
                    i += 1
            elif char == "\n":
                # Handle newlines - preserve double newlines (paragraph breaks)
                newline_count = 0
                start_i = i
                while i < len(section) and section[i] == "\n":
                    newline_count += 1
                    i += 1

                if newline_count >= 2:
                    # Preserve paragraph break
                    result += "\n\n"
                    result_positions.extend([positions[start_i], positions[start_i]])
                else:
                    # Single newline -> space
                    result += " "
                    result_positions.append(positions[start_i])

                i -= 1  # Adjust for loop increment
            else:
                result += char
                result_positions.append(positions[i])

            i += 1

        return result, result_positions

    def _remove_headers_footers(
        self, text: str, position_map: List[int], transformations: List[str]
    ) -> Tuple[str, List[int]]:
        """Conservatively remove repetitive headers and footers."""
        lines = text.split("\n")
        line_positions = []

        # Build line position mapping
        current_pos = 0
        for line in lines:
            line_start = current_pos
            line_end = current_pos + len(line)
            line_positions.append((line_start, line_end))
            current_pos = line_end + 1  # +1 for newline

        # Identify potential headers/footers (conservative approach)
        # Look for lines that appear multiple times and are short
        line_counts = {}
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) < 100:  # Only consider short lines
                line_counts[stripped] = line_counts.get(stripped, 0) + 1

        # Find lines that appear 3+ times (likely headers/footers)
        repetitive_lines = {
            line
            for line, count in line_counts.items()
            if count >= 3 and not self._is_content_line(line)
        }

        if not repetitive_lines:
            return text, position_map

        # Remove repetitive lines
        new_text = ""
        new_position_map = []

        for i, line in enumerate(lines):
            if line.strip() not in repetitive_lines:
                if new_text:
                    new_text += "\n"
                    new_position_map.append(-1)  # Mark newline as inserted
                new_text += line
                start_pos, end_pos = line_positions[i]
                new_position_map.extend(position_map[start_pos:end_pos])

        if len(new_text) != len(text):
            transformations.append("remove_headers_footers")

        return new_text, new_position_map

    def _is_content_line(self, line: str) -> bool:
        """Check if a line contains actual content vs header/footer."""
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            return False

        # Lines with just numbers (page numbers)
        if stripped.isdigit():
            return False

        # Lines with just roman numerals
        if re.match(r"^[ivxlcdm]+$", stripped.lower()):
            return False

        # Very short lines without meaningful content
        if len(stripped) < 5:
            return False

        # Lines that are just URLs
        if stripped.startswith(("http://", "https://", "www.")):
            return False

        # Lines that are just journal names or copyright
        copyright_patterns = [
            r"copyright",
            r"©\s*\d{4}",
            r"all rights reserved",
            r"acm\s+digital\s+library",
            r"doi:",
        ]

        for pattern in copyright_patterns:
            if re.search(pattern, stripped.lower()):
                return False

        return True
