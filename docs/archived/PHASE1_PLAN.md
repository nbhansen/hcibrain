# Phase 1: PDF Processing Foundation - Detailed Implementation Plan

## Overview
Phase 1 establishes the foundation for extracting and structuring text from academic PDFs while maintaining verbatim accuracy and implementing immutable design principles.

**Duration**: 5 days  
**Goal**: Reliable text extraction and section identification from HCI academic papers  
**Success Criteria**: 90% success rate on typical academic PDFs with <5 second processing time

---

## Step 1: Project Structure & Dependencies
**Timeline**: Day 1 (2-3 hours)  
**Priority**: Critical Foundation

### Tasks Breakdown
- [ ] Create directory structure matching design document specification
- [ ] Initialize Python package with proper `__init__.py` files
- [ ] Configure `requirements.txt` with core dependencies
- [ ] Set up development tooling (black, mypy, ruff, pytest)
- [ ] Create `.env.example` and `.gitignore`
- [ ] Configure basic logging framework
- [ ] Set up virtual environment documentation

### Dependencies to Add
```txt
# Core functionality
pymupdf>=1.23.0              # PDF text extraction
pydantic>=2.0.0              # Data validation and immutable models
click>=8.0.0                 # CLI framework
python-dotenv>=1.0.0         # Environment management

# Development tools
pytest>=7.0.0                # Testing framework
black>=23.0.0                # Code formatting
mypy>=1.0.0                  # Type checking
ruff>=0.1.0                  # Fast linting
pytest-cov>=4.0.0           # Coverage reporting
```

### Directory Structure to Create
```
hci-paper-extractor/
├── src/
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py      # PDF to text conversion
│   │   └── section_parser.py     # Identify paper sections
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Immutable data models
│   ├── storage/
│   │   ├── __init__.py
│   │   └── json_store.py       # Simple JSON persistence
│   └── main.py                  # CLI entry point
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── conftest.py
├── data/                        # Input PDFs
├── output/                      # Extracted results
├── requirements.txt
├── .env.example
├── .gitignore
├── pyproject.toml              # Modern Python config
└── README.md
```

**Deliverable**: Clean, importable project structure with development environment ready

---

## Step 2: Core PDF Text Extraction
**Timeline**: Day 1-2 (4-5 hours)  
**Priority**: Critical - Foundation for all other work

### Tasks Breakdown
- [ ] Implement `PdfExtractor` class with PyMuPDF integration
- [ ] Design immutable `PdfPage` and `PdfContent` dataclasses
- [ ] Add page-by-page text extraction with character positioning
- [ ] Handle basic PDF issues (password protection, corruption)
- [ ] Implement text normalization while preserving verbatim tracking
- [ ] Add extraction metadata (file info, processing time, page count)

### Key Data Models
```python
@dataclass(frozen=True)
class PdfPage:
    page_number: int
    text: str
    char_count: int
    bbox_data: Optional[dict] = None  # Character positioning for verbatim validation

@dataclass(frozen=True)
class PdfContent:
    file_path: str
    total_pages: int
    pages: tuple[PdfPage, ...]
    extraction_metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def full_text(self) -> str:
        return "\n".join(page.text for page in self.pages)
```

### Implementation Strategy
1. **Basic Extraction**: Start with simple text extraction using `fitz.open()`
2. **Character Tracking**: Preserve character positions for verbatim validation
3. **Error Handling**: Graceful failure for problematic PDFs
4. **Memory Management**: Process page-by-page to handle large files
5. **Validation**: Ensure extracted text is actually extractable

### Error Scenarios to Handle
- Password-protected PDFs
- Corrupted/unreadable files
- Scanned images (no text layer)
- Empty or very short documents
- Extremely large files (>100MB)

**Deliverable**: `extract_pdf_content(file_path: Path) -> PdfContent` function with comprehensive error handling

---

## Step 3: Section Detection Patterns
**Timeline**: Day 2 (3-4 hours)  
**Priority**: High - Required for structured extraction

