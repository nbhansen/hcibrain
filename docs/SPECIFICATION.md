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
## Research Features & Academic Workflow Support

### What Are Research Features?

Research features are advanced analytical capabilities that go beyond basic text extraction to support sophisticated academic research workflows. They transform raw extracted data into insights that enable systematic literature reviews, meta-analyses, and research gap identification.

### Core Research Capabilities

#### 1. **Literature Synthesis Support**
- **Cross-Paper Analysis**: Compare findings, claims, and methods across multiple papers
- **Contradiction Detection**: Identify conflicting claims or contradictory results
- **Consensus Building**: Highlight areas of agreement across literature
- **Evidence Triangulation**: Cross-validate findings from different research approaches

#### 2. **Research Gap Identification** 
- **Understudied Areas**: Identify topics with limited research coverage
- **Methodological Gaps**: Highlight missing research approaches or populations
- **Theoretical Gaps**: Detect areas lacking theoretical foundation
- **Temporal Gaps**: Find research areas that haven't been updated recently

#### 3. **Systematic Literature Review Support**
- **Automated Screening**: Pre-filter papers based on inclusion/exclusion criteria
- **Data Extraction Workflows**: Structured templates for systematic reviews
- **Inter-rater Reliability**: Tools for validating extraction consistency
- **PRISMA Compliance**: Export formats aligned with systematic review standards

#### 4. **Meta-Analysis Preparation**
- **Effect Size Extraction**: Identify and extract quantitative results for meta-analysis
- **Statistical Data Mining**: Extract p-values, confidence intervals, sample sizes
- **Study Characteristics**: Capture population demographics, intervention details
- **Quality Assessment**: Support methodological quality evaluation

### Academic Workflow Integration

#### **Workflow 1: Systematic Literature Review**
```
1. Batch extract 50-200 papers → HCI Extractor
2. Export structured data → CSV/JSON
3. Import into analysis tool → R/Python/Excel
4. Apply research feature analysis → Gap identification
5. Generate synthesis report → Research insights
```

#### **Workflow 2: Meta-Analysis Preparation**
```
1. Extract quantitative findings → HCI Extractor
2. Validate effect sizes → Research features
3. Export meta-analysis dataset → Statistical software
4. Conduct meta-analysis → External tools
```

#### **Workflow 3: Research Gap Analysis**
```
1. Process literature corpus → HCI Extractor
2. Identify understudied areas → Gap analysis features
3. Map research landscape → Visualization tools
4. Plan future research → Strategic decisions
```

### Concrete Use Cases

#### **For Systematic Review Researchers:**
- **Question**: "What user interface design patterns have been validated for accessibility?"
- **Process**: Extract all UI-related claims and methods, identify validation approaches
- **Output**: Structured comparison of validation methods and their effectiveness

#### **For Meta-Analysis Researchers:**
- **Question**: "What is the average effect size of gamification on user engagement?"
- **Process**: Extract quantitative findings from gamification studies
- **Output**: Dataset ready for meta-analytic synthesis

#### **For Literature Gap Analysis:**
- **Question**: "What aspects of remote work in HCI are understudied?"
- **Process**: Map research topics and identify areas with limited coverage
- **Output**: Research opportunity map with gap identification

### Current Research Features Status

#### ✅ **Available Now (MVP Features):**
- **Verbatim Extraction**: Maintains academic integrity for literature synthesis
- **Cross-Paper Comparison**: Manual comparison enabled through structured exports
- **Classification Accuracy**: Good performance for identifying research elements
- **Batch Processing**: Efficient processing of literature sets (10-50 papers)

#### 🚧 **Next Priority (Research Features Phase 1):**
- **Research Gap Identification**: Automated detection of understudied areas
- **Contradiction Detection**: Identify conflicting claims across papers
- **Research Landscape Mapping**: Visualize research coverage and gaps
- **Synthesis Support Tools**: Templates and workflows for systematic reviews

### Research Features Roadmap

#### **Phase 1: Gap Analysis & Synthesis (Next 6 months)**
- Automated research gap identification algorithms
- Cross-paper contradiction detection
- Research landscape visualization tools
- Systematic review workflow templates

#### **Phase 2: Meta-Analysis Support (6-18 months)**
- Quantitative data extraction (effect sizes, p-values)
- Statistical significance detection and validation
- Meta-analysis dataset preparation tools
- Integration with statistical software (R, SPSS)

#### **Phase 3: Advanced Research Intelligence (18+ months)**
- Longitudinal research trend analysis
- Citation network analysis and impact assessment
- Predictive gap identification using ML
- Collaborative research planning tools

