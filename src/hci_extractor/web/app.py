"""FastAPI application setup."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from hci_extractor.core.models import (
    ConfigurationError,
    DataError,
    LLMError,
    PdfError,
)
from hci_extractor.web.exceptions import (
    configuration_error_handler,
    data_error_handler,
    general_exception_handler,
    llm_error_handler,
    pdf_error_handler,
)
from hci_extractor.web.routes import extract, health, websocket


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="HCI Paper Extractor API",
        description="Extract structured content from HCI academic papers",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware for frontend development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handlers
    app.add_exception_handler(PdfError, pdf_error_handler)
    app.add_exception_handler(LLMError, llm_error_handler)
    app.add_exception_handler(ConfigurationError, configuration_error_handler)
    app.add_exception_handler(DataError, data_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(extract.router, prefix="/api/v1", tags=["extraction"])
    app.include_router(websocket.router, prefix="/api/v1", tags=["progress"])

    # Mount static files
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Serve the main UI page at root
    @app.get("/", include_in_schema=False)
    async def root():
        """Serve the main UI page."""
        index_path = static_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        else:
            # Fallback to API docs if UI not available
            return RedirectResponse(url="/docs")

    return app


# Create the application instance
app = create_app()