### Tasks Breakdown
- [ ] Research HCI paper section patterns through sample analysis
- [ ] Create comprehensive regex pattern dictionary
- [ ] Handle numbering variations (1., I., (1), etc.)
- [ ] Account for case insensitivity and spacing variations
- [ ] Add support for subsections and nested headers
- [ ] Test patterns against diverse academic paper samples

### Pattern Categories to Support
```python
SECTION_PATTERNS = {
    "abstract": [
        r"(?i)^\s*abstract\s*$",
        r"(?i)^\s*summary\s*$",
        r"(?i)^\s*overview\s*$"
    ],
    "introduction": [
        r"(?i)^\s*(1\.?\s*)?introduction\s*$",
        r"(?i)^\s*i\.?\s*introduction\s*$",
        r"(?i)^\s*\(1\)\s*introduction\s*$"
    ],
    "related_work": [
        r"(?i)^\s*(2\.?\s*)?(related work|background|literature review|prior work|previous work)\s*$",
        r"(?i)^\s*ii\.?\s*(related work|background)\s*$"
    ],
    "methodology": [
        r"(?i)^\s*(3\.?\s*)?(method|methodology|approach|design|procedure)\s*$",
        r"(?i)^\s*(experimental design|study design|research method)\s*$"
    ],
    "results": [
        r"(?i)^\s*(4\.?\s*)?(results|findings|analysis|evaluation)\s*$",
        r"(?i)^\s*(experimental results|study results)\s*$"
    ],
    "discussion": [
        r"(?i)^\s*(5\.?\s*)?(discussion|implications|interpretation)\s*$",
        r"(?i)^\s*(discussion and implications|discussion of results)\s*$"
    ],
    "conclusion": [
        r"(?i)^\s*(6\.?\s*)?(conclusion|conclusions|summary|final remarks)\s*$",
        r"(?i)^\s*(concluding remarks|future work)\s*$"
    ],
    "references": [
        r"(?i)^\s*references\s*$",
        r"(?i)^\s*bibliography\s*$",
        r"(?i)^\s*works cited\s*$"
    ]
}
```

### Special Cases to Handle
- **Multi-word sections**: "User Study", "Experimental Design"
- **Combined sections**: "Results and Discussion"
- **Numbered subsections**: "3.1 Participants", "3.2 Procedure"
- **Alternative names**: "Evaluation" vs "Results", "Background" vs "Related Work"

**Deliverable**: Comprehensive pattern dictionary with confidence scoring and test coverage

---

## Step 4: Section Parser Core Logic
**Timeline**: Day 2-3 (4-5 hours)  
**Priority**: High - Core functionality for structured extraction

### Tasks Breakdown
- [ ] Design immutable `Section` dataclass with positioning metadata
- [ ] Implement pattern matching with confidence scoring
- [ ] Handle overlapping matches and ambiguous sections
- [ ] Preserve exact text boundaries for verbatim validation
- [ ] Add fallback logic for papers with unusual structures
- [ ] Implement section ordering validation

### Core Implementation
```python
@dataclass(frozen=True)
class Section:
    name: str
    text: str
    start_page: int
    end_page: int
    confidence: float
    start_char_index: int
    end_char_index: int
    pattern_matched: str
    
    def __post_init__(self):
        """Validate section data integrity"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.start_char_index > self.end_char_index:
            raise ValueError("Invalid character indices")

def parse_sections(pdf_content: PdfContent) -> tuple[Section, ...]:
    """
    Parse PDF content into academic paper sections.
    
    Returns tuple of sections in document order with confidence scores.
    """
    # Implementation here
    pass
```

### Algorithm Strategy
1. **Line-by-line scanning**: Look for section header patterns
2. **Confidence scoring**: Multiple factors (pattern strength, position, length)
3. **Boundary detection**: Find where each section ends
4. **Validation**: Ensure logical section ordering
5. **Fallback handling**: What to do when sections aren't found

### Confidence Scoring Factors
- **Pattern strength**: Exact match = 1.0, fuzzy match = 0.7-0.9
- **Position appropriateness**: Introduction near beginning = higher score
- **Length reasonableness**: Sections shouldn't be too short/long
- **Ordering logic**: Results shouldn't come before methods

**Deliverable**: `parse_sections()` function returning immutable Section tuple with >85% accuracy on test papers

