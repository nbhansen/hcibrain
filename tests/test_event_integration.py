"""Test event system integration with extraction pipeline."""

import asyncio
from typing import List
from unittest.mock import AsyncMock, patch

import pytest

from hci_extractor.core.analysis import LLMSectionProcessor, extract_paper_simple
from hci_extractor.core.events import (
    DomainEvent,
    EventBus,
    EventHandler,
    ExtractionCompleted,
    ExtractionFailed,
    ExtractionStarted,
    SectionDetected,
    SectionProcessingCompleted,
    SectionProcessingStarted,
)
from hci_extractor.core.models import (
    DetectedSection,
    Paper,
    PdfContent,
    PdfPage,
)
from hci_extractor.providers import LLMProvider


class EventCollector(EventHandler):
    """Test event handler that collects all events."""

    def __init__(self):
        self.events: List[DomainEvent] = []

    def handle(self, event: DomainEvent) -> None:
        self.events.append(event)

    def get_events_by_type(self, event_type):
        """Get all events of a specific type."""
        return [e for e in self.events if isinstance(e, event_type)]

    def clear(self):
        """Clear collected events."""
        self.events.clear()


@pytest.fixture
def event_collector():
    """Create and register an event collector."""
    collector = EventCollector()
    event_bus = EventBus()  # Create a fresh EventBus for testing
    event_bus.subscribe_all(collector)
    yield collector
    event_bus.clear()  # Clean up


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = AsyncMock(spec=LLMProvider)
    # Set up to handle multiple calls (for chunked processing)
    provider.analyze_section.side_effect = lambda *args, **kwargs: [
        {
            "element_type": "finding",
            "text": "Test finding from section",
            "evidence_type": "quantitative",
            "confidence": 0.9,
        }
    ]
    return provider


@pytest.fixture
def mock_pdf_extractor():
    """Mock PDF extractor to return test content."""
    with patch("hci_extractor.core.analysis.simple_extractor.PdfExtractor") as mock:
        instance = mock.return_value
        instance.extract_content.return_value = PdfContent(
            file_path="test.pdf",
            total_pages=1,  # Match the number of pages in the tuple
            pages=(
                PdfPage(
                    page_number=1,
                    text="Title of the Paper\n\nAbstract\n\nThis is a test abstract with findings and results that should be detected by the section detector.\n\n1. Introduction\n\nThis is the introduction section with background information.",
                    char_count=len(
                        "Title of the Paper\n\nAbstract\n\nThis is a test abstract with findings and results that should be detected by the section detector.\n\n1. Introduction\n\nThis is the introduction section with background information."
                    ),
                    dimensions=(612.0, 792.0),
                    char_positions=(),
                ),
            ),
            extraction_metadata={},
        )
        yield mock


@pytest.mark.asyncio
async def test_extraction_events_published(
    event_collector, mock_llm_provider, mock_pdf_extractor, tmp_path
):
    """Test that extraction pipeline publishes expected events."""
    # Create a test PDF path
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"dummy content")

    # Run extraction
    await extract_paper_simple(
        pdf_path=pdf_path,
        llm_provider=mock_llm_provider,
        paper_metadata={"title": "Test Paper", "authors": ["Test Author"]},
    )

    # Check extraction started event
    started_events = event_collector.get_events_by_type(ExtractionStarted)
    assert len(started_events) == 1
    assert started_events[0].pdf_path == str(pdf_path)
    assert started_events[0].file_size_bytes == 13  # "dummy content"

    # Check section detected event
    section_events = event_collector.get_events_by_type(SectionDetected)
    assert len(section_events) == 1
    assert section_events[0].section_count > 0

    # Check extraction completed event
    completed_events = event_collector.get_events_by_type(ExtractionCompleted)
    assert len(completed_events) == 1
    assert completed_events[0].pages_extracted == 1  # We only have 1 page in mock
    assert completed_events[0].duration_seconds > 0

    # Verify no extraction failed events
    failed_events = event_collector.get_events_by_type(ExtractionFailed)
    assert len(failed_events) == 0


@pytest.mark.asyncio
async def test_extraction_failure_events(event_collector, mock_llm_provider, tmp_path):
    """Test that extraction failures publish appropriate events."""
    # Create a test PDF path that doesn't exist
    pdf_path = tmp_path / "nonexistent.pdf"

    # Mock PDF extractor to raise an error
    with patch("hci_extractor.core.analysis.simple_extractor.PdfExtractor") as mock:
        instance = mock.return_value
        instance.extract_content.side_effect = Exception("PDF read error")

        # Run extraction expecting failure
        with pytest.raises(Exception):
            await extract_paper_simple(
                pdf_path=pdf_path, llm_provider=mock_llm_provider
            )

    # Check extraction started event was published
    started_events = event_collector.get_events_by_type(ExtractionStarted)
    assert len(started_events) == 1

    # Check extraction failed event was published
    failed_events = event_collector.get_events_by_type(ExtractionFailed)
    assert len(failed_events) == 1
    assert failed_events[0].pdf_path == str(pdf_path)
    assert "PDF read error" in failed_events[0].error_message


