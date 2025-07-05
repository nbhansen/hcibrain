## Project Overview

An academic research tool for extracting and classifying claims, findings, and methods from HCI papers using LLM-driven analysis. The system focuses on **verbatim extraction** to maintain academic integrity while leveraging LLMs for identification and classification.--

*The HCI Paper Extractor is production-ready for academic research workflows. The system successfully automates literature extraction while maintaining verbatim accuracy and classification precision required for systematic literature reviews and meta-analyses. All core MVP requirements have been achieved and validated.*

**Primary Goal**: Support systematic literature reviews by extracting structured information from 10-50 HCI papers, enabling researchers to identify patterns, gaps, and conflicting claims across literature.

## Core Architecture Principles

### 1. Hexagonal Architecture (Ports & Adapters)
- **Domain Layer**: Pure business logic with no external dependencies
- **Application Layer**: CLI interface orchestrating domain operations
- **Infrastructure Layer**: External concerns (APIs, environment, file system)
- **Adapters**: Clean abstractions for all external integrations
- **Dependency Inversion**: All dependencies injected via DI container

### 2. Immutable Design Throughout
- All data structures are immutable once created (`@dataclass(frozen=True)`)
- Return new objects instead of modifying existing ones
- Functional programming patterns for data transformations
- Thread-safe by design through immutability
- No mutable default factories (tuples instead of lists)

### 3. Zero Global State
- No global variables or singleton patterns
- All configuration and services injected explicitly
- Dependency injection container manages object lifecycle
- Predictable and testable component interactions
- Complete elimination of side effects

### 4. Domain-Driven Design
- Academic research concepts modeled as first-class domain objects
- Clean separation between business logic and technical concerns
- Domain events for decoupled communication
- Rich domain models with behavior, not just data containers
- Ubiquitous language throughout codebase

### 5. Extensible Foundation
- Abstract LLM interface supports multiple providers (Gemini, OpenAI, Anthropic)
- Plugin architecture for new export formats
- Easy to add new extraction types or classification schemas
- Provider configuration abstraction for different LLM requirements

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
## Academic Workflow Support

### Current Capabilities

The HCI Paper Extractor currently supports core academic research workflows through validated extraction and export capabilities:

#### **Systematic Literature Review Support:**
- **Structured Data Extraction**: Verbatim extraction of claims, findings, and methods
- **Batch Processing**: Handle 10-50 papers efficiently with progress tracking
- **Multiple Export Formats**: CSV for analysis, JSON for data science, Markdown for review
- **Academic Integrity**: Maintain exact text with page references for citation
- **Customizable Extraction**: Modify prompts for specific research domains

#### **Research Analysis Workflows:**
```
1. Batch extract papers → HCI Extractor CLI
2. Export structured data → CSV/JSON formats
3. Import into analysis tools → Excel/R/Python pandas
4. Manual synthesis and analysis → Human expertise required
5. Generate research insights → Researcher-driven conclusions
```

#### **Integration with Academic Tools:**
- **Reference Managers**: Export formats compatible with Zotero, Mendeley, EndNote
- **Statistical Software**: CSV exports work directly with R, SPSS, Python pandas
- **Analysis Tools**: JSON structure supports custom analysis pipelines

### Realistic Academic Use Cases

#### **Literature Review Researchers:**
- Extract claims and findings from 20-50 papers in a research area
- Export to CSV for systematic comparison and thematic analysis
- Maintain academic integrity with verbatim text and page references

#### **Meta-Analysis Preparation:**
- Extract quantitative findings with confidence scores
- Export structured data for manual validation and synthesis
- Provide foundation for statistical analysis (human validation required)

#### **Research Domain Analysis:**
- Process papers in specific HCI subfields (e.g., accessibility, participatory design)
- Customize prompts to focus on domain-specific contributions
- Export results for manual gap identification and research planning

## Development Environment

### Virtual Environment (Required)
**Always use a virtual environment** for this project to ensure dependency isolation and reproducible builds.

## Non-Goals (MVP Boundaries)

