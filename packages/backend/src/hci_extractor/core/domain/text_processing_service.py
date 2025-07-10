"""Domain service for text processing operations."""

from typing import List


class TextProcessingService:
    """Domain service for handling text processing operations."""

    @staticmethod
    def merge_marked_chunks(marked_chunks: List[str]) -> str:
        """
        Merge marked chunks back together with appropriate formatting.

        This is business logic for combining text chunks that have been
        processed separately while maintaining document structure.

        Args:
            marked_chunks: List of text chunks with markup applied

        Returns:
            Single merged text with proper formatting
        """
        if not marked_chunks:
            return ""

        if len(marked_chunks) == 1:
            return marked_chunks[0]

        # Simple merge - join with double newlines to preserve structure
        # The chunking service handles overlap intelligently, so simple concatenation works well
        merged = marked_chunks[0]

        for chunk in marked_chunks[1:]:
            # Add paragraph break between chunks to maintain readability
            merged += "\n\n" + chunk

        return merged
