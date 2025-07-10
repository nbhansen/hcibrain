"""WebSocket endpoints for real-time progress tracking."""

import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from hci_extractor.core.events import EventBus
from hci_extractor.web.dependencies import get_event_bus, get_websocket_manager
from hci_extractor.web.progress import WebSocketManager, WebSocketProgressHandler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/progress/{session_id}")
async def progress_websocket(
    websocket: WebSocket,
    session_id: str,
    event_bus: EventBus = Depends(get_event_bus),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager),
) -> None:
    """
    WebSocket endpoint for real-time progress tracking.

    Args:
        websocket: WebSocket connection
        session_id: Unique session identifier for tracking
        event_bus: Event bus for subscribing to domain events
    """
    # Connect to WebSocket manager
    await websocket_manager.connect(websocket, session_id)

    # Create progress handler for this session
    progress_handler = WebSocketProgressHandler(websocket_manager, session_id)

    # Subscribe to all events (handler will filter by session)
    event_bus.subscribe_all(progress_handler)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for messages from client (heartbeat, etc.)
            try:
                data = await websocket.receive_text()
                logger.debug(
                    f"Received WebSocket message for session {session_id}: {data}",
                )

                # Handle client messages if needed
                if data == "ping":
                    await websocket.send_text("pong")

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except Exception:
                logger.exception(f"Error in WebSocket loop for session {session_id}")
                break

    finally:
        # Clean up
        websocket_manager.disconnect(session_id)
        # Note: EventBus should handle unsubscribing automatically


@router.get("/sessions/new")
async def create_session(
    websocket_manager: WebSocketManager = Depends(get_websocket_manager),
) -> dict[str, str]:
    """
    Create a new session ID for progress tracking.

    Returns:
        New session ID that can be used for WebSocket connection
    """
    session_id = websocket_manager.create_session_id()
    return {"session_id": session_id}
