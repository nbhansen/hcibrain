"""HTTP exception handlers for HCI extractor errors."""

from fastapi import Request
from fastapi.responses import JSONResponse

from hci_extractor.core.models import (
    ConfigurationError,
    DataError,
    LLMError,
    PdfError,
)


async def pdf_error_handler(request: Request, exc: PdfError) -> JSONResponse:
    """
    Handle PDF processing errors.

    Args:
        request: FastAPI request object
        exc: PDF processing exception

    Returns:
        JSON error response with appropriate status code
    """
    # Map specific PDF errors to HTTP status codes
    status_code = 400
    error_type = "pdf_processing_error"

    # You could add more specific error handling here based on PdfError subtypes

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "type": error_type,
        },
    )


async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    """
    Handle LLM processing errors.

    Args:
        request: FastAPI request object
        exc: LLM processing exception

    Returns:
        JSON error response with appropriate status code
    """
    # Map LLM errors to HTTP status codes
    status_code = 500
    error_type = "llm_processing_error"

    # You could add more specific mapping based on LLMError subtypes
    # For example: RateLimitError -> 429, ApiKeyError -> 401

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "type": error_type,
        },
    )


async def configuration_error_handler(
    request: Request, exc: ConfigurationError
) -> JSONResponse:
    """
    Handle configuration errors.

    Args:
        request: FastAPI request object
        exc: Configuration error exception

    Returns:
        JSON error response with appropriate status code
    """
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "type": "configuration_error",
        },
    )


async def data_error_handler(request: Request, exc: DataError) -> JSONResponse:
    """
    Handle data processing errors.

    Args:
        request: FastAPI request object
        exc: Data processing exception

    Returns:
        JSON error response with appropriate status code
    """
    return JSONResponse(
        status_code=422,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "type": "data_processing_error",
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: FastAPI request object
        exc: General exception

    Returns:
        JSON error response with 500 status code
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred during processing",
            "type": "internal_error",
        },
    )
