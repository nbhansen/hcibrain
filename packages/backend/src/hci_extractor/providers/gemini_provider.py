"""Gemini API provider implementation."""

import logging
from typing import Any, Dict, Optional

import google.generativeai as genai

from hci_extractor.core.events import EventBus
from hci_extractor.core.models.exceptions import (
    EmptyResponseError,
    GeminiApiError,
    GeminiAuthenticationError,
    GeminiSafetyFilterError,
    LLMError,
    LLMValidationError,
    MissingApiKeyError,
    ProviderInitializationError,
    RateLimitError,
)
from hci_extractor.prompts.markup_prompt_loader import MarkupPromptLoader
from hci_extractor.providers.base import LLMProvider
from hci_extractor.providers.provider_config import LLMProviderConfig
from hci_extractor.utils.retry_handler import RetryPolicy, RetryStrategy

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Gemini API provider for LLM-based text analysis."""

    def __init__(
        self,
        provider_config: LLMProviderConfig,
        event_bus: EventBus,
        markup_prompt_loader: Optional[MarkupPromptLoader] = None,
        model_name: str = "gemini-1.5-flash",
    ):
        """
        Initialize Gemini provider.

        Args:
            provider_config: Provider-specific configuration
            event_bus: Event bus for publishing events
            markup_prompt_loader: MarkupPromptLoader for markup generation prompts
            model_name: Gemini model to use
        """
        # Initialize base class with provider-specific configuration
        super().__init__(provider_config, event_bus)

        # Initialize markup prompt loader
        self.markup_prompt_loader = markup_prompt_loader

        # Get API key from provider configuration
        self.api_key = provider_config.api_key
        if not self.api_key:
            raise MissingApiKeyError()

        # Configure Gemini
        try:
            genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]
            self.model = genai.GenerativeModel(model_name)  # type: ignore[attr-defined]
        except Exception as e:
            raise ProviderInitializationError() from e

        # Generation configuration optimized for academic analysis
        self.generation_config = genai.types.GenerationConfig(
            temperature=provider_config.temperature,
            max_output_tokens=provider_config.max_output_tokens,
            response_mime_type="application/json",  # Force JSON output
        )

        # Separate configuration for markup generation (plain text, no JSON)
        self.markup_generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Lower temperature for more consistent markup
            max_output_tokens=provider_config.max_output_tokens,
            # No response_mime_type specified = plain text output
        )

        # Configure Gemini-specific retry policy
        RetryPolicy(
            max_attempts=provider_config.max_attempts,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay_seconds=1.0,
            backoff_multiplier=2.0,
            max_delay_seconds=60.0,  # Longer max delay for API rate limits
            retryable_exceptions=(LLMError, RateLimitError),
            non_retryable_exceptions=(LLMValidationError, ValueError, TypeError),
        )
        # Note: Retry policy is now handled by the base class

        # Store model name for metrics
        self.model_name = model_name

    async def generate_markup(self, full_text: str) -> str:
        """
        Generate HTML markup for the full text with goal/method/result tags.
        Uses chunking for long documents to avoid token limits.

        Args:
            full_text: Complete text to analyze and mark up

        Returns:
            Full text with HTML markup tags for highlights
        """
        import asyncio

        from hci_extractor.core.text import ChunkingMode, create_markup_chunking_service

        try:
            # DEBUG: Log input details
            logger.info(f"🔍 MARKUP DEBUG - Input text length: {len(full_text)}")
            logger.info(f"🔍 MARKUP DEBUG - First 200 chars: {full_text[:200]!r}")
            logger.info(f"🔍 MARKUP DEBUG - Last 200 chars: {full_text[-200:]!r}")

            # Check if we need chunking (conservative limit to ensure reliability)
            max_single_chunk_size = 15000  # Conservative limit for reliable processing

            if len(full_text) <= max_single_chunk_size:
                logger.info(
                    "🔍 MARKUP DEBUG - Text fits in single chunk, processing directly",
                )
                return await self._process_single_chunk(full_text)

            # Use chunking for large documents
            logger.info("🔍 MARKUP DEBUG - Text too large, using chunking approach")
            chunking_service = create_markup_chunking_service(
                ChunkingMode.SENTENCE_BASED,
            )

            # Prepare chunks with overlap for context continuity
            chunks = chunking_service.prepare_chunks_for_markup(
                text=full_text,
                max_chunk_size=12000,  # Leave room for prompt overhead
                overlap_size=300,  # Moderate overlap for context
            )

            logger.info(
                f"🔍 MARKUP DEBUG - Created {len(chunks)} chunks for processing",
            )

            # Process chunks with rate limiting
            marked_chunks = []
            for i, chunk in enumerate(chunks):
                print(f"🔄 Processing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)")
                print(f"   First 100 chars: {chunk[:100]!r}")
                logger.info(
                    f"🔍 MARKUP DEBUG - Processing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)",
                )

                try:
                    marked_chunk = await self._process_single_chunk(
                        chunk,
                        chunk_index=i + 1,
                        total_chunks=len(chunks),
                    )

                    print(
                        f"✅ Chunk {i + 1} complete ({len(marked_chunk)} chars output)",
                    )
                    print(f"   First 100 chars of result: {marked_chunk[:100]!r}")

                    marked_chunks.append(marked_chunk)

                    # Rate limiting between chunks
                    if i < len(chunks) - 1:  # Don't wait after last chunk
                        await asyncio.sleep(0.5)

                except Exception as e:
                    print(f"❌ Chunk {i + 1} failed: {e}")
                    logger.warning(
                        f"🔍 MARKUP DEBUG - Chunk {i + 1} failed: {e}, using original text",
                    )
                    marked_chunks.append(chunk)  # Fallback to unmarked text

            # Merge chunks back together
            full_marked_text = self._merge_marked_chunks(marked_chunks)

            logger.info(
                f"🔍 MARKUP DEBUG - Final merged text: {len(full_marked_text)} chars",
            )
            logger.info(
                f"🔍 MARKUP DEBUG - Merged first 200 chars: {full_marked_text[:200]!r}",
            )
            logger.info(
                f"🔍 MARKUP DEBUG - Merged last 200 chars: {full_marked_text[-200:]!r}",
            )

            return full_marked_text

        except Exception as e:
            logger.exception("Gemini API error for markup generation")
            if isinstance(e, (LLMError, RateLimitError, LLMValidationError)):
                raise
            raise GeminiApiError()

    async def _process_single_chunk(
        self,
        text: str,
        chunk_index: int = 1,
        total_chunks: int = 1,
    ) -> str:
        """Process a single chunk of text for markup generation."""
        # Generate prompt using prompt loader if available, otherwise fallback to hardcoded
        if self.markup_prompt_loader:
            prompt = self.markup_prompt_loader.get_markup_prompt(
                text,
                chunk_index,
                total_chunks,
            )
        else:
            # Fallback to hardcoded prompt (for backwards compatibility)
            chunk_info = (
                f" (chunk {chunk_index}/{total_chunks})" if total_chunks > 1 else ""
            )
            prompt = f"""