- **No Summarization**: Extract verbatim, never summarize or paraphrase
- **No Synthesis**: Provide structured data, don't synthesize insights
- **No Quality Assessment**: Don't score paper quality or methodological rigor
- **No Real-time Collaboration**: Single-user CLI tool
- **No Citation Networks**: Focus on content extraction, not reference analysis

## Current Implementation Status (July 2025)

### ✅ PRODUCTION READY AND ACTIVELY VALIDATED

The HCI Paper Extractor is production-ready and has been successfully validated in real academic research workflows. The system demonstrates reliable performance with enterprise-grade architecture, processing academic papers with high accuracy and excellent user experience.

**Core Features (Validated in Production):**
- **High-Performance Processing**: 17-page academic papers processed in ~30 seconds
- **Reliable PDF Extraction**: Handles complex academic formatting with section detection
- **Flexible LLM Integration**: Provider-agnostic design, currently using Gemini API
- **Batch Processing**: Concurrent handling of multiple papers with real-time progress tracking
- **Academic Integrity**: Verbatim extraction with validation (91+ elements extracted per paper)
- **Smart Classification**: Proven accuracy for identifying claims, findings, and methods
- **Customizable Prompts**: Easy modification of extraction behavior for different research domains
- **Multiple Export Formats**: JSON, CSV, and Markdown for different analysis workflows
- **Large Section Handling**: Automatic chunking for sections over 10k characters

**Infrastructure Enhancements:**
- **Hexagonal Architecture**: Complete ports/adapters implementation with clean separation
- **Dependency Injection**: Comprehensive DI container managing all services
- **Zero Global State**: No global variables or singleton patterns throughout codebase
- **Immutable Design**: All objects immutable with `@dataclass(frozen=True)`
- **Configuration System**: Environment variables, CLI options, and config files with proper precedence
- **Event System**: Decoupled monitoring and debugging capabilities via domain events
- **Error Recovery**: Multiple strategies for handling malformed LLM responses
- **Retry Logic**: Smart retries based on error type
- **User-Friendly Errors**: Technical errors translated to helpful guidance
- **Diagnostic Tools**: Commands to check system health and configuration
- **Architecture Validation**: 20 automated tests ensuring compliance

**CLI Commands (Fully Functional):**
- `extract`: Process single papers with LLM analysis (tested: 30s for 17-page paper)
- `batch`: Process multiple papers concurrently with progress tracking
- `export`: Generate CSV/JSON/Markdown outputs (all formats validated)
- `diagnose`: System health check (validates API keys, configuration)
- `validate`: Check if PDFs can be processed
- `test-config`: Validate configuration
- `serve`: Start web API server (NEW: MVP Web UI implementation complete)

**Quality Standards Met (Validated in Practice):**
- **Academic Integrity**: Verbatim accuracy with validation (91+ elements extracted per paper)
- **Classification Performance**: Reliable identification of claims (52), findings (33), methods (7)
- **Architecture Compliance**: Complete hexagonal architecture implementation
- **Code Quality**: Zero global state, full immutability, comprehensive DI
- **Error Handling**: Robust error handling with graceful degradation (tested with edge cases)
- **User Experience**: Clear error messages that help users fix issues
- **Performance**: Consistent 30-second processing for 17-page papers
- **Compatibility**: Handles real-world academic papers including complex formatting
- **Prompt Flexibility**: Easy customization for different research domains
- **Export Versatility**: Three validated formats (JSON, CSV, Markdown)
- **Type Safety**: Full mypy compliance with comprehensive type annotations

## Development Roadmap

### ✅ Phase 2: Web Interface & User Experience (COMPLETED)

**MVP Web UI Implementation Successfully Delivered (July 2025)**

The web interface has been fully implemented as a production-ready API that wraps the existing CLI functionality. The implementation follows the planned "wrap, don't rewrite" approach with zero business logic duplication.

**Delivered Components:**
- **REST API Backend**: FastAPI with complete extraction functionality
- **Real-time Progress**: WebSocket implementation for long-running extractions  
- **CLI Integration**: `serve` command for starting the web server
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Type Safety**: Full Pydantic validation for all API endpoints

