# Architecture Improvement Plan for Long-Term MVP Viability

## Executive Summary

This plan addresses architectural improvements to ensure the HCI Paper Extractor remains maintainable, scalable, and robust as an MVP that could evolve into a production system.

## Core Principles

1. **Low Coupling**: Modules should depend on abstractions, not concrete implementations
2. **High Cohesion**: Each module should have a single, well-defined responsibility
3. **Immutable Design**: All data should be immutable; operations return new objects
4. **Fail-Safe Defaults**: The system should degrade gracefully
5. **Configuration Over Code**: Behavior should be configurable, not hardcoded

## Priority 1: Critical Improvements (Week 1)

### 1.1 Decouple Configuration

**Problem**: Hardcoded paths, limits, and settings throughout the codebase.

**Solution**: Introduce a configuration service.

```python
# src/hci_extractor/core/config.py
from dataclasses import dataclass
from typing import Optional
import os
from pathlib import Path

@dataclass(frozen=True)
class ExtractorConfig:
    """Immutable configuration for the extractor."""
    max_concurrent_operations: int = 3
    chunk_size: int = 10000
    chunk_overlap: int = 500
    retry_max_attempts: int = 3
    retry_timeout_seconds: float = 60.0
    prompts_directory: Path = Path(__file__).parent.parent.parent / "prompts"
    cache_enabled: bool = False
    cache_directory: Optional[Path] = None
    
    @classmethod
    def from_env(cls) -> "ExtractorConfig":
        """Create config from environment variables."""
        return cls(
            max_concurrent_operations=int(os.getenv("HCI_MAX_CONCURRENT", "3")),
            chunk_size=int(os.getenv("HCI_CHUNK_SIZE", "10000")),
            cache_enabled=os.getenv("HCI_CACHE_ENABLED", "false").lower() == "true",
        )
```

### 1.2 Extract JSON Recovery Logic

**Problem**: Complex JSON recovery logic embedded in GeminiProvider.

**Solution**: Create a dedicated utility.

```python
# src/hci_extractor/utils/json_recovery.py
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class JsonRecoveryHandler:
    """Handles recovery from malformed JSON responses."""
    
    @staticmethod
    def attempt_recovery(
        response_text: str, 
        original_error: json.JSONDecodeError
    ) -> Optional[Dict[str, Any]]:
        """Attempt to recover valid JSON from malformed response."""
        # Move the 45+ lines of recovery logic here
        # Make it testable and reusable
```

### 1.3 Make Providers Stateless

**Problem**: Providers maintain mutable state for usage tracking.

**Solution**: Extract metrics to a separate collector.

```python
# src/hci_extractor/core/metrics.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

@dataclass(frozen=True)
class LLMUsageMetric:
    """Immutable record of a single LLM usage."""
    timestamp: datetime
    provider: str
    tokens_used: int
    response_time: float
    success: bool

class MetricsCollector:
    """Collects metrics without mutating provider state."""
    
    def __init__(self):
        self._metrics: List[LLMUsageMetric] = []
    
    def record(self, metric: LLMUsageMetric) -> None:
        """Record a new metric."""
        self._metrics.append(metric)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get immutable summary of metrics."""
        return {
            "total_requests": len(self._metrics),
            "total_tokens": sum(m.tokens_used for m in self._metrics),
            "success_rate": sum(1 for m in self._metrics if m.success) / len(self._metrics)
        }
```

## Priority 2: Reduce Coupling (Week 2)

### 2.1 Introduce Domain Events

**Problem**: Components need to communicate without tight coupling.

**Solution**: Event-driven architecture for cross-cutting concerns.

```python
# src/hci_extractor/core/events.py
from dataclasses import dataclass
from typing import Protocol, List
from datetime import datetime

@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    occurred_at: datetime
    
@dataclass(frozen=True)
class ExtractionStarted(DomainEvent):
    """Fired when extraction begins."""
    pdf_path: str
    paper_id: str

@dataclass(frozen=True)
class SectionProcessed(DomainEvent):
    """Fired when a section is processed."""
    paper_id: str
    section_type: str
    elements_found: int

class EventHandler(Protocol):
    """Protocol for event handlers."""
    def handle(self, event: DomainEvent) -> None: ...

class EventBus:
    """Simple event bus for decoupled communication."""
    
    def __init__(self):
        self._handlers: Dict[type, List[EventHandler]] = {}
    
    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers."""
        for handler in self._handlers.get(type(event), []):
            handler.handle(event)
```

### 2.2 Abstract File System Access

**Problem**: Direct file system access limits deployment options.

**Solution**: Introduce storage abstraction.

```python
# src/hci_extractor/core/storage.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Protocol

class StorageBackend(ABC):
    """Abstract storage interface."""
    
    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Read file contents."""
        pass
    
    @abstractmethod
    async def write(self, path: str, content: bytes) -> None:
        """Write file contents."""
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        pass

class LocalFileStorage(StorageBackend):
    """Local file system implementation."""
    
    async def read(self, path: str) -> bytes:
        with open(path, 'rb') as f:
            return f.read()

# Future: S3Storage, AzureStorage, etc.
```