---

## Step 5: Text Cleaning & Normalization
**Timeline**: Day 3 (3-4 hours)  
**Priority**: Medium-High - Required for LLM processing quality

### Tasks Breakdown
- [ ] Identify common PDF extraction artifacts in academic papers
- [ ] Implement reversible text cleaning pipeline
- [ ] Preserve academic formatting (citations, equations, symbols)
- [ ] Handle multi-column layouts and reading order
- [ ] Remove headers/footers while preserving content
- [ ] Create transformation tracking for verbatim validation

### Common Issues to Address
- **Broken words**: "eval- uation" → "evaluation"
- **Excessive whitespace**: Multiple spaces, irregular line breaks
- **Header/footer repetition**: Page numbers, journal names
- **Column merging**: Left column + right column text mixed
- **Special characters**: Unicode issues, mathematical symbols
- **Citation formatting**: "[1, 2, 3]" vs "1,2,3" vs "(Smith et al., 2023)"

### Cleaning Pipeline Design
```python
@dataclass(frozen=True)
class TextTransformation:
    original_text: str
    cleaned_text: str
    transformations_applied: tuple[str, ...]
    char_mapping: dict[int, int]  # Original pos -> cleaned pos

def clean_text_pipeline(raw_text: str) -> TextTransformation:
    """
    Apply cleaning transformations while maintaining verbatim traceability.
    """
    # Implementation tracks every change for reversal
    pass
```

### Critical Requirement
**Reversibility**: Every cleaning operation must be traceable back to original text positions for verbatim validation in later phases.

**Deliverable**: Text cleaning pipeline that improves LLM processing while maintaining verbatim validation capability

---

## Step 6: Immutable Data Integration
**Timeline**: Day 3-4 (3 hours)  
**Priority**: Medium - Architecture compliance

### Tasks Breakdown
- [ ] Audit all dataclasses for proper `@dataclass(frozen=True)` usage
- [ ] Convert all `List` types to `tuple` in data structures
- [ ] Implement builder patterns for complex object construction
- [ ] Add validation methods that return new objects
- [ ] Create utility functions for common data transformations
- [ ] Ensure thread safety through immutability

### Immutability Checklist
```python
# ✅ Correct immutable design
@dataclass(frozen=True)
class ExampleModel:
    items: tuple[str, ...]  # Not List[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_item(self, item: str) -> 'ExampleModel':
        """Return new instance with added item"""
        return ExampleModel(
            items=self.items + (item,),
            metadata=self.metadata
        )

# ❌ Mutable design to avoid
@dataclass
class BadExample:
    items: List[str]  # Mutable!
    
    def add_item(self, item: str) -> None:
        self.items.append(item)  # Modifies existing object!
```

### Builder Pattern Implementation
For complex objects requiring multiple steps to construct:
```python
class SectionBuilder:
    def __init__(self):
        self._name: Optional[str] = None
        self._text: Optional[str] = None
        # ... other fields
    
    def with_name(self, name: str) -> 'SectionBuilder':
        new_builder = SectionBuilder()
        new_builder._name = name
        return new_builder
    
    def build(self) -> Section:
        if not all([self._name, self._text]):
            raise ValueError("Missing required fields")
        return Section(name=self._name, text=self._text, ...)
```

**Deliverable**: Fully immutable data pipeline with type safety and thread safety guarantees

---

## Step 7: Error Handling & Resilience
**Timeline**: Day 4 (2-3 hours)  
**Priority**: High - Production readiness

### Tasks Breakdown
- [ ] Define comprehensive error hierarchy for PDF processing
- [ ] Implement graceful handling of problematic PDFs
- [ ] Add detailed logging with context for debugging
- [ ] Create user-friendly error messages
- [ ] Add retry logic for transient failures
- [ ] Implement fallback strategies where possible

### Error Categories
```python
class PdfProcessingError(Exception):
    """Base exception for PDF processing issues"""
    pass

class PdfExtractionError(PdfProcessingError):
    """PDF file cannot be opened or read"""
    pass

class SectionParsingError(PdfProcessingError):
    """Text extracted but sections cannot be identified"""
    pass

class TextNormalizationError(PdfProcessingError):
    """Issues during text cleaning process"""
    pass

class ValidationError(PdfProcessingError):
    """Extracted data doesn't meet quality thresholds"""
    pass
```