You are an expert at analyzing academic papers. Please read the following paper text{chunk_info} and perform TWO tasks:

TASK 1 - CLEAN THE TEXT:
Remove ONLY these academic artifacts:
- Page numbers, headers, footers
- Broken hyphenations across lines
- Excessive whitespace
- Copyright notices
- Journal metadata

PRESERVE: Reference content, citations, and bibliographies as they are scientifically important

TASK 2 - ADD MARKUP TAGS:
Add these tags around relevant text:
- <goal confidence="0.XX">text</goal> for research objectives, questions, and hypotheses
- <method confidence="0.XX">text</method> for approaches, techniques, and methodologies  
- <result confidence="0.XX">text</result> for findings, outcomes, and discoveries

Rules:
1. Return the COMPLETE cleaned text with markup added
2. Do NOT summarize or omit any content text
3. Use confidence scores from 0.50 to 0.99 based on how certain you are
4. Only mark text that clearly fits the categories
5. Do NOT use any other HTML tags or formatting
6. Escape any existing < > characters in the text as &lt; &gt;
7. This may be part of a larger document - focus on marking up what's clearly identifiable in this section

Paper text:
{text}
"""

        logger.info(f"🔍 MARKUP DEBUG - Single chunk prompt length: {len(prompt)}")

        # Make API request with markup-specific config (plain text, not JSON)
        response = await self._make_markup_api_request(prompt)

        # DEBUG: Log raw response details
        raw_response = response["raw_response"]
        logger.info(f"🔍 MARKUP DEBUG - Chunk response length: {len(raw_response)}")

        return raw_response.strip()

    def _merge_marked_chunks(self, marked_chunks: list[str]) -> str:
        """Merge marked chunks back together with paragraph breaks."""
        if not marked_chunks:
            return ""

        if len(marked_chunks) == 1:
            return marked_chunks[0]

        # Simple merge - join with double newlines to preserve structure
        # The chunking service handles overlap intelligently, so simple concatenation works well
        merged = marked_chunks[0]

        for chunk in marked_chunks[1:]:
            # Add paragraph break between chunks
            merged += "\n\n" + chunk

        return merged

    async def _make_markup_api_request(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make API request to Gemini for markup generation - plain text output."""
        try:
            logger.info(
                "🔍 MARKUP DEBUG - Making Gemini API request with plain text config",
            )

            # Generate content using Gemini with markup-specific config
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.markup_generation_config,
                **kwargs,
            )

            # Check for successful response
            if not response.text:
                raise EmptyResponseError()

            logger.info(
                f"🔍 MARKUP DEBUG - Gemini returned {len(response.text)} characters",
            )

            # Return raw text - no JSON parsing for markup
            return {"raw_response": response.text}

        except Exception as e:
            # Handle specific Gemini errors
            error_msg = str(e).lower()

            if "quota" in error_msg or "rate limit" in error_msg:
                raise RateLimitError()
            if "invalid api key" in error_msg or "authentication" in error_msg:
                raise GeminiAuthenticationError()
            if "blocked" in error_msg or "safety" in error_msg:
                raise GeminiSafetyFilterError()
            raise GeminiApiError()

    async def _make_api_request(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Make API request to Gemini - pure infrastructure operation."""
        try:
            # Generate content using Gemini
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.generation_config,
                **kwargs,
            )

            # Check for successful response
            if not response.text:
                raise EmptyResponseError()

            # Return raw text - domain layer will handle parsing
            return {"raw_response": response.text}

        except Exception as e:
            # Handle specific Gemini errors
            error_msg = str(e).lower()

            if "quota" in error_msg or "rate limit" in error_msg:
                raise RateLimitError()
            if "invalid api key" in error_msg or "authentication" in error_msg:
                raise GeminiAuthenticationError()
            if "blocked" in error_msg or "safety" in error_msg:
                raise GeminiSafetyFilterError()
            raise GeminiApiError()

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Basic response validation - delegates to domain layer."""
        # Minimal validation - just check we got a response
        # Domain layer handles actual validation
        return "raw_response" in response and response["raw_response"]

    def get_usage_stats(self) -> Dict[str, Any]:
        """Return usage statistics.

        This method is deprecated. Use the global metrics collector instead.
        Returns empty stats for backwards compatibility.
        """
        logger.warning(
            "GeminiProvider.get_usage_stats() is deprecated. "
            "Use get_metrics_collector().get_llm_summary() instead.",
        )
        return {
            "requests_made": 0,
            "tokens_used": 0,
            "estimated_cost": 0.0,
            "model_name": self.model_name,
        }