## Priority 3: Improve Cohesion (Week 3)

### 3.1 Split Section Processor Responsibilities

**Problem**: LLMSectionProcessor handles too many concerns.

**Solution**: Separate into focused components.

```python
# src/hci_extractor/core/processing/chunking.py
@dataclass(frozen=True)
class TextChunk:
    """Immutable text chunk."""
    text: str
    start_index: int
    end_index: int
    chunk_number: int
    total_chunks: int

class TextChunker:
    """Handles text chunking logic."""
    
    def __init__(self, config: ExtractorConfig):
        self.chunk_size = config.chunk_size
        self.overlap = config.chunk_overlap
    
    def chunk_text(self, text: str) -> tuple[TextChunk, ...]:
        """Split text into immutable chunks."""
        # Chunking logic here

# src/hci_extractor/core/processing/retry.py
class RetryHandler:
    """Centralized retry logic."""
    
    def __init__(self, config: ExtractorConfig):
        self.max_attempts = config.retry_max_attempts
        self.timeout = config.retry_timeout_seconds
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Execute operation with retry logic."""
        # Consolidated retry logic here
```

### 3.2 Introduce Result Cache

**Problem**: No caching of expensive operations.

**Solution**: Optional caching layer.

```python
# src/hci_extractor/core/caching.py
from abc import ABC, abstractmethod
from typing import Optional, Any
import hashlib

class CacheKey:
    """Immutable cache key."""
    
    @staticmethod
    def for_pdf(path: str) -> str:
        """Generate cache key for PDF extraction."""
        return hashlib.sha256(path.encode()).hexdigest()
    
    @staticmethod
    def for_section(paper_id: str, section_type: str, text_hash: str) -> str:
        """Generate cache key for section processing."""
        return hashlib.sha256(
            f"{paper_id}:{section_type}:{text_hash}".encode()
        ).hexdigest()

class Cache(ABC):
    """Abstract cache interface."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Store in cache."""
        pass

class NoOpCache(Cache):
    """No-op cache for when caching is disabled."""
    
    async def get(self, key: str) -> Optional[Any]:
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        pass
```

## Priority 4: Clean Up Technical Debt (Week 4)

### 4.1 Remove Legacy Structure
- Delete empty directories: `extractors/`, `models/`, `pipeline/`
- Move `prompts/` directory under `src/hci_extractor/` for consistency
- Consolidate `utils/` or expand with more utilities

### 4.2 Improve Error Handling

```python
# src/hci_extractor/core/errors.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ErrorContext:
    """Immutable error context."""
    operation: str
    paper_id: Optional[str]
    section_type: Optional[str]
    details: dict

class ExtractorError(Exception):
    """Base exception with context."""
    
    def __init__(self, message: str, context: ErrorContext):
        super().__init__(message)
        self.context = context
```

### 4.3 Add Health Checks

```python
# src/hci_extractor/core/health.py
from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class HealthStatus:
    """Immutable health status."""
    healthy: bool
    checks: tuple[str, ...]
    
@dataclass(frozen=True)
class ComponentHealth:
    """Health of a single component."""
    name: str
    healthy: bool
    message: str

class HealthChecker:
    """System health checker."""
    
    async def check_all(self) -> HealthStatus:
        """Check health of all components."""
        checks = []
        
        # Check PDF extractor
        pdf_health = await self._check_pdf_extractor()
        checks.append(pdf_health)
        
        # Check LLM provider
        llm_health = await self._check_llm_provider()
        checks.append(llm_health)
        
        return HealthStatus(
            healthy=all(c.healthy for c in checks),
            checks=tuple(f"{c.name}: {c.message}" for c in checks)
        )
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Implement configuration service
- [ ] Extract JSON recovery logic
- [ ] Make providers stateless
- [ ] Add metrics collector

### Week 2: Decoupling
- [ ] Implement event system
- [ ] Add storage abstraction
- [ ] Create caching layer

### Week 3: Cohesion
- [ ] Split section processor
- [ ] Centralize retry logic
- [ ] Implement health checks

### Week 4: Cleanup
- [ ] Remove legacy directories
- [ ] Improve error context
- [ ] Add integration tests for new components
- [ ] Update documentation

## Success Metrics

1. **Coupling Reduction**
   - No hardcoded paths or limits
   - All components depend on abstractions
   - Event-driven communication for cross-cutting concerns

2. **Cohesion Improvement**
   - Each class has a single responsibility
   - No class exceeds 150 lines
   - Clear module boundaries

3. **Immutability**
   - Zero mutable state in core business logic
   - All data structures are immutable
   - Operations return new objects

4. **Testability**
   - 100% unit test coverage for new components
   - All components can be tested in isolation
   - No test requires external resources

## Long-Term Benefits

1. **Maintainability**: Clear responsibilities make changes easier
2. **Scalability**: Caching and async patterns support growth
3. **Deployability**: Storage abstraction enables cloud deployment
4. **Reliability**: Health checks and metrics enable monitoring
5. **Extensibility**: New providers/formats can be added easily

This plan transforms the MVP into a robust foundation that can evolve into a production system while maintaining code quality and architectural integrity.