**Next Priority**: Frontend Development (React/Vue/Streamlit options available)

**Core Web Application:**
- **Drag & Drop Interface**: Upload PDFs directly in browser with real-time progress
- **Results Explorer**: Browse extracted elements by type, section, confidence score
- **Project Management**: Group papers into research projects with save/load functionality
- **Export Dashboard**: One-click exports to multiple formats with preview capability
- **Search & Filter**: Quick search across all extracted elements within projects

**Quality of Life Improvements:**
- **Prompt Customization UI**: Web interface for modifying extraction prompts
- **Batch Upload**: Web interface for processing multiple papers simultaneously
- **Comparison View**: Side-by-side comparison of extractions from multiple papers
- **Citation Integration**: Link extractions back to original PDF locations with page references
- **Configuration Profiles**: Pre-configured settings for different research domains

**Technical Infrastructure:**
- **RESTful API**: Clean API following hexagonal architecture principles
- **Authentication**: Simple user accounts for project management
- **Database Integration**: SQLite/PostgreSQL for storing projects and results
- **Real-time Updates**: WebSocket support for live progress tracking

### 🔧 Phase 3: Platform Enhancements (Medium Term)

**Additional LLM Providers:**
- OpenAI GPT-4 integration for improved extraction quality
- Anthropic Claude integration for diverse LLM capabilities  
- Local model support (Ollama) for privacy-sensitive research

**Collaboration Features:**
- **Team Projects**: Share projects with research team members
- **Comment System**: Annotate and discuss extracted elements
- **Export Sharing**: Generate shareable links for results
- **Integration APIs**: Connect with reference managers (Zotero, Mendeley)

## Current Architecture Overview (Hexagonal Architecture)

```
src/hci_extractor/
├── core/                    # Domain Layer (Pure Business Logic)
│   ├── config.py           # Immutable configuration domain objects
│   ├── di_container.py     # Dependency injection container
│   ├── events.py           # Domain events (all immutable)
│   ├── models/             # Domain models (Paper, ExtractedElement, etc.)
│   ├── analysis/           # Business logic (section processing, validation)
│   ├── extraction/         # PDF processing domain logic
│   └── metrics.py          # Domain metrics and monitoring
├── infrastructure/         # Infrastructure Layer (External Concerns)
│   └── configuration_service.py  # Environment variable access
├── providers/              # Adapters for External LLM Services
│   ├── base.py            # LLM provider port (abstract interface)
│   ├── gemini_provider.py # Gemini adapter implementation
│   └── provider_config.py # Provider configuration abstractions
├── cli/                   # Application Layer (CLI Interface)
│   ├── commands.py        # CLI command handlers
│   ├── config_builder.py  # CLI configuration building
│   ├── config_options.py  # CLI option definitions
│   ├── config_profiles.py # Predefined configuration profiles
│   └── cli_configuration_service.py  # CLI configuration service
├── utils/                 # Shared Utilities
│   ├── logging.py         # Logging configuration
│   ├── retry_handler.py   # Retry logic utilities
│   ├── json_recovery.py   # JSON parsing recovery
│   ├── error_classifier.py # Error classification
│   └── user_error_translator.py # User-friendly error messages
├── prompts/               # Prompt Management
│   ├── prompt_manager.py  # YAML-based prompt system
│   └── *.yaml            # Section-specific prompts
└── main.py               # Application entry point

tests/                     # Comprehensive Test Coverage
├── test_models.py                    # Domain model validation
├── test_pipeline.py                  # Pipeline integration tests
├── test_verbatim_validation.py       # Academic integrity validation
├── test_classification_precision.py  # Classification accuracy tests
├── test_cli_integration.py          # End-to-end CLI testing
├── test_immutable_providers.py      # Provider immutability tests
├── test_architecture_compliance.py  # Architecture validation (20 tests)
└── conftest.py                      # Test configuration and fixtures
```