### Scenarios to Handle Gracefully
- **Password-protected PDFs**: Detect and skip with clear message
- **Corrupted files**: Catch PyMuPDF errors and provide context
- **Scanned images**: Detect lack of text layer and suggest OCR
- **Memory issues**: Handle large files with streaming or chunking
- **Network timeouts**: If processing remote URLs
- **Permission errors**: File system access issues

### Logging Strategy
```python
import logging

logger = logging.getLogger(__name__)

def extract_with_logging(pdf_path: Path) -> PdfContent:
    logger.info(f"Starting extraction for {pdf_path}")
    try:
        result = extract_pdf_content(pdf_path)
        logger.info(f"Successfully extracted {len(result.pages)} pages")
        return result
    except PdfExtractionError as e:
        logger.error(f"Failed to extract {pdf_path}: {e}")
        raise
```

**Deliverable**: Robust error handling with clear user feedback and comprehensive logging

---

## Step 8: Basic Testing Framework
**Timeline**: Day 4-5 (4-5 hours)  
**Priority**: High - Quality assurance

### Tasks Breakdown
- [ ] Create diverse test PDF samples (simple, complex, problematic)
- [ ] Implement unit tests for each component
- [ ] Add integration tests for full pipeline
- [ ] Create property-based tests for section parsing
- [ ] Add performance benchmarks
- [ ] Set up test coverage reporting

### Test Structure
```
tests/
├── unit/
│   ├── test_pdf_extractor.py       # PDF extraction logic
│   ├── test_section_parser.py      # Section identification
│   ├── test_text_cleaning.py       # Normalization pipeline
│   └── test_data_models.py         # Immutable dataclasses
├── integration/
│   ├── test_pdf_pipeline.py        # End-to-end processing
│   └── test_error_handling.py      # Error scenarios
├── fixtures/
│   ├── sample_papers/              # Test PDFs
│   │   ├── simple_hci_paper.pdf
│   │   ├── complex_multicolumn.pdf
│   │   ├── password_protected.pdf
│   │   └── corrupted_file.pdf
│   └── expected_outputs/           # JSON fixtures
│       ├── simple_paper_sections.json
│       └── complex_paper_sections.json
└── conftest.py                     # Pytest configuration
```

### Test Categories
1. **Unit Tests**: Individual component functionality
2. **Integration Tests**: Full pipeline with real PDFs  
3. **Property Tests**: Section parsing with generated data
4. **Performance Tests**: Processing time benchmarks
5. **Error Tests**: Failure scenarios and recovery

### Test Coverage Goals
- **Overall**: >90% code coverage
- **Critical paths**: 100% coverage for extraction and parsing
- **Error handling**: All exception paths tested
- **Data models**: All validation rules tested

### Sample Test Implementation
```python
def test_pdf_extraction_basic():
    """Test basic PDF text extraction"""
    pdf_path = Path("tests/fixtures/simple_hci_paper.pdf")
    content = extract_pdf_content(pdf_path)
    
    assert content.total_pages > 0
    assert len(content.pages) == content.total_pages
    assert all(isinstance(page, PdfPage) for page in content.pages)
    assert len(content.full_text) > 100  # Should have meaningful content

def test_section_parsing_confidence():
    """Test section parsing returns appropriate confidence scores"""
    # Property-based test using hypothesis
    pass
```

**Deliverable**: Comprehensive test suite with >90% coverage and diverse test scenarios

---

## Step 9: CLI Foundation
**Timeline**: Day 5 (2-3 hours)  
**Priority**: Medium - User interface

### Tasks Breakdown
- [ ] Set up Click framework for CLI commands
- [ ] Implement basic PDF processing commands
- [ ] Add verbose output and debugging options
- [ ] Create JSON export functionality
- [ ] Add help documentation and examples
- [ ] Implement basic progress reporting

