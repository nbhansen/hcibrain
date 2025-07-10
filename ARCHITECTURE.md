# HCIBrain Architecture Documentation

**Version**: 2.0  
**Date**: January 9, 2025  
**Status**: Production Ready  

## Overview

HCIBrain is a research paper processing system built using **hexagonal architecture** (ports and adapters) with strict **immutability principles** and **dependency injection**. The system extracts structured data from academic papers using LLM providers and provides both CLI and web interfaces.

## Architecture Principles

### 1. **Hexagonal Architecture (Clean Architecture)**
- **Core Domain**: Pure business logic with no external dependencies
- **Application Layer**: Orchestrates domain operations
- **Infrastructure Layer**: External adapters (databases, APIs, file systems)
- **Presentation Layer**: User interfaces (CLI, web)

### 2. **Immutability First**
- All data structures are immutable (`@dataclass(frozen=True)`)
- No state mutations after object creation
- Functional state updates with new object creation
- Immutable default factories using `types.MappingProxyType`

### 3. **Dependency Injection**
- No global state or singletons
- All dependencies injected through constructors
- Centralized DI container with configurable factories
- Clear separation between configuration and implementation

### 4. **Event-Driven Communication**
- Domain events for loose coupling
- Event bus for component communication
- Immutable event objects
- Async event processing

## Project Structure

```
packages/backend/
├── src/hci_extractor/
│   ├── core/                    # Core domain layer
│   │   ├── analysis/           # Analysis domain services
│   │   ├── config/             # Configuration objects
│   │   ├── di_container.py     # Dependency injection
│   │   ├── domain/             # Business logic
│   │   ├── events/             # Domain events
│   │   ├── extraction/         # PDF extraction
│   │   ├── models/             # Domain models
│   │   └── text/               # Text processing
│   ├── infrastructure/         # Infrastructure adapters
│   │   ├── configuration_service.py
│   │   └── caching/
│   ├── providers/              # LLM provider adapters
│   │   ├── gemini_provider.py
│   │   └── provider_config.py
│   ├── cli/                    # Command line interface
│   │   ├── commands.py
│   │   └── config_builder.py
│   ├── web/                    # Web interface
│   │   ├── main.py
│   │   └── progress.py
│   ├── prompts/                # Prompt management
│   └── utils/                  # Utilities
├── tests/                      # Test suite
├── prompts/                    # Prompt templates
└── config.yaml                 # Configuration
```

## Layer Descriptions

### Core Domain Layer (`src/hci_extractor/core/`)

**Purpose**: Contains pure business logic with no external dependencies.

**Key Components**:
- **Domain Models**: Immutable data structures representing core concepts
- **Domain Services**: Business logic operations
- **Events**: Domain event definitions
- **Configuration**: Type-safe configuration objects

**Principles**:
- No imports from infrastructure or presentation layers
- All objects are immutable
- Pure functions and side-effect-free operations
- Domain events for state changes

### Infrastructure Layer (`src/hci_extractor/infrastructure/`)

**Purpose**: Adapters for external systems and services.

**Key Components**:
- **ConfigurationService**: Centralized configuration management
- **Caching**: File-based caching implementations
- **Database Adapters**: (Future) Database connections

**Principles**:
- Implements ports defined in core domain
- No business logic
- Handles external system complexity
- Dependency injection for all external connections

### Providers Layer (`src/hci_extractor/providers/`)

**Purpose**: LLM provider adapters following adapter pattern.

**Key Components**:
- **GeminiProvider**: Google Gemini API integration
- **ProviderConfig**: Provider-specific configurations
- **LLMProvider**: Abstract interface for all providers

**Principles**:
- Configurable provider selection
- Uniform interface for all LLM providers
- Error handling and retry logic
- Rate limiting and quota management

### Presentation Layer (`src/hci_extractor/cli/`, `src/hci_extractor/web/`)

**Purpose**: User interfaces and external API endpoints.

**Key Components**:
- **CLI Commands**: Command-line interface
- **Web API**: FastAPI-based web interface
- **Progress Tracking**: Real-time progress updates

**Principles**:
- Thin layer with minimal logic
- Delegates to domain services
- Immutable request/response objects
- Async processing for long-running operations

## Configuration Management

### Centralized Configuration
- **Single Source**: `config.yaml` file
- **Type Safety**: `ExtractorConfig` with frozen dataclasses
- **Environment Override**: Environment variables take precedence
- **Validation**: Comprehensive configuration validation

### Configuration Hierarchy
1. **CLI Arguments** (highest precedence)
2. **Environment Variables**
3. **Configuration File**
4. **Default Values** (lowest precedence)

