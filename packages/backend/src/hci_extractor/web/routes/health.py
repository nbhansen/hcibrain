"""Health check and system information endpoints."""

from typing import Any

from fastapi import APIRouter, Depends

from hci_extractor.core.config import ExtractorConfig
from hci_extractor.web.dependencies import get_extractor_config

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Basic health check endpoint.

    Returns:
        Health status information
    """
    return {"status": "healthy", "service": "hci-extractor-api"}


@router.get("/config")
async def get_config_info(
    config: ExtractorConfig = Depends(get_extractor_config),
) -> dict[str, Any]:
    """
    Get system configuration information (sanitized).

    Args:
        config: Injected ExtractorConfig

    Returns:
        Non-sensitive configuration information
    """
    return {
        "analysis": {
            "chunk_size": config.analysis.chunk_size,
            "max_concurrent_sections": config.analysis.max_concurrent_sections,
            "model_name": config.analysis.model_name,
            "temperature": config.analysis.temperature,
        },
        "extraction": {
            "max_file_size_mb": config.extraction.max_file_size_mb,
            "timeout_seconds": config.extraction.timeout_seconds,
        },
        "retry": {
            "max_attempts": config.retry.max_attempts,
        },
    }