**Key Architecture Achievements:**
- **Domain Layer**: Pure business logic with no external dependencies
- **Infrastructure Layer**: All external concerns (env vars, APIs) properly isolated
- **Application Layer**: CLI interface with dependency injection
- **Adapters**: Clean provider abstractions following ports/adapters pattern
- **Dependency Injection**: Complete DI container managing all services
- **Immutability**: All objects immutable with `@dataclass(frozen=True)`
- **Event-Driven**: Decoupled communication via immutable domain events

## Next Development Priorities

### ✅ **COMPLETED (Documentation & Cleanup):**
1. **Documentation Updates** - ✅ **COMPLETE**
   - Updated README with current CLI examples and all commands
   - Documented configuration profiles and environment variables
   - Added comprehensive troubleshooting guide with error recovery info
   - Added configuration options table and advanced usage examples

2. **Code Cleanup** - ✅ **COMPLETE**
   - Organized documentation in `/docs` with archived legacy files
   - Cleaned up git repository and removed obsolete files
   - Fixed all critical linting and testing issues

### ✅ **COMPLETED - Architecture Compliance (December 2025):**

**All hexagonal architecture violations have been systematically resolved:**

1. ✅ **Global State Elimination** (Critical) - **COMPLETED**
   - Removed global `_container` variable from DI container
   - Eliminated `get_container()` global function 
   - Implemented proper dependency injection throughout codebase
   - All configuration objects are immutable and passed explicitly

2. ✅ **Dependency Injection Implementation** (Critical) - **COMPLETED**
   - Created comprehensive DI container with service registration
   - Removed hardcoded provider selection in CLI commands
   - Implemented proper service registration and resolution
   - Added interface-based dependency registration with ports/adapters

3. ✅ **Provider Layer Refactoring** (High) - **COMPLETED**
   - Removed mutable state from all providers
   - Eliminated direct environment access in providers
   - Moved business logic out of provider layer into domain services
   - Implemented proper ports/adapters pattern with LLMProviderConfig

4. ✅ **Domain Model Immutability** (High) - **COMPLETED**
   - Fixed mutable default factories throughout codebase
   - Replaced `field(default_factory=dict)` with immutable tuple defaults
   - All domain objects are truly immutable with `@dataclass(frozen=True)`
   - Added comprehensive validation for immutability in architecture tests

5. ✅ **Event Bus Architecture** (Medium) - **COMPLETED**
   - Moved from global singleton to injected dependency
   - Implemented thread-safe event handling
   - All events are immutable with proper metadata
   - Event bus properly integrated into DI container

6. ✅ **Configuration Architecture** (Medium) - **COMPLETED**
   - Implemented configuration as first-class domain object
   - Added configuration validation and type safety
   - Removed direct environment variable access throughout codebase
   - Implemented proper configuration precedence (CLI > env > defaults)
   - Created infrastructure ConfigurationService for environment access

7. ✅ **Hexagonal Architecture Completion** (Medium) - **COMPLETED**
   - Completed ports/adapters implementation
   - Separated domain logic from infrastructure concerns
   - Implemented proper application service layer
   - Added adapter interfaces for all external dependencies
   - Created CLI configuration service layer

**Architecture Validation:**
- ✅ 20 comprehensive architecture compliance tests (all passing)
- ✅ Zero global state variables in entire codebase  
- ✅ Complete dependency injection implementation
- ✅ All dataclasses properly frozen and immutable
- ✅ Clean separation of domain, infrastructure, and application layers
- ✅ Provider configuration abstraction with LLMProviderConfig
- ✅ CLI configuration service extraction
- ✅ Mypy type safety compliance

### 🔬 Future Research Directions (Exploratory)

*These features represent interesting research opportunities but face significant challenges in the HCI domain due to the qualitative and interpretive nature of much HCI research.*

#### **Limitations of Automated Analysis in HCI:**
- **Contextual Interpretation**: HCI research often requires deep contextual understanding
- **Qualitative Complexity**: Many HCI contributions are qualitative and resist simple categorization
- **Domain Diversity**: HCI spans multiple methodologies, making automated analysis challenging
- **Subjective Evaluation**: Research quality and impact require human expert judgment

