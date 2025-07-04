## Project Overview

An academic research tool for extracting and classifying claims, findings, and methods from HCI papers using LLM-driven analysis. The system focuses on **verbatim extraction** to maintain academic integrity while leveraging LLMs for identification and classification.--

*The HCI Paper Extractor is production-ready for academic research workflows. The system successfully automates literature extraction while maintaining verbatim accuracy and classification precision required for systematic literature reviews and meta-analyses. All core MVP requirements have been achieved and validated.*

**Primary Goal**: Support systematic literature reviews by extracting structured information from 10-50 HCI papers, enabling researchers to identify patterns, gaps, and conflicting claims across literature.

## Core Architecture Principles

### 1. Single Responsibility
- Each component does one thing well
- Clear separation between PDF processing, LLM analysis, and data storage
- Modular design enables easy testing and maintenance

### 2. Minimal Dependencies
- Use Python standard library where possible
- Add packages only when essential for functionality
- Keep the dependency surface area small for reliability

### 3. Data-First Design
- Focus on getting quality extractions over fancy UI
- Prioritize data integrity and verbatim accuracy
- Export formats optimized for analysis workflows (CSV, JSON)

### 4. Extensible Foundation
- Abstract LLM interface supports multiple providers (Gemini, OpenAI, Anthropic)
- Plugin architecture for new export formats
- Easy to add new extraction types or classification schemas

### 5. Immutable Design
- All data structures are immutable once created
- Use `@dataclass(frozen=True)` for all data models
- Return new objects instead of modifying existing ones
- Functional programming patterns for data transformations
- Thread-safe by design through immutability

## Technical Implementation Strategy

### Phase 1: PDF Processing Foundation
- **Text Extraction**: PyMuPDF for reliable text preservation with page numbers
- **Section Detection**: Regex-based identification of paper sections (Abstract, Methods, Results, etc.)
- **Structured Output**: Return immutable sections with metadata for LLM processing

### Phase 2: LLM Integration
- **Provider Abstraction**: Base class enabling multiple LLM backends
- **Gemini API First**: Start with Gemini 1.5 Flash for cost-effectiveness
- **Structured Prompts**: Section-specific prompts with few-shot examples
- **JSON Output Mode**: Reliable structured responses with low temperature

### Phase 3: Core Pipeline
- **Async Processing**: Handle LLM API calls efficiently
- **Error Handling**: Robust retry logic and graceful degradation
- **Progress Tracking**: CLI feedback for batch processing
- **Data Validation**: Pydantic models ensure data integrity
- **Immutable Pipeline**: Each stage returns new immutable objects

### Phase 4: Export & Usability
- **Multiple Formats**: JSON (complete), CSV (analysis-ready), Markdown (readable)
- **CLI Interface**: Simple commands for single papers and batch processing
- **Integration Ready**: Output formats work with Excel, R, Python pandas

## Development Guiding Principles

### 1. Academic Integrity First
- **Verbatim Extraction**: Never paraphrase or summarize - extract exact text
- **Citation Tracking**: Maintain page numbers and section references
- **Transparency**: Clear confidence scores and evidence classification

### 2. Researcher-Centric Design
- **Literature Review Workflow**: Optimize for systematic review processes
- **Export Compatibility**: Work seamlessly with analysis tools researchers use
- **Manual Synthesis Support**: Provide structured data, don't replace human analysis

### 3. Reliable Automation
- **Deterministic Processing**: Consistent results across runs
- **Error Recovery**: Handle PDF parsing failures and API issues gracefully
- **Validation**: Verify extracted text exists in source documents

### 4. Immutable Data Flow
- **No Side Effects**: Functions return new objects, never modify inputs
- **Predictable State**: Data structures cannot change after creation
- **Thread Safety**: Immutable objects are inherently thread-safe
- **Debugging**: Easier to reason about data flow with immutable objects
- **Testing**: Simpler unit tests with guaranteed object state

## Data Models & Standards

