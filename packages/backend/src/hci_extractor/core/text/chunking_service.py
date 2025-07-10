"""Text chunking service for markup generation.

Adapted from silly_PDF2WAV project for handling long documents that exceed
LLM token limits. Uses sentence-aware chunking to preserve content integrity.
"""

import logging
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class ChunkingMode(Enum):
    """Available chunking strategies."""

    SENTENCE_BASED = "sentence"  # Split on sentences first
    WORD_BASED = "word"  # Split on words if sentences too large


class IChunkingStrategy(ABC):
    """Interface for text chunking strategies."""

    @abstractmethod
    def chunk_text(self, text: str, max_chunk_size: int) -> List[str]:
        """Split text into optimal chunks for LLM processing."""


class SentenceBasedChunking(IChunkingStrategy):
    """Sentence-aware chunking that preserves content integrity for markup
    generation."""

    def chunk_text(self, text: str, max_chunk_size: int) -> List[str]:
        """Split text on sentence boundaries, then words if needed."""
        if len(text) <= max_chunk_size:
            return [text]

        # Split on paragraph boundaries first for better context preservation
        paragraphs = self._split_paragraphs(text)
        result_chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # If single paragraph is too large, process with sentence splitting
            if len(paragraph) > max_chunk_size:
                # Add current chunk if it exists
                if current_chunk.strip():
                    result_chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Process large paragraph by sentences
                sentence_chunks = self._process_large_paragraph(
                    paragraph,
                    max_chunk_size,
                )
                result_chunks.extend(sentence_chunks)

            elif (
                len(current_chunk) + len(paragraph) + 2 > max_chunk_size
                and current_chunk
            ):
                # Current paragraph would exceed limit, save current chunk
                result_chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                # Add paragraph to current chunk
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        # Add final chunk if it exists
        if current_chunk.strip():
            result_chunks.append(current_chunk.strip())

        return [chunk for chunk in result_chunks if chunk.strip()]

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs for better context preservation."""
        # Split on double newlines (paragraph boundaries)
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _process_large_paragraph(
        self,
        paragraph: str,
        max_chunk_size: int,
    ) -> List[str]:
        """Process a large paragraph by splitting on sentences."""
        sentences = self._split_sentences(paragraph)
        result_chunks = []
        current_subchunk = ""

        for sentence in sentences:
            # If single sentence is too large, split by words
            if len(sentence) > max_chunk_size:
                word_chunks = self._split_by_words(sentence, max_chunk_size)
                # Add current subchunk if it exists
                if current_subchunk.strip():
                    result_chunks.append(current_subchunk.strip())
                    current_subchunk = ""
                # Add word chunks
                result_chunks.extend(word_chunks)
            elif (
                len(current_subchunk) + len(sentence) + 1 > max_chunk_size
                and current_subchunk
            ):
                # Current sentence would exceed limit, save current subchunk
                result_chunks.append(current_subchunk.strip())
                current_subchunk = sentence
            else:
                # Add sentence to current subchunk
                current_subchunk += " " + sentence if current_subchunk else sentence

        # Add final subchunk if it exists
        if current_subchunk.strip():
            result_chunks.append(current_subchunk.strip())

        return result_chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using academic-aware punctuation."""
        # Enhanced sentence splitting for academic papers
        # Handle common abbreviations that shouldn't split sentences
        text = text.replace("et al.", "et al·")  # Temporary replacement
        text = text.replace("e.g.", "e·g·")
        text = text.replace("i.e.", "i·e·")
        text = text.replace("Dr.", "Dr·")
        text = text.replace("Prof.", "Prof·")
        text = text.replace("Fig.", "Fig·")
        text = text.replace("Eq.", "Eq·")

        # Split on sentence boundaries with lookahead for capital letters
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)

        # Restore abbreviated forms
        sentences = [s.replace("·", ".") for s in sentences]

        return [s.strip() for s in sentences if s.strip()]

    def _split_by_words(self, text: str, max_size: int) -> List[str]:
        """Split text by words when sentences are too large."""
        words = text.split()
        chunks = []
        current_chunk = ""

        for word in words:
            if len(current_chunk) + len(word) + 1 > max_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                current_chunk += " " + word if current_chunk else word

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks


class WordBasedChunking(IChunkingStrategy):
    """Simple word-based chunking for basic splitting."""

    def chunk_text(self, text: str, max_chunk_size: int) -> List[str]:
        """Split text by words only."""
        if len(text) <= max_chunk_size:
            return [text]

        words = text.split()
        result_chunks = []
        current_chunk = ""

        for word in words:
            if len(current_chunk) + len(word) + 1 > max_chunk_size and current_chunk:
                result_chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                current_chunk += " " + word if current_chunk else word

        if current_chunk.strip():
            result_chunks.append(current_chunk.strip())

        return result_chunks


class MarkupChunkingService:
    """Service for text chunking optimized for markup generation.

    Handles long documents by splitting them into manageable chunks that preserve
    context and content integrity for LLM markup generation.
    """

    def __init__(self, strategy: Optional[IChunkingStrategy] = None):
        """Initialize with chunking strategy."""
        self._strategy = strategy or SentenceBasedChunking()

    def prepare_chunks_for_markup(
        self,
        text: str,
        max_chunk_size: int = 8000,
        overlap_size: int = 200,
    ) -> List[str]:
        """Prepare text chunks for markup generation with context overlap.

        Args:
            text: Full text to chunk
            max_chunk_size: Maximum size per chunk in characters
            overlap_size: Number of characters to overlap between chunks for context

        Returns:
            List of text chunks ready for markup processing
        """
        logger.info(
            f"Preparing chunks for markup: {len(text)} chars, max_chunk={max_chunk_size}",
        )

        if len(text) <= max_chunk_size:
            logger.info("Text fits in single chunk")
            return [text]

        # Get base chunks from strategy
        base_chunks = self._strategy.chunk_text(text, max_chunk_size - overlap_size)

        # Add overlap between chunks for better context continuity
        overlapped_chunks = self._add_context_overlap(base_chunks, overlap_size)

        logger.info(f"Created {len(overlapped_chunks)} chunks with overlap")
        for i, chunk in enumerate(overlapped_chunks):
            logger.debug(f"Chunk {i + 1}: {len(chunk)} chars")

        return overlapped_chunks

    def _add_context_overlap(self, chunks: List[str], overlap_size: int) -> List[str]:
        """Add overlap between chunks for better context continuity."""
        if len(chunks) <= 1 or overlap_size <= 0:
            return chunks

        overlapped_chunks = [chunks[0]]  # First chunk unchanged

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # Take last `overlap_size` characters from previous chunk
            if len(prev_chunk) > overlap_size:
                # Try to find a good breaking point (sentence or word boundary)
                overlap_text = prev_chunk[-overlap_size:]

                # Find the last sentence boundary in the overlap
                sentence_match = re.search(r"[.!?]\s+", overlap_text)
                if sentence_match:
                    overlap_start = sentence_match.end()
                    overlap_text = overlap_text[overlap_start:]

                # Create overlapped chunk
                overlapped_chunk = overlap_text + " " + current_chunk
                overlapped_chunks.append(overlapped_chunk)
            else:
                # Previous chunk too short for meaningful overlap
                overlapped_chunks.append(current_chunk)

        return overlapped_chunks


def create_markup_chunking_service(
    mode: ChunkingMode = ChunkingMode.SENTENCE_BASED,
) -> MarkupChunkingService:
    """Factory function for creating markup chunking services."""
    if mode == ChunkingMode.SENTENCE_BASED:
        return MarkupChunkingService(SentenceBasedChunking())
    if mode == ChunkingMode.WORD_BASED:
        return MarkupChunkingService(WordBasedChunking())
    raise ValueError(f"Unsupported chunking mode: {mode}")
