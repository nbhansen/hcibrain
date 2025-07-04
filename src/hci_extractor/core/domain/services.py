"""Domain services for HCI extractor - orchestrate business logic."""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.events import (
    EventBus,
    SectionProcessingCompleted,
    SectionProcessingStarted,
)
from hci_extractor.core.metrics import LLMMetricsContext
from hci_extractor.core.domain.transformers import ElementTransformer, ResponseParser
from hci_extractor.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class SectionAnalysisService:
    """Orchestrates section analysis with business rules."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        config: ExtractorConfig,
        event_bus: EventBus,
    ):
        """
        Initialize section analysis service.

        Args:
            llm_provider: LLM provider for API calls
            config: Configuration object
            event_bus: Event bus for publishing events
        """
        self._llm_provider = llm_provider
        self._config = config
        self._event_bus = event_bus

    async def analyze_section(
        self,
        section_text: str,
        section_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], ...]:
        """
        Analyze a section and return extracted elements.

        Args:
            section_text: Text content to analyze
            section_type: Type of section
            context: Additional context

        Returns:
            Immutable tuple of extracted elements
        """
        if not section_text.strip():
            return tuple()

        paper_id = context.get("paper_id") if context else None

        # Track metrics and publish events
        with LLMMetricsContext(
            provider=self._llm_provider.__class__.__name__.lower().replace(
                "provider", ""
            ),
            model=getattr(self._llm_provider, "model_name", "unknown"),
            operation="analyze_section",
            paper_id=paper_id,
            section_type=section_type,
        ) as metrics:
            start_time = time.time()

            # Publish processing started event
            self._event_bus.publish(
                SectionProcessingStarted(
                    paper_id=paper_id or "unknown",
                    section_type=section_type,
                    section_size_chars=len(section_text),
                    chunk_count=1,  # Chunking not implemented in simple extractor
                )
            )

            try:
                # Call provider for raw analysis
                raw_elements = await self._llm_provider.analyze_section(
                    section_text, section_type, context
                )

                # Transform to domain objects
                cleaned_elements = ElementTransformer.transform_elements(raw_elements)

                # Update metrics
                metrics.tokens_input = len(section_text) // 4  # Rough estimate
                metrics.tokens_output = sum(len(str(e)) for e in cleaned_elements) // 4

                # Publish completion event
                duration = time.time() - start_time
                self._event_bus.publish(
                    SectionProcessingCompleted(
                        paper_id=paper_id or "unknown",
                        section_type=section_type,
                        elements_extracted=len(cleaned_elements),
                        duration_seconds=duration,
                        tokens_used=metrics.tokens_input + metrics.tokens_output,
                    )
                )

                logger.info(
                    f"Analyzed {section_type} section: "
                    f"{len(cleaned_elements)} elements extracted"
                )

                return cleaned_elements

            except Exception as e:
                logger.error(f"Error analyzing section {section_type}: {e}")
                raise


class PaperSummaryService:
    """Orchestrates paper summary generation with business rules."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        config: ExtractorConfig,
        event_bus: EventBus,
    ):
        """
        Initialize paper summary service.

        Args:
            llm_provider: LLM provider for API calls
            config: Configuration object
            event_bus: Event bus for publishing events
        """
        self._llm_provider = llm_provider
        self._config = config
        self._event_bus = event_bus

    async def generate_summary(
        self,
        abstract_text: str,
        introduction_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate paper summary from abstract and introduction.

        Args:
            abstract_text: Abstract section text
            introduction_text: Introduction section text
            context: Additional context

        Returns:
            Immutable summary dictionary
        """
        if not abstract_text.strip() and not introduction_text.strip():
            return {
                "summary": "",
                "confidence": 0.0,
                "source_sections": tuple(),
            }

        paper_id = context.get("paper_id") if context else None

        # Track metrics
        with LLMMetricsContext(
            provider=self._llm_provider.__class__.__name__.lower().replace(
                "provider", ""
            ),
            model=getattr(self._llm_provider, "model_name", "unknown"),
            operation="generate_paper_summary",
            paper_id=paper_id,
            section_type="summary",
        ) as metrics:
            try:
                # Call provider for raw summary
                raw_summary = await self._llm_provider.generate_paper_summary(
                    abstract_text, introduction_text, context
                )

                # Transform to domain format
                cleaned_summary = ElementTransformer.transform_summary(raw_summary)

                # Update metrics
                total_text = abstract_text + introduction_text
                metrics.tokens_input = len(total_text) // 4
                metrics.tokens_output = len(str(cleaned_summary)) // 4

                logger.info(
                    f"Generated paper summary with confidence "
                    f"{cleaned_summary['confidence']}"
                )

                return cleaned_summary

            except Exception as e:
                logger.error(f"Error generating paper summary: {e}")
                raise