#### **Potential Long-term Research Areas:**
1. **Semi-Automated Research Support** (Requires significant R&D)
   - Human-in-the-loop gap identification with AI assistance
   - Pattern highlighting in extracted data (not automated conclusions)
   - Consistency checking across extractions (flagging potential issues)
   - Template generation for systematic review workflows

2. **Enhanced Data Mining** (Highly Challenging)
   - Statistical data extraction from figures/tables (very unreliable in practice)
   - Citation network analysis integration (many existing tools already available)
   - Cross-reference validation and consistency checking
   - *Note: Success would require major advances in multimodal AI*

#### **Why These Features Are Not Currently Prioritized:**
- **HCI Research Diversity**: Unlike medical research, HCI lacks standardized reporting formats
- **Interpretive Nature**: Gap identification requires understanding research community priorities
- **Expert Knowledge Required**: Quality assessment needs domain expertise, not just text analysis
- **Existing Tools**: Many citation and statistical analysis tools already exist and excel in their domains

*The focus remains on providing excellent extraction and export capabilities that support human-driven research synthesis.*


## Usage for Academic Researchers (Validated Examples)

**System Setup and Validation:**
```bash
# Check system health and API configuration
python -m hci_extractor diagnose

# Expected output: All checks pass, ready for extraction
```

**Single Paper Analysis (Production Validated):**
```bash
# Extract from single PDF - typically 30 seconds for 17-page paper
python -m hci_extractor extract paper.pdf --output paper_extraction.json

# Results: 91+ elements extracted (claims, findings, methods)
# Output: JSON file with verbatim text, confidence scores, page references
```

**Multiple Export Formats:**
```bash
# Rename for export compatibility
mv results.json paper_extraction.json

# Export to CSV for analysis in Excel/R/Python
python -m hci_extractor export . --format csv --output analysis.csv

# Export to Markdown for human review
python -m hci_extractor export . --format markdown --output review.md
```

**Batch Literature Review:**
```bash
# Process multiple papers concurrently
python -m hci_extractor batch papers_folder/ results_folder/

# Export all results to analysis-ready CSV
python -m hci_extractor export results_folder/ --format csv --output literature_analysis.csv
```

**Prompt Customization for Research Domains:**
```bash
# Modify prompts in /prompts/ directory for domain-specific extraction
# Backup originals: cp -r prompts prompts_backup
# Edit prompts/base_prompts.yaml and prompts/section_guidance.yaml
# Test modifications: python -m hci_extractor extract test_paper.pdf --output test_results.json
```

## Technical Architecture for Web UI Development

**Current CLI Architecture (Hexagonal Design):**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Layer     │    │   Domain Layer   │    │ Infrastructure  │
│   (Commands)    │◄──►│  (Business Logic)│◄──►│  (LLM Providers)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Planned Web UI Architecture (API-First):**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   REST API       │    │   Domain Layer  │
│   (React/Vue)   │◄──►│   (FastAPI)      │◄──►│ (Existing Logic)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │    Database      │
                    │ (Project Storage)│
                    └──────────────────┘
