# Architecture Vision: From MVP to Production-Ready

## Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          CLI Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Extract   │  │    Batch    │  │   Export    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                 │                 │                │
│         └─────────────────┴─────────────────┘                │
│                           │                                  │
├───────────────────────────┼─────────────────────────────────┤
│                           ▼                                  │
│                      Core Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Models    │  │ Extraction  │  │  Analysis   │        │
│  │ (Immutable) │  │   - PDF     │  │ - Section   │        │
│  │  - Paper    │  │   - Text    │  │ - Pipeline  │        │
│  │  - Element  │  │             │  │ - Validator │        │
│  └─────────────┘  └──────┬──────┘  └──────┬──────┘        │
│                           │                 │                │
├───────────────────────────┼─────────────────┼───────────────┤
│                           ▼                 ▼                │
│                     Provider Layer                           │
│  ┌─────────────────────────────────────────────┐           │
│  │            LLMProvider (Abstract)            │           │
│  └───────────────────┬─────────────────────────┘           │
│                      │                                       │
│  ┌─────────────┐  ┌─┴─────────────┐  ┌─────────────┐     │
│  │   Gemini    │  │   OpenAI      │  │   Claude    │     │
│  │  Provider   │  │  (Future)     │  │  (Future)   │     │
│  └─────────────┘  └───────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────┘

Issues:
- Hardcoded configuration
- Mutable state in providers
- Tight coupling to file system
- No caching layer
- Mixed responsibilities
```

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Interface Layer                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │   CLI   │  │   API   │  │   Web   │  │  SDK    │      │
│  │         │  │ (Future)│  │ (Future)│  │ (Future)│      │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘      │
│       └─────────────┴─────────────┴─────────────┘          │
│                           │                                  │
│                      Event Bus                               │
│  ┌─────────────────────────────────────────────────┐       │
│  │  DomainEvents: Started|Processed|Completed|Failed│       │
│  └─────────────────────────────────────────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Extractor  │  │   Analyzer   │  │   Exporter   │     │
│  │   Service    │  │   Service    │  │   Service    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘             │
│                           │                                  │
├───────────────────────────┼─────────────────────────────────┤
│                           ▼                                  │
│                     Domain Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Immutable  │  │  Business   │  │   Domain    │        │
│  │   Models    │  │    Rules    │  │   Events    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                 Infrastructure Layer                         │
│  ┌──────────────────────────────────────────────────┐      │
│  │              Abstractions (Ports)                 │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │      │
│  │  │ Storage  │  │   LLM    │  │  Cache   │      │      │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘      │      │
│  └───────┼──────────────┼──────────────┼────────────┘      │
│          │              │              │                     │
│  ┌───────▼────┐  ┌─────▼─────┐  ┌────▼─────┐             │
│  │   Local    │  │  Gemini   │  │  Memory  │             │
│  │    FS      │  │ Provider  │  │  Cache   │             │
│  ├────────────┤  ├───────────┤  ├──────────┤             │
│  │    S3      │  │  OpenAI   │  │  Redis   │             │
│  │  (Future)  │  │ (Future)  │  │ (Future) │             │
│  └────────────┘  └───────────┘  └──────────┘             │
├─────────────────────────────────────────────────────────────┤
│                  Cross-Cutting Concerns                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Config  │  │ Metrics  │  │  Health  │  │  Retry   │  │
│  │ Service  │  │Collector │  │ Checker  │  │ Handler  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Key Architectural Improvements

### 1. **Hexagonal Architecture**
- Core domain is isolated from external concerns
- Ports (interfaces) and adapters pattern
- Easy to test and extend

### 2. **Event-Driven Communication**
- Loose coupling between components
- Easy to add new features without modifying existing code
- Enables async processing and monitoring

### 3. **Immutable Domain Model**
```python
# All domain objects are immutable
@dataclass(frozen=True)
class Paper:
    paper_id: str
    title: str
    authors: tuple[str, ...]
    
    def with_title(self, new_title: str) -> "Paper":
        """Return new Paper with updated title."""
        return Paper(
            paper_id=self.paper_id,
            title=new_title,
            authors=self.authors
        )
```

### 4. **Configuration as First-Class Citizen**
```python
# Centralized, immutable configuration
@dataclass(frozen=True)
class Config:
    extraction: ExtractionConfig
    analysis: AnalysisConfig
    export: ExportConfig
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load from environment."""
        return cls(...)
```

### 5. **Dependency Injection Container**
```python
# Simple DI container for wiring
class Container:
    def __init__(self, config: Config):
        self.config = config
        self._storage = self._create_storage()
        self._cache = self._create_cache()
        self._llm_provider = self._create_llm_provider()
    
    def extractor_service(self) -> ExtractorService:
        return ExtractorService(
            storage=self._storage,
            cache=self._cache,
            config=self.config.extraction
        )
```

## Benefits of Target Architecture

### 1. **Testability**
- Every component can be tested in isolation
- No need for external resources in unit tests
- Clear boundaries make mocking simple

### 2. **Scalability**
- Caching reduces redundant processing
- Event-driven allows horizontal scaling
- Storage abstraction enables cloud deployment

### 3. **Maintainability**
- Single responsibility for each component
- Changes don't ripple through the system
- Clear dependency flow

### 4. **Extensibility**
- New LLM providers just implement interface
- New storage backends are plug-and-play
- New export formats don't affect core logic

### 5. **Observability**
- Events provide natural monitoring points
- Metrics collector tracks all operations
- Health checks ensure system reliability

## Migration Path

### Phase 1: Foundation (Current Sprint)
- Extract configuration
- Implement event bus
- Create abstraction layer

### Phase 2: Decoupling (Next Sprint)
- Move to hexagonal architecture
- Implement storage abstraction
- Add caching layer

### Phase 3: Enhancement (Future)
- Add web API
- Implement additional providers
- Cloud deployment support

This architecture ensures the MVP can evolve into a production system without major rewrites, maintaining code quality and team velocity throughout the journey.