### CLI Command Structure
```bash
# Core functionality
python -m hci_extractor parse paper.pdf --output sections.json
python -m hci_extractor validate paper.pdf  # Check processability
python -m hci_extractor debug paper.pdf --verbose  # Detailed info

# Batch operations (future)
python -m hci_extractor batch input_dir/ --output-dir results/

# Utility commands
python -m hci_extractor --version
python -m hci_extractor --help
```

### Implementation with Click
```python
import click
from pathlib import Path

@click.group()
def cli():
    """HCI Paper Extractor - Extract structured content from academic PDFs"""
    pass

@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='Output file for extracted sections')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def parse(pdf_path: Path, output: Optional[Path], verbose: bool):
    """Extract sections from a single PDF"""
    if verbose:
        logging.basicConfig(level=logging.INFO)
    
    try:
        content = extract_pdf_content(pdf_path)
        sections = parse_sections(content)
        
        if output:
            save_sections_json(sections, output)
            click.echo(f"Extracted {len(sections)} sections to {output}")
        else:
            for section in sections:
                click.echo(f"{section.name}: {len(section.text)} chars")
                
    except PdfProcessingError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
```

**Deliverable**: Working CLI that processes PDFs and outputs structured section data

---

## Success Criteria & Validation

### Functional Requirements
- [ ] Successfully process 90% of typical academic PDFs
- [ ] Extract text with character-level position tracking
- [ ] Identify standard academic sections with >85% accuracy
- [ ] Handle common PDF issues gracefully with clear error messages
- [ ] Maintain complete immutability throughout data pipeline

### Performance Requirements
- [ ] Process typical academic papers (10-20 pages) in <5 seconds
- [ ] Handle PDFs up to 50 pages without memory issues
- [ ] Minimal memory footprint through efficient data structures

### Quality Requirements
- [ ] >90% test coverage across all components
- [ ] Type safety with mypy validation
- [ ] Code formatting with black and ruff compliance
- [ ] Comprehensive error handling and logging

### Usability Requirements
- [ ] Single command extracts structured data ready for Phase 2
- [ ] Clear error messages for common failure scenarios
- [ ] JSON export format compatible with downstream processing

---

## Risk Mitigation

### Technical Risks
**Risk**: Complex academic PDFs break section detection  
**Mitigation**: Start with pattern-based approach, collect failure cases for ML enhancement in later phases

**Risk**: Memory issues with large batch processing  
**Mitigation**: Process PDFs individually, implement streaming for very large files

**Risk**: Text extraction loses critical formatting  
**Mitigation**: Preserve character-level positioning and implement format reconstruction utilities

### Schedule Risks
**Risk**: PDF processing complexity exceeds time estimates  
**Mitigation**: Focus on 80% case initially, document edge cases for future phases

**Risk**: Testing setup takes longer than expected  
**Mitigation**: Start with basic tests early, expand coverage incrementally

---

## Phase 1 Completion Checklist

- [ ] All 9 steps completed with deliverables
- [ ] Comprehensive test suite passing
- [ ] CLI commands working for single PDF processing
- [ ] Error handling tested with problematic PDFs
- [ ] Code quality checks (mypy, black, ruff) passing
- [ ] Documentation updated with API examples
- [ ] Performance benchmarks established
- [ ] Ready for Phase 2 LLM integration

---

## Step 2: Core PDF Text Extraction - Detailed Implementation Plan
**Timeline**: Day 1-2 (4-5 hours total)  
**Priority**: Critical - Foundation for all PDF processing

### Overview
Implement robust PDF text extraction with character-level positioning while maintaining immutable design principles and verbatim accuracy requirements.

### Step 2A: Add PDF Dependencies & Data Models (1 hour)
**Goal**: Add PyMuPDF and create immutable data structures

#### Tasks:
- [ ] Add PyMuPDF to pyproject.toml dependencies
- [ ] Create immutable `PdfPage` and `PdfContent` dataclasses
- [ ] Add character positioning metadata for verbatim validation
- [ ] Create extraction metadata structure
- [ ] Update type hints and validation