### Environment Access
- **Centralized**: All environment access through `ConfigurationService`
- **No Direct Access**: No `os.environ` calls in business logic
- **Testable**: Easy to mock and test

## Dependency Injection

### DI Container (`src/hci_extractor/core/di_container.py`)

**Features**:
- **Service Lifetimes**: Singleton and transient services
- **Factory Functions**: Complex object creation
- **Circular Dependency Detection**: Prevents infinite loops
- **Type Safety**: Full type annotations

**Registration Patterns**:
```python
# Singleton registration
container.register_singleton(EventBus, EventBus)

# Factory registration
container.register_factory(LLMProvider, create_llm_provider)

# Instance registration
container.register_instance(ExtractorConfig, config)
```

### Configuration-Driven Factories
- **Provider Selection**: Configurable LLM provider types
- **Service Creation**: Configuration-based service instantiation
- **Dependency Resolution**: Automatic dependency injection

## Immutability Patterns

### Data Structures
```python
@dataclass(frozen=True)
class PaperSection:
    title: str
    content: str
    elements: tuple[Element, ...] = ()
    
    def with_elements(self, elements: tuple[Element, ...]) -> "PaperSection":
        return dataclasses.replace(self, elements=elements)
```

### State Management
```python
@dataclass(frozen=True)
class ProgressState:
    current_progress: float
    sections_processed: int = 0
    
    def with_progress(self, progress: float) -> "ProgressState":
        return ProgressState(
            current_progress=progress,
            sections_processed=self.sections_processed,
        )
```

### Default Factories
```python
@dataclass(frozen=True)
class JsonRecoveryOptions:
    strategies: tuple[str, ...] = ("all",)
    metadata: Dict[str, Any] = field(
        default_factory=lambda: types.MappingProxyType({})
    )
```

## Event-Driven Architecture

### Domain Events
- **Immutable**: All events are frozen dataclasses
- **Descriptive**: Clear event names and payloads
- **Decoupled**: No direct dependencies between components

### Event Bus
- **Central Hub**: Single event distribution point
- **Async Processing**: Non-blocking event handling
- **Error Isolation**: Failed handlers don't affect others

### Event Patterns
```python
@dataclass(frozen=True)
class PaperProcessingStarted:
    paper_id: str
    timestamp: datetime
    
@dataclass(frozen=True)  
class SectionProcessingCompleted:
    paper_id: str
    section_name: str
    elements_found: int
```

## Provider Integration

### LLM Provider Abstraction
```python
class LLMProvider(ABC):
    @abstractmethod
    async def process_section(self, section: PaperSection) -> ProcessingResult:
        pass
```

### Configurable Provider Selection
```yaml
api:
  provider_type: "gemini"  # "gemini", "openai", "anthropic"
  gemini_api_key: "your-key"
```

### Provider Factory
```python
def create_llm_provider(config: ExtractorConfig) -> LLMProvider:
    provider_type = config.api.provider_type.lower()
    
    if provider_type == "gemini":
        return GeminiProvider(...)
    elif provider_type == "openai":
        return OpenAIProvider(...)
    else:
        raise ValueError(f"Unsupported provider: {provider_type}")
```

## Testing Architecture

### Test Organization
- **Unit Tests**: Pure domain logic testing
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Full workflow testing

### Testability Features
- **Dependency Injection**: Easy mocking of dependencies
- **Immutable Objects**: Predictable test data
- **Pure Functions**: Deterministic testing
- **Event-Driven**: Isolated component testing

## Performance Considerations

### Concurrent Processing
- **Async Operations**: Non-blocking I/O operations
- **Parallel Processing**: Multiple section processing
- **Rate Limiting**: Configurable request throttling

### Memory Management
- **Immutable Objects**: Efficient object reuse
- **Streaming Processing**: Large file handling
- **Caching**: Configurable result caching

## Security Measures

### Configuration Security
- **No Hardcoded Secrets**: All secrets from environment
- **Input Validation**: Comprehensive input validation
- **Error Handling**: Secure error responses

### API Security
- **Rate Limiting**: Request throttling
- **Input Sanitization**: XSS prevention
- **Authentication**: (Future) API key validation

## Monitoring and Observability

### Logging
- **Structured Logging**: JSON-formatted logs
- **Log Levels**: Configurable verbosity
- **Context Propagation**: Request tracing

### Metrics
- **Processing Metrics**: Success/failure rates
- **Performance Metrics**: Processing times
- **Resource Metrics**: Memory and CPU usage

## Future Enhancements

### Planned Improvements
1. **Database Integration**: Persistent storage
2. **Authentication System**: User management
3. **API Rate Limiting**: Advanced throttling
4. **Distributed Processing**: Horizontal scaling
5. **Monitoring Dashboard**: Real-time metrics

