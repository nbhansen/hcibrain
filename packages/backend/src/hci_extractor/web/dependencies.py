"""FastAPI dependencies that bridge to existing DI container."""

from functools import lru_cache

from fastapi import Depends

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.core.di_container import DIContainer, create_configured_container
from hci_extractor.core.events import EventBus
from hci_extractor.core.extraction.pdf_extractor import PdfExtractor
from hci_extractor.core.ports.llm_provider_port import LLMProviderPort
from hci_extractor.web.progress import WebSocketManager


@lru_cache
def get_container() -> DIContainer:
    """
    Get the configured DI container.

    Uses LRU cache to ensure we use the same container instance
    across the FastAPI application lifecycle.

    Returns:
        Configured DIContainer with all services registered
    """
    return create_configured_container()


def get_extractor_config(
    container: DIContainer = Depends(get_container),
) -> ExtractorConfig:
    """
    FastAPI dependency that resolves ExtractorConfig from DI container.

    Args:
        container: DI container instance

    Returns:
        Immutable ExtractorConfig object
    """
    return container.resolve(ExtractorConfig)


def get_llm_provider(
    container: DIContainer = Depends(get_container),
) -> LLMProviderPort:
    """
    FastAPI dependency that resolves LLMProvider from DI container.

    Args:
        container: DI container instance

    Returns:
        Configured LLM provider instance
    """
    return container.resolve(LLMProviderPort)


def get_event_bus(container: DIContainer = Depends(get_container)) -> EventBus:
    """
    FastAPI dependency that resolves EventBus from DI container.

    Args:
        container: DI container instance

    Returns:
        EventBus instance for publishing domain events
    """
    return container.resolve(EventBus)


def get_websocket_manager(
    container: DIContainer = Depends(get_container),
) -> WebSocketManager:
    """
    FastAPI dependency that resolves WebSocketManager from DI container.

    Args:
        container: DI container instance

    Returns:
        WebSocketManager instance for WebSocket connections
    """
    return container.resolve(WebSocketManager)


def get_pdf_extractor(
    container: DIContainer = Depends(get_container),
) -> PdfExtractor:
    """
    FastAPI dependency that resolves PdfExtractor from DI container.

    Args:
        container: DI container instance

    Returns:
        PdfExtractor instance for extracting content from PDF files
    """
    return container.resolve(PdfExtractor)
