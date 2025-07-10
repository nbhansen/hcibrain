"""
Domain events for decoupled communication between components.

This module implements a simple event system that allows components to
communicate without direct dependencies, following the Observer pattern
with immutable events.
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Protocol, Type
from uuid import uuid4


@dataclass(frozen=True)
class DomainEvent(ABC):
    """
    Base class for all domain events.

    All events are immutable and contain metadata about when they occurred
    and a unique identifier for tracing.
    """


@dataclass(frozen=True)
class ExtractionStarted(DomainEvent):
    """Fired when PDF extraction begins."""

    pdf_path: str
    paper_id: str
    file_size_bytes: int
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ExtractionCompleted(DomainEvent):
    """Fired when PDF extraction completes successfully."""

    paper_id: str
    pages_extracted: int
    characters_extracted: int
    duration_seconds: float
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ExtractionFailed(DomainEvent):
    """Fired when PDF extraction fails."""

    pdf_path: str
    error_type: str
    error_message: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class SectionDetected(DomainEvent):
    """Fired when sections are detected in a document."""

    paper_id: str
    section_count: int
    section_types: tuple[str, ...]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class SectionProcessingStarted(DomainEvent):
    """Fired when LLM processing of a section begins."""

    paper_id: str
    section_type: str
    section_size_chars: int
    chunk_count: int
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class SectionProcessingCompleted(DomainEvent):
    """Fired when LLM processing of a section completes."""

    paper_id: str
    section_type: str
    elements_extracted: int
    duration_seconds: float
    tokens_used: Optional[int] = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ChunkProcessingStarted(DomainEvent):
    """Fired when processing of a text chunk begins."""

    paper_id: str
    section_type: str
    chunk_index: int
    total_chunks: int
    chunk_size_chars: int


@dataclass(frozen=True)
class ChunkProcessingCompleted(DomainEvent):
    """Fired when processing of a text chunk completes."""

    paper_id: str
    section_type: str
    chunk_index: int
    total_chunks: int
    elements_extracted: int
    duration_seconds: float


@dataclass(frozen=True)
class JsonRecoveryAttempted(DomainEvent):
    """Fired when JSON recovery is attempted on malformed response."""

    paper_id: str
    section_type: str
    strategy_used: str
    success: bool
    error_message: Optional[str] = None


@dataclass(frozen=True)
class ExtractionQualityAssessed(DomainEvent):
    """Fired when extraction quality is assessed."""

    paper_id: str
    section_type: str
    elements_extracted: int
    average_confidence: float
    quality_score: float
    quality_issues: tuple[str, ...]


@dataclass(frozen=True)
class BatchProcessingStarted(DomainEvent):
    """Fired when batch processing begins."""

    total_papers: int
    input_directory: str
    output_directory: str
    max_concurrent: int
    filter_pattern: str


@dataclass(frozen=True)
class BatchProcessingCompleted(DomainEvent):
    """Fired when batch processing completes."""

    total_papers: int
    successful_papers: int
    failed_papers: int
    duration_seconds: float
    average_elements_per_paper: float


@dataclass(frozen=True)
class PaperProcessingStarted(DomainEvent):
    """Fired when processing of a single paper begins."""

    paper_id: str
    paper_title: str
    file_path: str
    file_size_bytes: int
    batch_position: Optional[int] = None
    total_papers_in_batch: Optional[int] = None


@dataclass(frozen=True)
class PaperProcessingCompleted(DomainEvent):
    """Fired when processing of a single paper completes."""

    paper_id: str
    paper_title: str
    elements_extracted: int
    sections_processed: int
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    batch_position: Optional[int] = None
    total_papers_in_batch: Optional[int] = None


@dataclass(frozen=True)
class ConfigurationLoaded(DomainEvent):
    """Fired when configuration is loaded or updated."""

    config_source: str  # "file", "environment", "cli", "default"
    config_path: Optional[str]
    overrides_applied: tuple[str, ...]
    chunk_size: int
    timeout_seconds: float
    max_retries: int


@dataclass(frozen=True)
class ProgressUpdate(DomainEvent):
    """Fired to update processing progress."""

    operation_type: str  # "batch", "paper", "section", "chunk"
    operation_id: str
    current_step: int
    total_steps: int
    step_name: str
    percentage_complete: float
    estimated_time_remaining: Optional[float] = None


@dataclass(frozen=True)
class ElementValidated(DomainEvent):
    """Fired when an element passes validation."""

    paper_id: str
    element_id: str
    element_type: str
    confidence: float


@dataclass(frozen=True)
class ElementRejected(DomainEvent):
    """Fired when an element fails validation."""

    paper_id: str
    element_id: str
    rejection_reason: str


@dataclass(frozen=True)
class ExportStarted(DomainEvent):
    """Fired when export operation begins."""

    export_format: str
    element_count: int
    output_path: str


@dataclass(frozen=True)
class ExportCompleted(DomainEvent):
    """Fired when export operation completes."""

    export_format: str
    elements_exported: int
    file_size_bytes: int
    duration_seconds: float


@dataclass(frozen=True)
class RetryAttempted(DomainEvent):
    """Fired when a retry attempt is made."""

    operation_name: str
    attempt_number: int
    max_attempts: int
    delay_seconds: float
    error_type: str
    error_message: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class RetryExhausted(DomainEvent):
    """Fired when all retry attempts are exhausted."""

    operation_name: str
    total_attempts: int
    total_duration_seconds: float
    final_error_type: str
    final_error_message: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class RetrySucceeded(DomainEvent):
    """Fired when an operation succeeds after retries."""

    operation_name: str
    successful_attempt: int
    total_duration_seconds: float
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)


class EventHandler(Protocol):
    """Protocol for event handlers."""

    def handle(self, event: DomainEvent) -> None:
        """Handle a domain event."""
        ...


class EventBus:
    """
    Simple synchronous event bus for publishing and subscribing to events.

    This implementation is thread-safe and maintains weak references to
    handlers to prevent memory leaks.
    """

    def __init__(self) -> None:
        self._handlers: Dict[Type[DomainEvent], tuple[EventHandler, ...]] = {}
        self._global_handlers: tuple[EventHandler, ...] = ()

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type: The type of event to handle
            handler: The handler to call when the event is published
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = ()
        self._handlers[event_type] = self._handlers[event_type] + (handler,)

    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Subscribe a handler to all events.

        Useful for logging, metrics, or debugging.

        Args:
            handler: The handler to call for all events
        """
        self._global_handlers = (*self._global_handlers, handler)

    def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all registered handlers.

        Handlers are called synchronously in the order they were registered.
        Exceptions in handlers are logged but don't stop other handlers.

        Args:
            event: The event to publish
        """
        # Call specific handlers
        for handler in self._handlers.get(type(event), ()):
            try:
                handler.handle(event)
            except Exception as e:
                # Log error but continue with other handlers
                import logging

                logging.error(f"Error in event handler: {e}", exc_info=True)

        # Call global handlers
        for handler in self._global_handlers:
            try:
                handler.handle(event)
            except Exception as e:
                import logging

                logging.error(f"Error in global event handler: {e}", exc_info=True)

    def clear(self) -> None:
        """Clear all event handlers."""
        self._handlers = {}
        self._global_handlers = ()


# Example handlers for common use cases


class LoggingEventHandler:
    """Logs all events for debugging."""

    def __init__(self, logger: Any) -> None:
        self.logger = logger

    def handle(self, event: DomainEvent) -> None:
        event_id = getattr(event, "event_id", "unknown")
        occurred_at = getattr(event, "occurred_at", "unknown")
        self.logger.debug(
            f"Event {event.__class__.__name__} [{event_id}] at {occurred_at}",
        )


class MetricsEventHandler:
    """Collects metrics from events."""

    def __init__(self) -> None:
        self.event_counts: Dict[str, int] = {}
        self.processing_times: tuple[float, ...] = ()

    def handle(self, event: DomainEvent) -> None:
        # Count events by type
        event_name = event.__class__.__name__
        self.event_counts[event_name] = self.event_counts.get(event_name, 0) + 1

        # Track processing times
        if isinstance(
            event,
            (
                ExtractionCompleted,
                SectionProcessingCompleted,
                ChunkProcessingCompleted,
                PaperProcessingCompleted,
                BatchProcessingCompleted,
            ),
        ):
            self.processing_times = (*self.processing_times, event.duration_seconds)

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics as an immutable snapshot."""
        return {
            "event_counts": dict(self.event_counts),
            "total_events": sum(self.event_counts.values()),
            "avg_processing_time": (
                sum(self.processing_times) / len(self.processing_times)
                if self.processing_times
                else 0.0
            ),
        }
