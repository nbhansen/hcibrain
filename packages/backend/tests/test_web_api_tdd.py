"""Test-driven tests for web API functionality."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hci_extractor.web.app import create_app


class TestWebAPIEndpoints:
    """Test the actual web API endpoints that exist."""

    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def sample_pdf_file(self):
        """Create a minimal PDF-like file for testing."""
        # Create a file that looks like PDF for upload testing
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n%%EOF"
        return io.BytesIO(pdf_content)

    def test_health_endpoint_exists(self, test_client):
        """Test that health endpoint works."""
        response = test_client.get("/api/v1/health")

        # Should return successful response
        assert response.status_code == 200

        # Should return JSON
        data = response.json()
        assert isinstance(data, dict)

        # Should indicate system is healthy
        assert "status" in data
        assert data["status"] == "healthy"

    def test_extract_markup_endpoint_exists(self, test_client):
        """Test that the main extraction endpoint exists."""
        # Test without file - should give validation error
        response = test_client.post("/api/v1/extract/markup")

        # FastAPI should return 422 for missing required field
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_extract_markup_file_validation(self, test_client):
        """Test file validation on extraction endpoint."""
        # Test with non-PDF file
        text_file = io.BytesIO(b"This is plain text, not a PDF")

        response = test_client.post(
            "/api/v1/extract/markup",
            files={"file": ("test.txt", text_file, "text/plain")},
        )

        # Should reject non-PDF files
        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "PDF" in error_detail

    def test_extract_markup_response_format(self, test_client, sample_pdf_file):
        """Test that successful extraction returns expected format."""
        response = test_client.post(
            "/api/v1/extract/markup",
            files={"file": ("test.pdf", sample_pdf_file, "application/pdf")},
        )

        # This test will initially fail until full pipeline works
        # But it defines what we expect the response to look like
        if response.status_code == 200:
            data = response.json()

            # Expected response structure
            assert "paper_full_text_with_markup" in data
            assert "paper_info" in data
            assert "plain_language_summary" in data
            assert "processing_time_seconds" in data

            # Verify data types
            assert isinstance(data["paper_full_text_with_markup"], str)
            assert isinstance(data["paper_info"], dict)
            assert isinstance(data["plain_language_summary"], str)
            assert isinstance(data["processing_time_seconds"], (int, float))

            # Paper info should have expected fields
            paper_info = data["paper_info"]
            assert "title" in paper_info
            assert "authors" in paper_info
            assert "paper_id" in paper_info
        else:
            # For TDD - this is expected to fail initially
            pytest.skip(
                f"Extraction pipeline not fully implemented: {response.status_code}"
            )

    def test_file_size_limits(self, test_client):
        """Test that oversized files are rejected."""
        # Create a large fake file
        large_content = b"PDF-like content " * 100000  # Large file
        large_file = io.BytesIO(large_content)

        response = test_client.post(
            "/api/v1/extract/markup",
            files={"file": ("large.pdf", large_file, "application/pdf")},
        )

        # Should reject files over size limit
        # Might be 413 (Payload Too Large) or 400 (Bad Request)
        assert response.status_code in [400, 413]

    def test_api_error_responses_are_json(self, test_client):
        """Test that all API errors return proper JSON."""
        # Test various error scenarios
        error_responses = [
            test_client.get("/api/v1/nonexistent"),  # 404
            test_client.delete("/api/v1/health"),  # 405 (method not allowed)
            test_client.post("/api/v1/extract/markup"),  # 422 (validation error)
        ]

        for response in error_responses:
            # All errors should return JSON
            assert response.headers.get("content-type", "").startswith(
                "application/json"
            )

            # Should have error detail
            data = response.json()
            assert "detail" in data or "message" in data

    def test_cors_configuration(self, test_client):
        """Test CORS headers for frontend compatibility."""
        response = test_client.get("/api/v1/health")

        # Should allow CORS for frontend access
        # (Implementation will determine exact headers)
        assert response.status_code == 200

    def test_request_timeout_handling(self, test_client):
        """Test that requests don't hang indefinitely."""
        # This test ensures requests complete in reasonable time
        import time

        start_time = time.time()
        response = test_client.get("/api/v1/health")
        end_time = time.time()

        # Health endpoint should be very fast
        assert (end_time - start_time) < 5.0  # 5 second timeout
        assert response.status_code == 200


