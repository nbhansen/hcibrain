"""WebSocket progress tracking for long-running operations."""

import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import WebSocket
from pydantic import BaseModel

from hci_extractor.core.events import DomainEvent, EventHandler

logger = logging.getLogger(__name__)


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
            except Exception as e:
                logger.error(f"Error sending progress to {session_id}: {e}")
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
        self.progress = 0.0

    def handle(self, event: DomainEvent) -> None:
        """
        Handle domain event and forward as progress message.

        Args:
            event: Domain event to handle
        """
        try:
            # Map different event types to progress messages
            if (
                hasattr(event, "operation_id")
                and getattr(event, "operation_id") != self.session_id
            ):
                return  # Not for this session

            message = self._map_event_to_progress(event)
            if message:
                # Schedule the async call in the event loop and store reference
                task = asyncio.create_task(self.manager.send_progress(self.session_id, message))
                # Add error handling for the task
                task.add_done_callback(lambda t: logger.error(f"Progress send error: {t.exception()}") if t.exception() else None)

        except Exception as e:
            logger.error(f"Error handling event in WebSocket handler: {e}")

    def _map_event_to_progress(self, event: DomainEvent) -> Optional[ProgressMessage]:
        """
        Map domain event to progress message.

        Args:
            event: Domain event

        Returns:
            Progress message or None if event should be ignored
        """
        event_name = event.__class__.__name__

        # Map specific events to progress
        if event_name == "PaperProcessingStarted":
            return ProgressMessage(
                session_id=self.session_id,
                status="started",
                progress=0.0,
                message="Starting paper processing",
                data={"event": event_name},
            )

        elif event_name == "SectionDetected":
            self.progress = 0.1
            return ProgressMessage(
                session_id=self.session_id,
                status="processing",
                progress=self.progress,
                message="Detected paper sections",
                data={
                    "event": event_name,
                    "sections_found": getattr(event, "sections_count", 0),
                },
            )

        elif event_name == "SectionProcessingStarted":
            return ProgressMessage(
                session_id=self.session_id,
                status="processing",
                progress=self.progress,
                message=f"Processing {getattr(event, 'section_name', 'section')}",
                data={"event": event_name},
            )

        elif event_name == "SectionProcessingCompleted":
            # Update progress based on completed sections
            self.progress = min(0.9, self.progress + 0.15)
            return ProgressMessage(
                session_id=self.session_id,
                status="processing",
                progress=self.progress,
                message=f"Completed {getattr(event, 'section_name', 'section')}",
                data={
                    "event": event_name,
                    "elements_found": getattr(event, "elements_count", 0),
                },
            )

        elif event_name == "PaperProcessingCompleted":
            return ProgressMessage(
                session_id=self.session_id,
                status="completed",
                progress=1.0,
                message="Paper processing completed",
                data={
                    "event": event_name,
                    "total_elements": getattr(event, "total_elements", 0),
                },
            )

        elif event_name == "ExtractionFailed":
            return ProgressMessage(
                session_id=self.session_id,
                status="failed",
                progress=self.progress,
                message="Extraction failed",
                data={
                    "event": event_name,
                    "error": str(getattr(event, "error", "Unknown error")),
                },
            )

        # Return generic progress for other events
        return ProgressMessage(
            session_id=self.session_id,
            status="processing",
            progress=self.progress,
            message=f"Processing: {event_name}",
            data={"event": event_name},
        )


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