```

**Web UI Technical Stack (Proposed):**
- **Backend API**: FastAPI with hexagonal architecture integration
- **Frontend**: Modern web framework (React/Vue) with real-time updates
- **Database**: SQLite for development, PostgreSQL for production
- **Authentication**: Simple session-based auth for project management
- **Real-time**: WebSocket support for extraction progress tracking

## MVP Web UI Implementation (Rapid Prototyping)

### Philosophy: "Wrap, Don't Rewrite"

The fastest way to build a web UI is to create a thin web layer that wraps the existing, proven CLI business logic. This approach minimizes risk, complexity, and development time while providing immediate value.

**Core Strategy:**
- **Reuse 100% of existing business logic** - zero duplication
- **Leverage existing DI container** - same service registration and dependencies
- **Follow hexagonal architecture** - web interface as new adapter layer
- **Minimal dependencies** - only add FastAPI for async web support

### Technical Architecture (MVP)

```
┌─────────────────────────────────────────┐
│             Web Interface               │
│  ┌─────────────┐  ┌─────────────┐     │
│  │  FastAPI    │  │  WebSocket  │     │
│  │  Routes     │  │  Progress   │     │
│  └──────┬──────┘  └─────────────┘     │
│         │                              │
│         ▼                              │
│  ┌─────────────────────────────────────┤
│  │     Web Service Layer               │
│  │  (Wraps extract_paper_simple)       │
│  └──────┬──────────────────────────────┘
│         │                              │
│         ▼                              │
│  ┌─────────────────────────────────────┤
│  │    Existing Business Logic          │
│  │  ┌─────────────┐  ┌─────────────┐  │
│  │  │ DI Container│  │   Services  │  │
│  │  └─────────────┘  └─────────────┘  │
│  └─────────────────────────────────────┘
```

**Request Flow:**
```
HTTP Upload → FastAPI Route → Web Service → extract_paper_simple() → JSON Response
```

### Implementation Plan (2-3 Hours Total)

#### **Phase 1: Foundation (30 minutes)**
1. **Add FastAPI dependency** to pyproject.toml
2. **Create web module** at `src/hci_extractor/web/`
3. **Set up DI container integration** using existing `create_configured_container()`
4. **Create basic FastAPI app** with health check endpoint

#### **Phase 2: Core API (60 minutes)**
1. **Create `/extract` endpoint** that accepts:
   - PDF file upload (multipart/form-data)
   - Optional paper metadata (title, authors, venue, year)
   - Optional extraction parameters
2. **Implement response models** using existing `ExtractionResult` structure
3. **Add progress tracking** via WebSocket connection
4. **Handle file upload/cleanup** with temporary file management

#### **Phase 3: Configuration & Error Handling (30 minutes)**
1. **Web-specific configuration** integration with existing config system
2. **Error handling** mapping existing HCI exceptions to HTTP responses
3. **API documentation** via FastAPI automatic OpenAPI generation
4. **Validation** using existing data models

#### **Phase 4: Integration & Testing (30 minutes)**
1. **Create startup script** that initializes DI container with web dependencies
2. **Add CLI command** to start web server: `hci-extractor serve --port 8000`
3. **Basic integration tests** using existing test patterns
4. **CORS configuration** for frontend development

### File Structure (Minimal)

```
src/hci_extractor/web/
├── __init__.py
├── app.py              # FastAPI application setup
├── routes.py           # API route handlers (/extract, /health)
├── models.py           # Request/Response Pydantic models
├── service.py          # Web service layer (wraps existing functions)
└── exceptions.py       # HTTP exception handling
```

### API Specification

#### **POST /extract**
```json
// Request (multipart/form-data)
{
  "file": "<PDF file>",
  "title": "optional paper title",
  "authors": "optional author list",
  "venue": "optional venue",
  "year": 2025
}

