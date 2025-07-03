"""
CLI integration tests - ensuring end-to-end functionality.

Tests the complete CLI workflow from PDF input to structured output.
Uses mock LLM provider to avoid API dependencies in testing.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from click.testing import CliRunner

from hci_extractor.cli.commands import cli


class TestCLIIntegration:
    """Test CLI commands with realistic workflow scenarios."""
    
    def test_cli_version_command(self):
        """Test basic CLI functionality with version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['version'])
        
        assert result.exit_code == 0
        assert "HCI Paper Extractor" in result.output
        assert "Python" in result.output
    
    def test_cli_help_shows_all_commands(self):
        """Test that CLI help shows all expected commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "extract" in result.output
        assert "batch" in result.output
        assert "export" in result.output
        assert "parse" in result.output
        assert "validate" in result.output
    
    def test_extract_command_help(self):
        """Test extract command help includes all expected options."""
        runner = CliRunner()
        result = runner.invoke(cli, ['extract', '--help'])
        
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--title" in result.output
        assert "--authors" in result.output
        assert "--venue" in result.output
        assert "--year" in result.output
    
    def test_batch_command_help(self):
        """Test batch command help includes expected options."""
        runner = CliRunner()
        result = runner.invoke(cli, ['batch', '--help'])
        
        assert result.exit_code == 0
        assert "--max-concurrent" in result.output
        assert "--skip-errors" in result.output
        assert "--filter-pattern" in result.output
    
    def test_export_command_help(self):
        """Test export command help includes format options."""
        runner = CliRunner()
        result = runner.invoke(cli, ['export', '--help'])
        
        assert result.exit_code == 0
        assert "--format" in result.output
        assert "csv|json|markdown" in result.output
        assert "--element-type" in result.output
        assert "--min-confidence" in result.output
    
    def test_extract_command_requires_api_key(self):
        """Test that extract command properly checks for API key."""
        runner = CliRunner()
        
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_pdf:
            # Create a minimal PDF file (this will fail PDF extraction, but should fail at API key check first)
            tmp_pdf.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF")
            tmp_pdf.flush()
            
            # Run without GEMINI_API_KEY environment variable
            with patch.dict('os.environ', {}, clear=True):
                result = runner.invoke(cli, ['extract', tmp_pdf.name])
                
                assert result.exit_code != 0
                assert "GEMINI_API_KEY" in result.output
                assert "environment variable is required" in result.output
    
    @patch('hci_extractor.cli.commands.get_llm_provider')
    @patch('hci_extractor.core.analysis.extract_paper_simple')
    def test_extract_command_basic_workflow(self, mock_extract, mock_get_provider):
        """Test extract command with mocked LLM to verify workflow."""
        runner = CliRunner()
        
        # Mock the LLM provider
        mock_provider = AsyncMock()
        mock_get_provider.return_value = mock_provider
        
        # Mock the extraction result
        from hci_extractor.models import Paper, ExtractedElement, ExtractionResult
        from datetime import datetime
        
        mock_paper = Paper.create_with_auto_id(
            title="Test Paper",
            authors=("Dr. Test",)
        )
        
        mock_elements = (
            ExtractedElement.create_with_auto_id(
                paper_id=mock_paper.paper_id,
                element_type="finding",
                text="Users completed tasks 25% faster",
                section="results",
                confidence=0.95,
                evidence_type="quantitative"
            ),
        )
        
        mock_result = ExtractionResult(
            paper=mock_paper,
            elements=mock_elements,
            created_at=datetime.now()
        )
        
        mock_extract.return_value = mock_result
        
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_pdf:
            # Create a basic PDF file
            tmp_pdf.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF")
            tmp_pdf.flush()
            
            with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                result = runner.invoke(cli, ['extract', tmp_pdf.name])
                
                assert result.exit_code == 0
                assert "Initializing LLM provider" in result.output
                # This check is no longer valid as progress is in a different module
                # assert "Processing PDF" in result.output 
                assert "Test Paper" in result.output
                assert "1" in result.output  # Total elements
    
    @patch('hci_extractor.cli.commands.get_llm_provider')
    @patch('hci_extractor.core.analysis.extract_paper_simple')
    def test_extract_command_with_output_file(self, mock_extract, mock_get_provider):
        """Test extract command saves results to JSON file."""
        runner = CliRunner()
        
        # Mock setup
        mock_provider = AsyncMock()
        mock_get_provider.return_value = mock_provider
        
        from hci_extractor.models import Paper, ExtractedElement, ExtractionResult
        from datetime import datetime
        
        mock_paper = Paper.create_with_auto_id(
            title="Test Output Paper",
            authors=("Dr. Output",)
        )
        
        mock_elements = (
            ExtractedElement.create_with_auto_id(
                paper_id=mock_paper.paper_id,
                element_type="claim",
                text="This is a test claim",
                section="introduction",
                confidence=0.85,
                evidence_type="theoretical"
            ),
        )
        
        mock_result = ExtractionResult(
            paper=mock_paper,
            elements=mock_elements,
            created_at=datetime.now()
        )
        
        mock_extract.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            pdf_file = tmp_dir_path / "test.pdf"
            output_file = tmp_dir_path / "results.json"
            
            # Create PDF file
            with open(pdf_file, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF")
            
            with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
                result = runner.invoke(cli, [
                    'extract', str(pdf_file), 
                    '--output', str(output_file)
                ])
                
                assert result.exit_code == 0
                assert "Saving results to" in result.output
                assert "Results saved to" in result.output
                
                # Verify output file was created and contains expected data
                assert output_file.exists()
                
                with open(output_file) as f:
                    data = json.load(f)
                
                assert "paper" in data
                assert "extracted_elements" in data
                assert data["paper"]["title"] == "Test Output Paper"
                assert len(data["extracted_elements"]) == 1
                assert data["extracted_elements"][0]["text"] == "This is a test claim"
    
    def test_export_command_requires_results_directory(self):
        """Test export command validates results directory exists."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['export', '/nonexistent/directory'])
        
        assert result.exit_code != 0
        assert "does not exist" in result.output.lower()
    
    def test_export_csv_format_selection(self):
        """Test export command format selection works."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            
            # Create a mock extraction file
            extraction_file = tmp_dir_path / "test_extraction.json"
            mock_data = {
                "paper": {
                    "title": "Test Paper",
                    "authors": ["Dr. Test"],
                    "venue": "Test Venue",
                    "year": 2024
                },
                "extracted_elements": [
                    {
                        "element_id": "test-id",
                        "element_type": "finding",
                        "text": "Test finding text",
                        "section": "results",
                        "confidence": 0.9,
                        "evidence_type": "quantitative",
                        "page_number": 1
                    }
                ]
            }
            
            with open(extraction_file, "w") as f:
                json.dump(mock_data, f)
            
            # Test CSV export
            result = runner.invoke(cli, [
                'export', str(tmp_dir_path), 
                '--format', 'csv'
            ])
            
            assert result.exit_code == 0
            assert "CSV" in result.output
            assert "Test Paper" in result.output
            assert "Test finding text" in result.output


if __name__ == "__main__":
    pytest.main([__file__])