#### Data Models to Implement:
```python
@dataclass(frozen=True)
class CharacterPosition:
    """Character-level positioning for verbatim validation."""
    char_index: int
    page_number: int
    x: float
    y: float
    bbox: tuple[float, float, float, float]

@dataclass(frozen=True)
class PdfPage:
    """Immutable representation of a single PDF page."""
    page_number: int
    text: str
    char_count: int
    dimensions: tuple[float, float]  # width, height
    char_positions: tuple[CharacterPosition, ...] = ()
    
    def __post_init__(self):
        if self.page_number < 1:
            raise ValueError("Page number must be >= 1")
        if len(self.text) != self.char_count:
            raise ValueError("Text length must match char_count")

@dataclass(frozen=True)
class PdfContent:
    """Immutable representation of complete PDF document."""
    file_path: str
    total_pages: int
    pages: tuple[PdfPage, ...]
    extraction_metadata: dict[str, Any]
    created_at: datetime
    
    @property
    def full_text(self) -> str:
        return "\n".join(page.text for page in self.pages)
    
    @property
    def total_chars(self) -> int:
        return sum(page.char_count for page in self.pages)
    
    def get_text_at_position(self, char_index: int) -> tuple[str, int]:
        """Return character and page number at global character index."""
        current_index = 0
        for page in self.pages:
            if current_index + page.char_count > char_index:
                local_index = char_index - current_index
                return page.text[local_index], page.page_number
            current_index += page.char_count
        raise IndexError("Character index out of range")
```

### Step 2B: PDF Extraction Engine (2 hours)
**Goal**: Implement core PyMuPDF extraction with positioning

#### Tasks:
- [ ] Create `PdfExtractor` class with PyMuPDF integration
- [ ] Implement page-by-page text extraction
- [ ] Capture character-level positioning data
- [ ] Add text quality validation
- [ ] Handle basic PDF variations

#### Implementation Strategy:
```python
class PdfExtractor:
    """Extract text from PDFs with character-level positioning."""
    
    def extract_content(self, file_path: Path) -> PdfContent:
        """Extract complete PDF content with positioning data."""
        # Implementation tracks every character position
        
    def _extract_page(self, page: fitz.Page, page_num: int) -> PdfPage:
        """Extract single page with character positions."""
        # Get text blocks with positioning
        # Build character position mapping
        # Return immutable PdfPage
        
    def _validate_extraction(self, content: PdfContent) -> bool:
        """Validate extraction quality and completeness."""
        # Check for reasonable text length
        # Verify character positions are valid
        # Ensure pages are in order
```

#### Character Position Tracking:
- Use PyMuPDF's `get_text("dict")` for detailed positioning
- Map every character to page coordinates
- Enable precise verbatim validation later
- Support text selection reconstruction

### Step 2C: Error Handling & Edge Cases (1 hour)
**Goal**: Robust handling of problematic PDFs

#### Error Scenarios to Handle:
```python
class PdfExtractionError(Exception):
    """Base exception for PDF extraction issues."""
    pass

class PasswordProtectedError(PdfExtractionError):
    """PDF requires password for access."""
    pass

class CorruptedFileError(PdfExtractionError):
    """PDF file is corrupted or unreadable."""
    pass

class NoTextLayerError(PdfExtractionError):
    """PDF contains only images, no extractable text."""
    pass

class ExtractionQualityError(PdfExtractionError):
    """Extracted text quality below acceptable threshold."""
    pass
```

#### Error Handling Strategy:
- Detect password protection before extraction
- Validate PDF file integrity
- Check for text layer existence
- Provide clear error messages for researchers
- Log detailed error context for debugging

### Step 2D: Text Normalization Pipeline (1.5 hours)
**Goal**: Clean text while maintaining verbatim traceability

#### Tasks:
- [ ] Create reversible text cleaning pipeline
- [ ] Handle common PDF extraction artifacts
- [ ] Preserve academic formatting (citations, equations)
- [ ] Map cleaned text back to original positions
- [ ] Implement transformation tracking

