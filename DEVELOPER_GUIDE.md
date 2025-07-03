# HCI Paper Extractor - Developer Guide

This guide provides comprehensive information for developers working on the HCI Paper Extractor project.

## Table of Contents

1. [Project Architecture](#project-architecture)
2. [Development Setup](#development-setup)
3. [Code Organization](#code-organization)
4. [Testing](#testing)
5. [Type Safety](#type-safety)
6. [Contributing](#contributing)
7. [API Reference](#api-reference)

## Project Architecture

The HCI Paper Extractor follows a clean, layered architecture with clear separation of concerns:

```
src/hci_extractor/
├── core/              # Business logic (no CLI dependencies)
│   ├── models/        # Data models and exceptions
│   ├── extraction/    # PDF processing
│   └── analysis/      # LLM analysis pipeline
├── providers/         # LLM provider implementations
├── cli/              # Command-line interface
└── utils/            # Shared utilities (logging, config)
```

### Key Principles

1. **Immutable Data Models**: All data structures use `@dataclass(frozen=True)` for thread safety and predictability
2. **Dependency Injection**: LLM providers are injected, not hardcoded
3. **Clean Architecture**: Core business logic has no knowledge of CLI or external APIs
4. **Type Safety**: Full type annotations throughout the codebase
5. **Error Handling**: Graceful degradation with proper error types

## Development Setup

### Prerequisites

- Python 3.9+
- Virtual environment
- Gemini API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd hci-paper-extractor

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Set up environment variables
echo "GEMINI_API_KEY=your-api-key" > .env
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test modules
python -m pytest tests/test_models.py -v
python -m pytest tests/test_pipeline.py -v

# Run with coverage
python -m pytest tests/ --cov=hci_extractor --cov-report=html
```

### Code Quality Tools

```bash
# Type checking
mypy src/

# Code formatting
black src/ tests/

# Linting
ruff check src/

# All quality checks
make quality  # If Makefile is available
```

## Code Organization

### Core Module (`hci_extractor/core/`)

#### Models (`core/models/`)
- **Data Models**: `Paper`, `ExtractedElement`, `DetectedSection`, `ExtractionResult`
- **PDF Models**: `PdfContent`, `PdfPage`, `PdfMetadata`
- **Exceptions**: `PdfError`, `LLMError`, `LLMValidationError`, `ProcessingError`

All models are immutable and use factory methods for creation:

```python
# Example: Creating a paper
paper = Paper.create_with_auto_id(
    title="Example Paper",
    authors=("Author 1", "Author 2"),
    venue="CHI 2024"
)
```

#### Extraction (`core/extraction/`)
- **PdfExtractor**: Handles PDF text extraction using PyMuPDF
- **TextNormalizer**: Cleans and normalizes extracted text

```python
# Example: Extracting PDF content
extractor = PdfExtractor()
pdf_content = extractor.extract_content("paper.pdf")
```

#### Analysis (`core/analysis/`)
- **SectionDetector**: Identifies paper sections (abstract, intro, etc.)
- **SectionProcessor**: Abstract interface for processing sections
- **LLMSectionProcessor**: Concrete implementation using LLM providers
- **SimpleValidator**: Validates extracted elements for verbatim accuracy

```python
# Example: Processing sections
sections = detect_sections(pdf_content)
processor = LLMSectionProcessor(llm_provider=gemini)
elements = await process_sections_batch(sections, paper, processor)
```

### Providers Module (`hci_extractor/providers/`)

- **Base Provider**: Abstract `LLMProvider` class defining the interface
- **GeminiProvider**: Google Gemini API implementation
- Future: OpenAI, Anthropic, local model providers

```python
# Example: Using a provider
provider = GeminiProvider(api_key="your-key")
elements = await provider.analyze_section(
    section_text="...",
    section_type="results",
    context={"paper_title": "..."}
)
```

### CLI Module (`hci_extractor/cli/`)

- **Commands**: All CLI commands (extract, batch, export, validate, etc.)
- **Progress**: Rich progress bars and status tracking
- **Main**: Entry point and command group setup

### Utils Module (`hci_extractor/utils/`)

- **Logging**: Centralized logging configuration
- **Config**: Environment and settings management

## Testing

### Test Structure

```
tests/
├── test_models.py                    # Data model tests
├── test_pipeline.py                  # Pipeline integration tests
├── test_llm.py                      # LLM provider tests
├── test_simple_extraction.py        # End-to-end extraction tests
├── test_verbatim_validation.py      # Academic integrity tests
├── test_classification_precision.py  # Classification accuracy tests
└── test_cli_integration.py          # CLI command tests
```

### Writing Tests

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows

Example test pattern:

```python
@pytest.mark.asyncio
async def test_extraction_workflow():
    # Arrange
    mock_llm = AsyncMock()
    mock_llm.analyze_section.return_value = [...]
    
    # Act
    result = await extract_paper_simple(
        "test.pdf",
        llm_provider=mock_llm
    )
    
    # Assert
    assert len(result.elements) > 0
    assert all(e.text in pdf_text for e in result.elements)
```

## Type Safety

The project uses comprehensive type annotations:

- All functions have typed parameters and return types
- Complex types use `typing` module constructs
- Mypy runs with strict settings

Example:

```python
from typing import Tuple, Optional, Dict, Any

async def process_section(
    self,
    section: DetectedSection,
    paper: Paper,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[ExtractedElement, ...]:
    """Process a section to extract academic elements."""
    ...
```

## Contributing

### Code Style

- Follow PEP 8 with Black formatting
- Use descriptive variable names
- Add docstrings to all public functions/classes
- Keep functions focused and small

### Commit Messages

Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with tests
3. Run all quality checks (`pytest`, `mypy`, `black`, `ruff`)
4. Update documentation if needed
5. Submit PR with clear description

## API Reference

### Core Functions

#### `extract_paper_simple`

```python
async def extract_paper_simple(
    pdf_path: str,
    llm_provider: Optional[LLMProvider] = None,
    paper_metadata: Optional[Dict[str, Any]] = None
) -> ExtractionResult:
    """
    Extract academic elements from a PDF paper.
    
    Args:
        pdf_path: Path to PDF file
        llm_provider: Optional LLM provider (defaults to Gemini)
        paper_metadata: Optional metadata (title, authors, etc.)
        
    Returns:
        ExtractionResult with paper info and extracted elements
    """
```

#### `process_sections_batch`

```python
async def process_sections_batch(
    sections: Tuple[DetectedSection, ...],
    paper: Paper,
    processor: SectionProcessor,
    context: Optional[Dict[str, Any]] = None,
    max_concurrent: int = 3
) -> Tuple[ExtractedElement, ...]:
    """
    Process multiple sections concurrently.
    
    Args:
        sections: Detected sections to process
        paper: Paper metadata
        processor: Section processor implementation
        context: Optional processing context
        max_concurrent: Max concurrent operations
        
    Returns:
        Tuple of all extracted elements
    """
```

### Data Models

#### `Paper`

```python
@dataclass(frozen=True)
class Paper:
    paper_id: str
    title: str
    authors: Tuple[str, ...]
    venue: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    file_path: str = ""
```

#### `ExtractedElement`

```python
@dataclass(frozen=True)
class ExtractedElement:
    element_id: str
    paper_id: str
    element_type: Literal["claim", "finding", "method", "artifact"]
    text: str
    section: str
    confidence: float
    evidence_type: Literal["quantitative", "qualitative", "theoretical", "unknown"]
    page_number: Optional[int] = None
```

### CLI Commands

#### Extract Command

```bash
python -m hci_extractor extract <pdf_file> [options]

Options:
  --output PATH         Output file (format auto-detected from extension)
  --title TEXT         Paper title
  --authors TEXT       Comma-separated author names
  --venue TEXT         Publication venue
  --year INTEGER       Publication year
```

#### Batch Command

```bash
python -m hci_extractor batch <input_dir> <output_dir> [options]

Options:
  --max-concurrent INT  Max concurrent extractions (default: 3)
  --filter TEXT        File pattern filter (default: *.pdf)
  --skip-errors        Continue on errors
```

#### Export Command

```bash
python -m hci_extractor export <results_dir> [options]

Options:
  --format TEXT        Output format (csv, json, markdown)
  --output PATH        Output file path
  --min-confidence     Minimum confidence threshold
  --element-type       Filter by element type
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **API Key Issues**: Check `.env` file and environment variables
3. **Type Errors**: Run `mypy src/` to catch type issues
4. **Test Failures**: Check test fixtures and mock data

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:

```bash
export HCI_EXTRACTOR_LOG_LEVEL=DEBUG
```

---

For more information, see the [README](README.md) and [CLAUDE.md](CLAUDE.md) files.