### Integration with Academic Tools

#### **Reference Managers:**
- Export citations compatible with Zotero, Mendeley, EndNote
- Maintain bidirectional linking between extractions and source papers

#### **Statistical Software:**
- Direct export to R data frames for meta-analysis
- SPSS-compatible datasets for quantitative synthesis
- Python pandas integration for data science workflows

#### **Visualization Tools:**
- Research landscape maps showing coverage and gaps
- Interactive filtering and exploration of extracted data
- Dashboard views for research progress tracking

## Development Environment

### Virtual Environment (Required)
**Always use a virtual environment** for this project to ensure dependency isolation and reproducible builds.

## Non-Goals (MVP Boundaries)

- **No Summarization**: Extract verbatim, never summarize or paraphrase
- **No Synthesis**: Provide structured data, don't synthesize insights
- **No Quality Assessment**: Don't score paper quality or methodological rigor
- **No Real-time Collaboration**: Single-user CLI tool
- **No Citation Networks**: Focus on content extraction, not reference analysis

## Current Implementation Status (December 2025)

### ✅ PRODUCTION READY WITH ENTERPRISE ARCHITECTURE

The HCI Paper Extractor is production-ready for academic research workflows with enterprise-grade architecture. All core features are implemented with hexagonal architecture compliance and comprehensive test coverage.

**Core Features:**
- **Immutable Data Models**: All data structures use frozen dataclasses for thread safety
- **PDF Processing**: Reliable text extraction with section detection 
- **LLM Integration**: Provider-agnostic design, currently using Gemini API
- **Batch Processing**: Concurrent handling of multiple papers with progress tracking
- **Academic Integrity**: Verbatim extraction with validation
- **Smart Classification**: Good accuracy for identifying claims, findings, and methods
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

**CLI Commands:**
- `extract`: Process single papers with LLM analysis
- `batch`: Process multiple papers concurrently
- `export`: Generate CSV/JSON/Markdown outputs
- `validate`: Check if PDFs can be processed
- `diagnose`: System health check
- `test-config`: Validate configuration

**Quality Standards Met:**
- **Academic Integrity**: Verbatim accuracy with validation
- **Classification Performance**: Good accuracy for claims, findings, and methods
- **Architecture Compliance**: Complete hexagonal architecture implementation
- **Code Quality**: Zero global state, full immutability, comprehensive DI
- **Error Handling**: Robust error handling with graceful degradation
- **User Experience**: Clear error messages that help users fix issues
- **Performance**: Efficient processing (typically under 30 seconds per paper)
- **Compatibility**: Handles real-world academic papers including complex formatting
- **Maintainability**: Clean architecture enables easy testing and feature addition
- **Type Safety**: Full mypy compliance with comprehensive type annotations

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

### **Next Priority - Research Features Implementation:**

Now that architecture compliance is complete, the focus shifts to implementing the Research Features defined in the "Research Features & Academic Workflow Support" section above.

**Phase 1 Implementation Priority:**
1. **Research Gap Identification Engine** (High Impact)
   - Implement automated detection algorithms for understudied areas
   - Build cross-paper comparison and contradiction detection
   - Create research landscape mapping and visualization
   - Develop systematic review workflow templates

*See the comprehensive Research Features section above for detailed definitions, use cases, and implementation roadmap.*

### **Technical Infrastructure Enhancements:**
*Technical improvements that support research features and platform expansion*

1. **Additional LLM Providers** (Medium Priority)
   - OpenAI GPT-4 support for improved extraction quality
   - Anthropic Claude support for diverse LLM capabilities  
   - Local model options (Ollama) for privacy-sensitive research

2. **Platform & User Interface** (Lower Priority)
   - Web-based interface for result exploration
   - Interactive filtering and search capabilities
   - Collaborative review features for research teams

*Note: Research Features (gap analysis, meta-analysis support, etc.) are detailed in the "Research Features & Academic Workflow Support" section above, including the 3-phase implementation roadmap.*

### **Complex Future Features:**
*Features that would be valuable but require significant R&D and are not immediately prioritized*

1. **Advanced Statistical Data Extraction** (Complex R&D)
   - Automated p-value and effect size extraction from figures/tables
   - Statistical test identification and validation
   - Quantitative data validation and quality assessment
   - *Note: Very challenging to implement reliably due to diverse reporting formats*

2. **Enhanced Citation Network Analysis** (Complex R&D)
   - Deep citation parsing and cross-reference validation
   - Research impact and influence mapping
   - Automated bibliography generation and management
   - *Note: Many specialized tools already exist for citation analysis*


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