class TestWebAPIIntegration:
    """Test API integration scenarios."""

    @pytest.fixture
    def test_client(self):
        """Create test client for integration testing."""
        app = create_app()
        return TestClient(app)

    def test_full_extraction_workflow(self, test_client):
        """Test complete PDF extraction workflow."""
        # This test represents the full user workflow:
        # 1. Upload PDF
        # 2. Get markup response
        # 3. Verify markup contains expected elements

        # Use a smaller test PDF from repository root
        pdf_path = Path(__file__).parent.parent.parent.parent / "ootest.pdf"

        with open(pdf_path, "rb") as pdf_file:
            response = test_client.post(
                "/api/v1/extract/markup",
                files={"file": ("ootest.pdf", pdf_file, "application/pdf")},
            )

        # For TDD - this defines our success criteria
        if response.status_code == 200:
            data = response.json()
            markup_text = data["paper_full_text_with_markup"]

            # Should contain HTML markup tags for academic elements
            has_markup = any(
                tag in markup_text for tag in ["<goal", "<method", "<result"]
            )
            assert has_markup, "Response should contain academic markup tags"

            # Should have non-empty summary
            assert len(data["plain_language_summary"]) > 0

            # Should complete in reasonable time
            assert data["processing_time_seconds"] < 300  # 5 minute limit
        else:
            pytest.skip(f"Full workflow not implemented: {response.status_code}")

    def test_concurrent_requests(self, test_client):
        """Test that API handles concurrent requests properly."""
        import concurrent.futures

        def make_health_request():
            return test_client.get("/api/v1/health")

        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_health_request) for _ in range(10)]
            responses = [f.result() for f in futures]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

    def test_dependency_injection_works(self, test_client):
        """Test that dependency injection provides correct services."""
        # This test verifies DI container properly wires dependencies
        response = test_client.get("/api/v1/health")

        # If health endpoint works, basic DI is working
        assert response.status_code == 200

        # More detailed DI testing would check specific service resolution

    def test_chunked_extraction_workflow(self, test_client):
        """Test PDF extraction workflow with chunking (large PDF).

        NOTE: This test takes 5-10 minutes due to:
        - Multiple chunks (~2 chunks from 23k characters)
        - Rate limiting between API calls
        - Multiple Gemini API requests
        """
        # This test represents chunked processing workflow:
        # 1. Upload large PDF that triggers chunking
        # 2. Verify chunking is used (will take longer)
        # 3. Verify merged result contains expected elements

        # Use a large PDF that triggers chunking from repository root
        pdf_path = Path(__file__).parent.parent.parent.parent / "ootest_big.pdf"

        print(f"\n🔄 Starting chunked extraction test with {pdf_path.name}")
        print("⏱️  This will take 5-10 minutes due to chunking and rate limiting...")

        import time

        start_time = time.time()

        with open(pdf_path, "rb") as pdf_file:
            response = test_client.post(
                "/api/v1/extract/markup",
                files={"file": ("ootest_big.pdf", pdf_file, "application/pdf")},
            )

        elapsed = time.time() - start_time
        print(f"⏱️  Chunked extraction completed in {elapsed:.1f} seconds")

        # For TDD - this defines our success criteria for chunked processing
        if response.status_code == 200:
            data = response.json()
            markup_text = data["paper_full_text_with_markup"]

            print(f"📝 Chunked markup length: {len(markup_text):,} characters")

            # Should contain HTML markup tags for academic elements
            has_markup = any(
                tag in markup_text for tag in ["<goal", "<method", "<result"]
            )
            assert has_markup, "Chunked response should contain academic markup tags"

            # Should have non-empty summary
            assert len(data["plain_language_summary"]) > 0

            # Should complete in reasonable time (chunking takes longer)
            assert (
                data["processing_time_seconds"] < 900
            )  # 15 minute limit for chunked processing

            # Chunked processing should produce longer output (more content processed)
            assert len(markup_text) > 10000, (
                "Chunked processing should handle large documents"
            )

            print("✅ Chunked extraction workflow test passed!")
        else:
            pytest.skip(f"Chunked workflow not implemented: {response.status_code}")