### Core Entities (All Immutable)
```python
@dataclass(frozen=True)
class Paper:
    paper_id: str
    title: str
    authors: tuple[str, ...]  # Immutable sequence
    venue: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    file_path: str = ""

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
## Development Environment

### Virtual Environment (Required)
**Always use a virtual environment** for this project to ensure dependency isolation and reproducible builds.


### Research Impact Goals
- Enable faster systematic literature reviews through automated extraction
- Improve consistency in claim identification across papers
- Support meta-analysis with structured data exports
- Help identify research gaps through systematic analysis

## Non-Goals (MVP Boundaries)

- **No Summarization**: Extract verbatim, never summarize or paraphrase
- **No Synthesis**: Provide structured data, don't synthesize insights
- **No Quality Assessment**: Don't score paper quality or methodological rigor
- **No Real-time Collaboration**: Single-user CLI tool
- **No Citation Networks**: Focus on content extraction, not reference analysis

## Current Implementation Status (July 2025)

### ✅ PRODUCTION READY

The HCI Paper Extractor is production-ready for academic research workflows. All core features are implemented and working well.

**Core Features:**
- **Immutable Data Models**: All data structures use frozen dataclasses for thread safety
- **PDF Processing**: Reliable text extraction with section detection 
- **LLM Integration**: Provider-agnostic design, currently using Gemini API
- **Batch Processing**: Concurrent handling of multiple papers with progress tracking
- **Academic Integrity**: Verbatim extraction with validation
- **Smart Classification**: Good accuracy for identifying claims, findings, and methods
- **Large Section Handling**: Automatic chunking for sections over 10k characters

**Infrastructure Enhancements:**
- **Configuration System**: Environment variables, CLI options, and config files with proper precedence
- **Event System**: Decoupled monitoring and debugging capabilities
- **Error Recovery**: Multiple strategies for handling malformed LLM responses
- **Retry Logic**: Smart retries based on error type
- **User-Friendly Errors**: Technical errors translated to helpful guidance
- **Diagnostic Tools**: Commands to check system health and configuration

**CLI Commands:**
- `extract`: Process single papers with LLM analysis
- `batch`: Process multiple papers concurrently
- `export`: Generate CSV/JSON/Markdown outputs
- `validate`: Check if PDFs can be processed
- `diagnose`: System health check
- `test-config`: Validate configuration

**Quality Standards Met:**
- Verbatim accuracy for academic integrity
- Good classification performance
- Robust error handling with graceful degradation
- Clear error messages that help users fix issues
- Efficient processing (typically under 30 seconds per paper)
- Handles real-world academic papers including complex formatting

### 📋 FUTURE ENHANCEMENTS (Post-MVP)

**Additional LLM Providers:**
- OpenAI GPT-4 integration
- Anthropic Claude integration
- Local model support (Ollama, etc.)

**Advanced Features:**
- Statistical data extraction (p-values, effect sizes, sample sizes)
- Citation network analysis
- Multi-language support
- Real-time collaboration features

**Research Integration:**
- Systematic literature review templates
- Meta-analysis data preparation tools
- Research gap identification algorithms
- Inter-rater reliability metrics

**User Interface:**
- Web-based viewer for extraction results
- Visualization dashboards
- Integration with reference managers (Zotero, Mendeley)

## Current Architecture Overview

```
src/hci_extractor/
├── models/           # Immutable data structures (Paper, ExtractedElement, ExtractionResult)
├── extractors/       # PDF processing (PyMuPDF integration, text normalization)
├── llm/             # LLM provider abstraction (Gemini + future providers)
├── pipeline/        # Section processing, validation, batch handling
├── prompts/         # YAML-based prompt management system
└── main.py          # Complete CLI interface (extract, batch, export, validate)

tests/               # Comprehensive test coverage
├── test_models.py                    # Data model validation (immutability, UUIDs)
├── test_pipeline.py                  # Pipeline integration (concurrency, error handling)
├── test_verbatim_validation.py       # Academic integrity (100% requirement)
├── test_classification_precision.py  # Classification accuracy (>90% requirement)
└── test_cli_integration.py          # End-to-end CLI testing
```

## Next Development Priorities

### **Immediate Tasks:**
1. **Documentation Updates**
   - Update README with current CLI examples
   - Document all configuration options
   - Add troubleshooting guide

2. **Code Cleanup**
   - Remove any legacy directories
   - Clean up unused imports

### **Future Enhancements:**
1. **Research Features**
   - Extract statistical data (p-values, effect sizes)
   - Better citation tracking
   - Research gap identification tools

2. **Additional LLM Providers**
   - OpenAI GPT-4 support
   - Anthropic Claude support
   - Local model options

3. **Advanced Export Options**
   - Research-specific formats
   - Integration with reference managers
   - Visualization dashboards


## Usage for Academic Researchers

**Single Paper Analysis:**
```bash
python -m hci_extractor extract paper.pdf --output results.json
```

**Batch Literature Review:**
```bash
python -m hci_extractor batch papers_folder/ results_folder/
python -m hci_extractor export results_folder/ --format csv --output analysis.csv
```

-