### Architecture Evolution
- **Microservices**: Service decomposition
- **Message Queues**: Async communication
- **API Gateway**: Centralized routing
- **Container Orchestration**: Kubernetes deployment

## Development Guidelines

### Code Standards
- **Immutability**: All new code must be immutable
- **Dependency Injection**: No global state
- **Type Safety**: Full type annotations
- **Documentation**: Comprehensive docstrings

### Architecture Compliance
- **Layer Violations**: Core cannot import from infrastructure
- **Dependency Direction**: Dependencies point inward
- **Testing**: All code must be testable
- **Configuration**: No hardcoded values

## Recent Architecture Improvements

### January 9, 2025 - Error Handling Simplification

**Problem**: Complex error classification system was over-engineered and causing import dependencies that prevented CLI loading.

**Solution**: Simplified error handling by removing complex classification and implementing basic pattern matching.

**Changes Made**:
- **Removed Complex Error Classification**: Eliminated `ErrorClassifier` and `ErrorCategory` classes from global state
- **Simplified `user_error_translator.py`**: Replaced complex classification with simple pattern matching for common error types
- **Fixed Import Errors**: Resolved `ImportError: cannot import name 'classify_error'` that was preventing CLI from loading
- **Maintained User Experience**: Error messages still provide helpful guidance and remediation steps
- **Improved Maintainability**: Reduced complexity while maintaining functionality

**Files Modified**:
- `src/hci_extractor/utils/user_error_translator.py` - Simplified error analysis using basic pattern matching
- `src/hci_extractor/core/analysis/section_processor.py` - Simplified error handling to use basic logging
- `src/hci_extractor/utils/error_classifier.py` - Removed global instance functions
- `src/hci_extractor/core/di_container.py` - Removed ErrorClassifier registration

**Impact**: 
- ✅ CLI loads successfully
- ✅ Error handling works with simpler, more maintainable code
- ✅ Follows architectural principle of letting LLM handle complex understanding
- ✅ Reduced technical debt by removing unused complexity

**Pattern Matching Approach**: The new system uses simple string pattern matching to categorize errors into types like:
- Timeout/Network issues
- Permission/Access errors  
- Memory/Resource constraints
- File not found errors
- API/Authentication problems
- Generic processing errors

This aligns with the user's guidance to "leave anything like sections and understanding what's going on to the LLM" rather than maintaining complex classification logic.

### Previous Architecture Work Completed

**All Critical Global State Violations Fixed**:
- ✅ Removed global `_metrics_collector` instance
- ✅ Removed global `_error_classifier` instance  
- ✅ Converted CLI services to factory functions
- ✅ Fixed ApiConfig constructor missing provider_type parameter
- ✅ Added all services to DI container

**Status**: All high-priority architecture violations have been resolved. The system now follows strict hexagonal architecture principles with no global state.

## Conclusion

The HCIBrain architecture provides a robust, maintainable, and scalable foundation for academic paper processing. The combination of hexagonal architecture, immutability principles, and dependency injection creates a system that is both flexible and reliable.

The architecture successfully separates concerns, enables easy testing, and provides clear boundaries between different system components. With all critical violations resolved and error handling simplified, the system is ready for production use and future enhancements.

The recent simplification of error handling demonstrates the architectural principle of preferring simplicity over complexity, especially when the LLM can handle understanding tasks more effectively than hardcoded classification logic.

## Major Architectural Decisions

### Text-First Rendering Architecture

**Decision**: Replace PDF coordinate mapping with text-based rendering where the full extracted PDF text is displayed with inline highlights.

**Problem Solved**: The original PDF coordinate mapping approach had fundamental issues:
- **PyMuPDF ↔ PDF.js mismatch**: Complex transformation between backend and frontend coordinate systems
- **Page boundary issues**: LLM detects elements on page 12, coordinate mapper finds text on page 2
- **Scaling problems**: Viewport scaling, zoom levels, responsive design complications
- **User experience issues**: Highlight misplacement, mobile unfriendly, blocked text selection

**Solution Benefits**:
1. **Elimination of coordinate complexity**: No PyMuPDF ↔ PDF.js transformation needed
2. **Perfect text matching**: Direct string matching between LLM-extracted text and full PDF text
3. **Better user experience**: Continuous text flow, mobile-friendly, native selection
4. **Simplified maintenance**: Removed coordinate mapping complexity
5. **Better accessibility**: Screen readers work better with HTML text

**Implementation**: The full extracted PDF text is rendered as HTML with `<goal>`, `<method>`, and `<result>` tags embedded inline, styled with CSS for visual highlighting.

**Trade-offs Accepted**: Loss of visual layout (figures, tables, multi-column formatting) in favor of better text accessibility and mobile experience.