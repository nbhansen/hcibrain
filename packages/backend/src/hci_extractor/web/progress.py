"""WebSocket progress tracking for long-running operations."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from fastapi import WebSocket
from pydantic import BaseModel

from hci_extractor.core.events import DomainEvent, EventHandler

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProgressState:
    """Immutable progress state for tracking operation progress."""

    current_progress: float
    sections_processed: int = 0
    total_sections: int = 0

    def with_progress(self, progress: float) -> "ProgressState":
        """Create new state with updated progress."""
        return ProgressState(
            current_progress=progress,
            sections_processed=self.sections_processed,
            total_sections=self.total_sections,
        )

    def with_section_completed(self) -> "ProgressState":
        """Create new state with incremented section count."""
        new_sections = self.sections_processed + 1
        # Calculate progress based on sections completed
        progress = min(0.9, 0.1 + (new_sections * 0.15))
        return ProgressState(
            current_progress=progress,
            sections_processed=new_sections,
            total_sections=self.total_sections,
        )

    def with_total_sections(self, total: int) -> "ProgressState":
        """Create new state with total sections count."""
        return ProgressState(
            current_progress=self.current_progress,
            sections_processed=self.sections_processed,
            total_sections=total,
        )


class ProgressMessage(BaseModel):
    """Progress message sent via WebSocket."""

    session_id: str
    status: str
    progress: float
    message: str
    data: Dict[str, Any] = {}


class WebSocketManager:
    """Manages WebSocket connections for progress tracking."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_handlers: Dict[str, "WebSocketProgressHandler"] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Accept a WebSocket connection and store it.

        Args:
            websocket: WebSocket connection
            session_id: Unique session identifier
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            session_id: Session to disconnect
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_handlers:
            del self.session_handlers[session_id]
        logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_progress(self, session_id: str, message: ProgressMessage) -> None:
        """
        Send progress message to a specific session.

        Args:
            session_id: Session to send message to
            message: Progress message to send
        """
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message.model_dump())
            except Exception:
                logger.exception(f"Error sending progress to {session_id}")
                self.disconnect(session_id)

    def create_session_id(self) -> str:
        """
        Generate a new session ID.

        Returns:
            Unique session identifier
        """
        return str(uuid4())


class WebSocketProgressHandler(EventHandler):
    """Event handler that forwards domain events to WebSocket."""

    def __init__(self, manager: WebSocketManager, session_id: str) -> None:
        self.manager = manager
        self.session_id = session_id
        self._progress_state = ProgressState(current_progress=0.0)

    def handle(self, event: DomainEvent) -> None:
        """
        Handle domain event and forward as progress message.

        Args:
            event: Domain event to handle
        """
        try:
            # Map different event types to progress messages
            if hasattr(event, "operation_id") and event.operation_id != self.session_id:
                return  # Not for this session

            result = self._map_event_to_progress(event)
            if result:
                message, new_state = result
                # Update progress state immutably
                self._progress_state = new_state

                # Schedule the async call in the event loop and store reference
                task = asyncio.create_task(
                    self.manager.send_progress(self.session_id, message),
                )
                # Add error handling for the task
                task.add_done_callback(
                    lambda t: logger.error(f"Progress send error: {t.exception()}")
                    if t.exception()
                    else None,
                )

        except Exception:
            logger.exception("Error handling event in WebSocket handler")

    def _map_event_to_progress(
        self,
        event: DomainEvent,
    ) -> Optional[Tuple[ProgressMessage, ProgressState]]:
        """
        Map domain event to progress message and new state.

        Args:
            event: Domain event

        Returns:
            Tuple of (progress message, new state) or None if event should be ignored
        """
        event_name = event.__class__.__name__

        # Map specific events to progress
        if event_name == "PaperProcessingStarted":
            new_state = self._progress_state.with_progress(0.0)
            message = ProgressMessage(
                session_id=self.session_id,
                status="started",
                progress=0.0,
                message="Starting paper processing",
                data={"event": event_name},
            )
            return (message, new_state)

        if event_name == "SectionDetected":
            new_state = self._progress_state.with_progress(0.1)
            sections_count = getattr(event, "sections_count", 0)
            if sections_count > 0:
                new_state = new_state.with_total_sections(sections_count)

            message = ProgressMessage(
                session_id=self.session_id,
                status="processing",
                progress=new_state.current_progress,
                message="Detected paper sections",
                data={
                    "event": event_name,
                    "sections_found": sections_count,
                },
            )
            return (message, new_state)

        if event_name == "SectionProcessingStarted":
            message = ProgressMessage(
                session_id=self.session_id,
                status="processing",
                progress=self._progress_state.current_progress,
                message=f"Processing {getattr(event, 'section_name', 'section')}",
                data={"event": event_name},
            )
            return (message, self._progress_state)

        if event_name == "SectionProcessingCompleted":
            # Update progress based on completed sections
            new_state = self._progress_state.with_section_completed()
            message = ProgressMessage(
                session_id=self.session_id,
                status="processing",
                progress=new_state.current_progress,
                message=f"Completed {getattr(event, 'section_name', 'section')}",
                data={
                    "event": event_name,
                    "elements_found": getattr(event, "elements_count", 0),
                },
            )
            return (message, new_state)

        if event_name == "PaperProcessingCompleted":
            new_state = self._progress_state.with_progress(1.0)
            message = ProgressMessage(
                session_id=self.session_id,
                status="completed",
                progress=1.0,
                message="Paper processing completed",
                data={
                    "event": event_name,
                    "total_elements": getattr(event, "total_elements", 0),
                },
            )
            return (message, new_state)

        if event_name == "ExtractionFailed":
            message = ProgressMessage(
                session_id=self.session_id,
                status="failed",
                progress=self._progress_state.current_progress,
                message="Extraction failed",
                data={
                    "event": event_name,
                    "error": str(getattr(event, "error", "Unknown error")),
                },
            )
            return (message, self._progress_state)

        # Return generic progress for other events
        message = ProgressMessage(
            session_id=self.session_id,
            status="processing",
            progress=self._progress_state.current_progress,
            message=f"Processing: {event_name}",
            data={"event": event_name},
        )
        return (message, self._progress_state)


# WebSocket manager will be managed via DI container - no global instance