@pytest.mark.asyncio
async def test_section_processing_events(event_collector, mock_llm_provider):
    """Test that section processing publishes expected events."""
    # Create test data
    paper = Paper.create_with_auto_id(
        title="Test Paper", authors=("Test Author",), file_path="test.pdf"
    )

    section_text = "This is a test methodology section with important findings."
    section = DetectedSection.create_with_auto_id(
        section_type="methodology",
        title="Methodology",
        text=section_text,
        start_page=2,
        end_page=3,
        confidence=0.95,
        char_start=0,
        char_end=len(section_text),
    )

    # Create processor and process section
    processor = LLMSectionProcessor(mock_llm_provider)
    elements = await processor.process_section(section, paper)

    # Check section processing started event
    started_events = event_collector.get_events_by_type(SectionProcessingStarted)
    assert len(started_events) == 1
    assert started_events[0].paper_id == paper.paper_id
    assert started_events[0].section_type == "methodology"
    assert started_events[0].section_size_chars == len(section.text)
    assert started_events[0].chunk_count == 1

    # Check section processing completed event
    completed_events = event_collector.get_events_by_type(SectionProcessingCompleted)
    assert len(completed_events) == 1
    assert completed_events[0].paper_id == paper.paper_id
    assert completed_events[0].section_type == "methodology"
    assert completed_events[0].elements_extracted == len(elements)
    assert completed_events[0].duration_seconds >= 0


@pytest.mark.asyncio
async def test_chunked_section_events(event_collector, mock_llm_provider):
    """Test that chunked sections publish correct events."""
    # Create test data with a large section
    paper = Paper.create_with_auto_id(
        title="Test Paper", authors=("Test Author",), file_path="test.pdf"
    )

    # Create a large section that will be chunked
    large_text = "This is a large section. " * 500  # ~12,500 chars
    section = DetectedSection.create_with_auto_id(
        section_type="results",
        title="Results",
        text=large_text,
        start_page=3,
        end_page=10,
        confidence=0.95,
        char_start=0,
        char_end=len(large_text),
    )

    # Create processor with small chunk size to force chunking
    processor = LLMSectionProcessor(
        mock_llm_provider, chunk_size=1000, chunk_overlap=100
    )
    await processor.process_section(section, paper)

    # Check section processing started event shows multiple chunks
    started_events = event_collector.get_events_by_type(SectionProcessingStarted)
    assert len(started_events) == 1
    assert started_events[0].chunk_count > 1  # Should be chunked

    # Check processing completed event
    completed_events = event_collector.get_events_by_type(SectionProcessingCompleted)
    assert len(completed_events) == 1
    assert (
        completed_events[0].elements_extracted > 0
    )  # Should have extracted elements from chunks
    assert completed_events[0].section_type == "results"


@pytest.mark.asyncio
async def test_concurrent_event_handling(
    event_collector, mock_llm_provider, mock_pdf_extractor, tmp_path
):
    """Test that events work correctly with concurrent operations."""
    # Create multiple test PDFs
    pdf_paths = []
    for i in range(3):
        pdf_path = tmp_path / f"test_{i}.pdf"
        pdf_path.write_bytes(b"dummy content")
        pdf_paths.append(pdf_path)

    # Run multiple extractions concurrently
    tasks = [
        extract_paper_simple(
            pdf_path=pdf_path,
            llm_provider=mock_llm_provider,
            paper_metadata={"title": f"Paper {i}", "authors": [f"Author {i}"]},
        )
        for i, pdf_path in enumerate(pdf_paths)
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    # Check we got events for all extractions
    started_events = event_collector.get_events_by_type(ExtractionStarted)
    assert len(started_events) == 3

    completed_events = event_collector.get_events_by_type(ExtractionCompleted)
    assert len(completed_events) == 3

    # Verify all papers were processed
    paper_ids = {e.paper_id for e in completed_events}
    assert len(paper_ids) == 3  # All unique paper IDs


def test_event_handler_protocol():
    """Test that event handler protocol works correctly."""

    # Create a custom handler
    class CustomHandler:
        def __init__(self):
            self.handled_events = []

        def handle(self, event: DomainEvent) -> None:
            self.handled_events.append(event)

    handler = CustomHandler()
    event_bus = EventBus()  # Create a fresh EventBus for testing

    # Subscribe to specific event type
    event_bus.subscribe(ExtractionStarted, handler)

    # Publish events
    event_bus.publish(
        ExtractionStarted(
            pdf_path="test.pdf", paper_id="test-123", file_size_bytes=1000
        )
    )

    event_bus.publish(
        ExtractionCompleted(
            paper_id="test-123",
            pages_extracted=10,
            characters_extracted=5000,
            duration_seconds=5.0,
        )
    )

    # Handler should only receive ExtractionStarted
    assert len(handler.handled_events) == 1
    assert isinstance(handler.handled_events[0], ExtractionStarted)

    event_bus.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
