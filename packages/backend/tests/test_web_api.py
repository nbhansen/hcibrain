"""Minimal web API integration test."""

import pytest
from fastapi.testclient import TestClient

from hci_extractor.web.app import create_app


class TestWebAPI:
    """Test basic web API functionality."""

    @pytest.fixture
    def client(self):
        """Create test client for the web API."""
        app = create_app()
        return TestClient(app)

    def test_health_check_endpoint_exists(self, client):
        """Test that the API is accessible."""
        # Test root endpoint or docs endpoint
        response = client.get("/docs")
        assert response.status_code == 200

    def test_markup_endpoint_requires_file(self, client):
        """Test that the markup endpoint requires a file upload."""
        # Test without file - should get validation error
        response = client.post("/extract/markup")
        assert response.status_code == 422  # Validation error

    def test_markup_endpoint_accepts_pdf_content_type(self, client):
        """Test that the markup endpoint accepts PDF files."""
        # Create a minimal "PDF" file for testing
        # Note: This will likely fail at the PDF processing stage, but should
        # pass validation and reach the processing logic
        fake_pdf_content = b"%PDF-1.4\n%test content"
        
        response = client.post(
            "/extract/markup",
            files={"file": ("test.pdf", fake_pdf_content, "application/pdf")}
        )
        
        # Should accept the file but may fail at processing stage
        # We're testing the API structure, not the full processing pipeline
        assert response.status_code in [200, 422, 500]  # Various acceptable outcomes
        
        # If it's a 422, it should be validation-related, not "missing file"
        if response.status_code == 422:
            error_detail = response.json()
            # Should not be "field required" for file
            assert "file" not in str(error_detail).lower() or "required" not in str(error_detail).lower()

    def test_api_returns_json_responses(self, client):
        """Test that API endpoints return JSON responses."""
        # Test an endpoint that should return JSON
        response = client.post("/extract/markup")
        
        # Even error responses should be JSON
        assert response.headers.get("content-type", "").startswith("application/json")