#### Normalization Strategy:
```python
@dataclass(frozen=True)
class TextTransformation:
    """Track text cleaning transformations for reversibility."""
    original_text: str
    cleaned_text: str
    transformations: tuple[str, ...]
    char_mapping: dict[int, int]  # cleaned_pos -> original_pos
    
    def reverse_lookup(self, cleaned_position: int) -> int:
        """Map cleaned text position back to original."""
        return self.char_mapping.get(cleaned_position, -1)

class TextNormalizer:
    """Clean PDF text while maintaining verbatim validation."""
    
    def normalize(self, raw_text: str) -> TextTransformation:
        """Apply cleaning with full traceability."""
        # Fix hyphenated words: "eval- uation" -> "evaluation"
        # Remove excessive whitespace
        # Preserve citation formatting
        # Track every transformation
```

#### Cleaning Rules (Academic-Aware):
- **Hyphenation**: "eval- uation" → "evaluation"
- **Whitespace**: Multiple spaces → single space
- **Line breaks**: Preserve paragraph structure
- **Citations**: Keep "[1, 2, 3]" and "(Smith et al., 2023)" intact
- **Equations**: Preserve mathematical notation
- **Headers/Footers**: Remove repetitive page elements

### Step 2E: CLI Integration & Testing (0.5 hours)
**Goal**: Add PDF parsing to CLI and validate functionality

#### Tasks:
- [ ] Add `parse` command to CLI
- [ ] Implement basic PDF extraction workflow
- [ ] Add verbose output for debugging
- [ ] Create test files and validation
- [ ] Update help documentation

#### CLI Commands to Add:
```bash
# Extract text from single PDF
python -m hci_extractor parse paper.pdf --output extracted.json

# Debug extraction process
python -m hci_extractor parse paper.pdf --verbose --debug

# Validate PDF is processable
python -m hci_extractor validate paper.pdf
```

### Success Criteria for Step 2

#### Functional Requirements:
- [ ] Extract text from 90% of typical academic PDFs
- [ ] Maintain character-level position tracking
- [ ] Handle common PDF issues gracefully
- [ ] Preserve text quality for academic content
- [ ] Process 10-20 page papers in <5 seconds

#### Quality Requirements:
- [ ] 100% verbatim accuracy (cleaned text maps to original)
- [ ] Immutable data structures throughout
- [ ] Comprehensive error handling with clear messages
- [ ] >90% test coverage for extraction logic

#### Integration Requirements:
- [ ] CLI commands work end-to-end
- [ ] JSON output ready for next phase processing
- [ ] Error messages guide user troubleshooting
- [ ] Verbose mode provides debugging information

### Testing Strategy

#### Test Cases to Implement:
```python
def test_simple_pdf_extraction():
    """Test basic PDF text extraction."""
    
def test_character_position_tracking():
    """Verify character positions map correctly."""
    
def test_text_normalization_reversibility():
    """Ensure cleaned text can be traced back to original."""
    
def test_password_protected_handling():
    """Test graceful handling of encrypted PDFs."""
    
def test_corrupted_file_error():
    """Test error handling for malformed PDFs."""
    
def test_multipage_extraction():
    """Test extraction across multiple pages."""
    
def test_academic_formatting_preservation():
    """Test that citations and equations are preserved."""
```

#### Test Data Requirements:
- Simple academic paper (10-15 pages)
- Complex multi-column layout
- Paper with equations and citations
- Password-protected PDF
- Corrupted/malformed file
- Scanned image PDF (no text layer)

### Dependencies to Add

```toml
# Add to pyproject.toml dependencies
dependencies = [
    "click>=8.0.0",
    "python-dotenv>=1.0.0", 
    "pymupdf>=1.24.0",  # PDF text extraction with positioning
]
```

### Risk Mitigation

**Risk**: PyMuPDF character positioning inaccurate  
**Mitigation**: Implement validation against known text patterns, fallback to simpler extraction

**Risk**: Memory issues with large PDFs  
**Mitigation**: Page-by-page processing, implement streaming for very large files

**Risk**: Text cleaning breaks academic formatting  
**Mitigation**: Conservative cleaning rules, extensive testing with academic content

**Risk**: Extraction speed too slow for batch processing  
**Mitigation**: Profile extraction performance, optimize PyMuPDF settings

---

**Next Phase**: Phase 2 will integrate LLM analysis using the structured sections from Phase 1, implementing the verbatim extraction and confidence scoring system.