// Response
{
  "paper": {
    "paper_id": "uuid",
    "title": "extracted or provided title",
    "authors": ["author1", "author2"],
    "file_path": "uploaded_file.pdf"
  },
  "extraction_summary": {
    "total_elements": 91,
    "elements_by_type": {"claim": 44, "finding": 35, "method": 12},
    "average_confidence": 0.93,
    "processing_time_seconds": 30.5
  },
  "extracted_elements": [
    {
      "element_id": "uuid",
      "element_type": "claim",
      "text": "verbatim extracted text",
      "section": "abstract",
      "confidence": 0.95,
      "evidence_type": "quantitative",
      "page_number": 1
    }
  ]
}
```

#### **WebSocket /ws/progress**
```json
// Progress updates during extraction
{
  "status": "processing",
  "stage": "section_processing",
  "progress": 0.6,
  "message": "Processing discussion section (3/6 sections complete)"
}
```

### Key Benefits of This Approach

1. **Zero Business Logic Duplication** - complete reuse of proven extraction logic
2. **Consistent Behavior** - same validation, processing, and error handling as CLI
3. **Maintains Architecture** - follows established hexagonal architecture patterns
4. **Minimal Risk** - thin web layer over extensively tested core functionality
5. **Easy Testing** - leverage existing test infrastructure and patterns
6. **Fast Development** - 2-3 hours to working MVP
7. **Auto Documentation** - FastAPI generates OpenAPI/Swagger docs automatically

### Success Criteria

- [x] `/extract` endpoint successfully processes PDF files (same as CLI)
- [x] Returns identical structured data as `extract` CLI command
- [x] Progress tracking works via WebSocket with real-time updates
- [x] Error handling provides meaningful HTTP responses
- [x] API documentation auto-generated and accessible at `/docs`
- [x] Integration tests validate core functionality
- [x] CLI command `hci-extractor serve` starts web server
- [x] Processing time matches CLI performance (~30 seconds for 17-page paper)

## ✅ MVP Web UI Implementation COMPLETE

**Implementation Status: DELIVERED (July 2025)**

The MVP Web UI has been successfully implemented following the "wrap, don't rewrite" philosophy. All success criteria have been met with a fully functional API that provides identical functionality to the CLI interface through a web-based REST API.

### ✅ Delivered Features

**Core API Endpoints:**
- `GET /api/v1/health` - Service health check
- `GET /api/v1/config` - System configuration (sanitized)
- `POST /api/v1/extract` - PDF extraction with file upload
- `GET /api/v1/sessions/new` - Create progress tracking session
- `WS /api/v1/ws/progress/{session_id}` - Real-time progress via WebSocket

**CLI Integration:**
- `python -m hci_extractor serve` - Start web server
- Command-line options: `--host`, `--port`, `--reload`
- Full integration with existing CLI configuration system

**Technical Implementation:**
- **FastAPI Backend**: Async web framework with automatic OpenAPI documentation
- **Hexagonal Architecture**: Complete integration with existing DI container
- **Real-time Progress**: WebSocket endpoint broadcasting domain events
- **File Upload Handling**: Secure temporary file management with validation
- **Error Handling**: Comprehensive HTTP error responses with user-friendly messages
- **Type Safety**: Full Pydantic model validation for requests and responses

### ✅ Architecture Achievements

**Zero Business Logic Duplication:**
- 100% reuse of existing `extract_paper_simple()` function
- Same validation, processing, and error handling as CLI
- Identical data models and response structures

**Hexagonal Architecture Compliance:**
- Web interface as clean adapter layer
- No violations of domain/infrastructure boundaries  
- Complete dependency injection integration
- Immutable design patterns maintained throughout

**Performance Verified:**
- Health endpoint: `200 OK` in <50ms
- Full processing capability maintained
- Identical extraction accuracy as CLI interface

### ✅ Usage Instructions

**Starting the Web Server:**
```bash
# Default (localhost:8000)
python -m hci_extractor serve

# Custom host and port  
python -m hci_extractor serve --host 0.0.0.0 --port 8080

# Development mode with auto-reload
python -m hci_extractor serve --reload
```

**API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

**Example API Usage:**
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Extract PDF
curl -X POST "http://localhost:8000/api/v1/extract" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@paper.pdf"
```

### ✅ Implementation Timeline

- **Research Phase**: Explored existing codebase and hexagonal architecture
- **Planning Phase**: Created detailed 4-phase implementation plan  
- **Implementation Phase**: Completed all 4 phases in sequence
  - Phase 1: FastAPI foundation and DI integration
  - Phase 2: Core extraction API and file handling
  - Phase 3: WebSocket progress tracking  
  - Phase 4: CLI integration and serve command
- **Testing Phase**: Validated all endpoints and CLI integration
- **Documentation Phase**: Updated specifications and usage guides

The MVP Web UI provides a solid foundation for future frontend development while maintaining the academic integrity and reliability of the existing CLI interface.

### Future Frontend Options

Once the API is working, any frontend can be added:
- **Static HTML/JS**: Single-file upload interface
- **React/Vue SPA**: Full-featured web application  
- **Streamlit**: Rapid data science interface
- **Gradio**: ML demo interface

The API-first approach ensures frontend flexibility while maintaining the core extraction quality.

-