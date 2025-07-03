# Week 1 Implementation Plan: Foundation for Long-Term Viability

## Overview

Week 1 focuses on establishing the foundational infrastructure that will enable the HCI Paper Extractor to evolve from MVP to production-ready system without major rewrites.

## Goals

1. **Eliminate hardcoded values** through centralized configuration
2. **Remove mutable state** from providers using metrics collection
3. **Extract complex logic** into focused, testable utilities
4. **Establish event-driven patterns** for loose coupling

## Day 1: Configuration Service Implementation

### Morning: Core Configuration

**Tasks:**
1. ✅ Create `core/config.py` with immutable configuration objects
2. Integrate configuration into existing components
3. Remove all hardcoded values

**Implementation Steps:**

```python
# 1. Update PdfExtractor to use config
# src/hci_extractor/core/extraction/pdf_extractor.py
def __init__(self, config: Optional[ExtractorConfig] = None):
    self.config = config or get_config()
    self.max_file_size = self.config.extraction.max_file_size_mb * 1024 * 1024
    self.timeout = self.config.extraction.timeout_seconds

# 2. Update SectionDetector to use config
# src/hci_extractor/core/analysis/section_detector.py
def detect_sections(pdf_content: PdfContent, config: Optional[ExtractorConfig] = None) -> Tuple[DetectedSection, ...]:
    config = config or get_config()
    min_length = config.analysis.min_section_length
    # Remove hardcoded 50 character minimum

# 3. Update LLMSectionProcessor to use config
# src/hci_extractor/core/analysis/section_processor.py
def __init__(self, llm_provider: LLMProvider, config: Optional[ExtractorConfig] = None):
    self.config = config or get_config()
    self.llm_provider = llm_provider
    self.max_retries = self.config.retry.max_attempts
    self.timeout_seconds = self.config.analysis.section_timeout_seconds
    self.chunk_size = self.config.analysis.chunk_size
    self.chunk_overlap = self.config.analysis.chunk_overlap
```

### Afternoon: CLI Integration

**Tasks:**
1. Update CLI commands to use configuration
2. Add configuration override options
3. Create configuration validation

**Implementation:**

```python
# src/hci_extractor/cli/commands.py
@click.option('--config-file', type=click.Path(exists=True), help='Configuration file path')
@click.option('--config-override', multiple=True, help='Override config values (key=value)')
def extract(pdf_file, output, config_file, config_override, **kwargs):
    # Load configuration
    if config_file:
        config = ExtractorConfig.from_file(config_file)
    else:
        config = get_config()
    
    # Apply overrides
    if config_override:
        config = apply_overrides(config, config_override)
```

**Testing:**
- Unit tests for configuration loading
- Integration tests with overrides
- Validation of all configuration paths

## Day 2: Metrics Collection System

### Morning: Remove Mutable State from Providers

**Tasks:**
1. ✅ Create `core/metrics.py` with immutable metrics
2. Remove usage tracking from GeminiProvider
3. Integrate metrics collection

**Implementation Steps:**

```python
# 1. Update GeminiProvider to remove mutable state
# src/hci_extractor/providers/gemini_provider.py
class GeminiProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, config: Optional[ExtractorConfig] = None):
        super().__init__(
            rate_limit_delay=1.0,  # Will move to config
            max_retries=config.retry.max_attempts if config else 3
        )
        self.config = config or get_config()
        # Remove: self._requests_made = 0
        # Remove: self._tokens_used = 0
        # Remove: self._estimated_cost = 0.0

    async def analyze_section(self, section_text: str, section_type: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        # Use metrics context manager
        with LLMMetricsContext(
            provider="gemini",
            model=self.model_name,
            operation="analyze_section",
            section_type=section_type
        ) as metrics:
            # Existing logic...
            response = await self._make_api_request(prompt)
            
            # Record token usage
            metrics.tokens_input = len(prompt) // 4  # Estimate
            metrics.tokens_output = len(response.text) // 4  # Estimate
            
            return elements
```

### Afternoon: Event Integration

**Tasks:**
1. Integrate event publishing into core operations
2. Add event handlers for metrics collection
3. Create event logging

**Implementation:**

```python
# 1. Update extraction to publish events
# src/hci_extractor/core/analysis/simple_extractor.py
async def extract_paper_simple(pdf_path: str, llm_provider: Optional[LLMProvider] = None, paper_metadata: Optional[Dict[str, Any]] = None) -> ExtractionResult:
    event_bus = get_event_bus()
    paper_id = str(uuid4())
    
    # Publish extraction started
    event_bus.publish(ExtractionStarted(
        pdf_path=pdf_path,
        paper_id=paper_id,
        file_size_bytes=Path(pdf_path).stat().st_size
    ))
    
    try:
        # Existing extraction logic...
        result = await _do_extraction(...)
        
        # Publish completion
        event_bus.publish(ExtractionCompleted(
            paper_id=paper_id,
            pages_extracted=len(pdf_content.pages),
            characters_extracted=pdf_content.total_characters,
            duration_seconds=time.time() - start_time
        ))
        
        return result
    except Exception as e:
        event_bus.publish(ExtractionFailed(
            pdf_path=pdf_path,
            error_type=type(e).__name__,
            error_message=str(e)
        ))
        raise

# 2. Create metrics event handler
class MetricsEventCollector:
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
    
    def handle(self, event: DomainEvent) -> None:
        if isinstance(event, ExtractionCompleted):
            # Create extraction metric from event
            metric = ExtractionMetric(...)
            self.metrics_collector.record_extraction(metric)
```

## Day 3: Extract Complex Logic

### Morning: JSON Recovery Utility

**Tasks:**
1. Create `utils/json_recovery.py`
2. Extract JSON recovery logic from GeminiProvider
3. Add comprehensive tests

**Implementation:**

```python
# src/hci_extractor/utils/json_recovery.py
from typing import Optional, Dict, Any, List
import json
import re
import logging

logger = logging.getLogger(__name__)

class JsonRecoveryHandler:
    """Handles recovery from malformed JSON responses."""
    
    def __init__(self, config: Optional[ExtractorConfig] = None):
        self.config = config or get_config()
        self.max_recovery_attempts = 3
    
    def attempt_recovery(
        self,
        response_text: str,
        original_error: json.JSONDecodeError
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to recover valid JSON from malformed response.
        
        Tries multiple strategies:
        1. Fix unterminated strings
        2. Close unclosed arrays/objects
        3. Remove trailing commas
        4. Extract partial valid JSON
        """
        strategies = [
            self._fix_unterminated_strings,
            self._close_unclosed_structures,
            self._remove_trailing_commas,
            self._extract_partial_json,
        ]
        
        for strategy in strategies:
            try:
                recovered = strategy(response_text, original_error)
                if recovered:
                    return json.loads(recovered)
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _fix_unterminated_strings(
        self,
        text: str,
        error: json.JSONDecodeError
    ) -> Optional[str]:
        """Fix unterminated string errors."""
        if "Unterminated string" not in str(error):
            return None
        
        # Implementation moved from GeminiProvider
        # ... (45+ lines of recovery logic)
        
    # Additional recovery strategies...

# Update GeminiProvider to use utility
class GeminiProvider(LLMProvider):
    def __init__(self, ...):
        self.json_recovery = JsonRecoveryHandler(config)
    
    async def _make_api_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            response_data = json.loads(response.text)
        except json.JSONDecodeError as e:
            # Use recovery utility
            recovered_data = self.json_recovery.attempt_recovery(response.text, e)
            if recovered_data:
                logger.warning(f"Recovered from JSON error using {recovered_data.get('recovery_method', 'unknown')} strategy")
                return recovered_data
            else:
                raise LLMValidationError(f"Invalid JSON response: {e}")
```

### Afternoon: Retry Handler Consolidation

**Tasks:**
1. Create unified retry handler
2. Remove duplicate retry logic
3. Add exponential backoff with jitter

**Implementation:**

```python
# src/hci_extractor/utils/retry.py
import asyncio
import random
from typing import TypeVar, Callable, Optional, Any
from dataclasses import dataclass

T = TypeVar('T')

@dataclass(frozen=True)
class RetryResult:
    """Immutable result of a retry operation."""
    success: bool
    result: Optional[Any]
    attempts: int
    total_delay: float
    final_error: Optional[Exception]

class RetryHandler:
    """Unified retry handler with exponential backoff."""
    
    def __init__(self, config: Optional[ExtractorConfig] = None):
        self.config = config or get_config()
    
    async def execute_with_retry(
        self,
        operation: Callable[..., T],
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> T:
        """
        Execute operation with retry logic.
        
        Features:
        - Exponential backoff with jitter
        - Configurable max attempts
        - Event publishing for monitoring
        """
        last_error = None
        total_delay = 0.0
        
        for attempt in range(self.config.retry.max_attempts):
            try:
                result = await operation(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"{operation_name} succeeded after {attempt + 1} attempts")
                
                return result
                
            except Exception as e:
                last_error = e
                
                if attempt < self.config.retry.max_attempts - 1:
                    # Calculate delay with jitter
                    base_delay = self.config.retry.initial_delay_seconds
                    delay = base_delay * (self.config.retry.backoff_multiplier ** attempt)
                    delay = min(delay, self.config.retry.max_delay_seconds)
                    
                    # Add jitter (±25%)
                    jitter = delay * 0.25 * (2 * random.random() - 1)
                    delay += jitter
                    
                    logger.warning(
                        f"{operation_name} failed (attempt {attempt + 1}/"
                        f"{self.config.retry.max_attempts}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    await asyncio.sleep(delay)
                    total_delay += delay
        
        # All retries exhausted
        raise last_error

# Update LLMSectionProcessor to use unified retry
class LLMSectionProcessor(SectionProcessor):
    def __init__(self, llm_provider: LLMProvider, config: Optional[ExtractorConfig] = None):
        self.config = config or get_config()
        self.llm_provider = llm_provider
        self.retry_handler = RetryHandler(config)
    
    async def _process_with_retries(self, section: DetectedSection, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Use unified retry handler
        return await self.retry_handler.execute_with_retry(
            self._do_process_section,
            section,
            context,
            operation_name=f"process_{section.section_type}_section"
        )
```

## Day 4: Testing & Integration

### Morning: Unit Tests

**Tasks:**
1. Test configuration loading and validation
2. Test metrics collection
3. Test event publishing
4. Test JSON recovery strategies

**Test Plan:**

```python
# tests/test_config.py
def test_config_from_env():
    """Test configuration loads from environment."""
    with mock.patch.dict(os.environ, {
        'HCI_ANALYSIS_CHUNK_SIZE': '5000',
        'HCI_CACHE_ENABLED': 'true',
    }):
        config = ExtractorConfig.from_env()
        assert config.analysis.chunk_size == 5000
        assert config.cache.enabled is True

def test_config_immutability():
    """Test configuration objects are immutable."""
    config = ExtractorConfig.from_env()
    with pytest.raises(AttributeError):
        config.analysis.chunk_size = 9999

# tests/test_metrics.py
def test_metrics_collection():
    """Test metrics are collected correctly."""
    collector = MetricsCollector()
    
    with LLMMetricsContext("test", "model", "op") as ctx:
        ctx.tokens_input = 100
        ctx.tokens_output = 200
    
    summary = collector.get_llm_summary()
    assert summary.total_requests == 1
    assert summary.total_tokens == 300

# tests/test_events.py
@pytest.mark.asyncio
async def test_event_publishing():
    """Test events are published and handled."""
    bus = EventBus()
    received_events = []
    
    class TestHandler:
        def handle(self, event):
            received_events.append(event)
    
    bus.subscribe(ExtractionStarted, TestHandler())
    bus.publish(ExtractionStarted(
        pdf_path="test.pdf",
        paper_id="123",
        file_size_bytes=1000
    ))
    
    assert len(received_events) == 1
    assert isinstance(received_events[0], ExtractionStarted)
```

### Afternoon: Integration Testing

**Tasks:**
1. Test end-to-end with new configuration
2. Verify metrics collection in real extraction
3. Ensure events flow correctly
4. Performance testing

**Integration Tests:**

```python
# tests/test_integration_week1.py
@pytest.mark.asyncio
async def test_extraction_with_config_and_metrics():
    """Test extraction uses config and collects metrics."""
    # Create test configuration
    config = ExtractorConfig.for_testing(
        analysis=AnalysisConfig(chunk_size=1000),
        cache=CacheConfig(enabled=False)
    )
    set_config(config)
    
    # Set up metrics collection
    collector = get_metrics_collector()
    collector.clear()
    
    # Set up event collection
    events = []
    get_event_bus().subscribe_all(lambda e: events.append(e))
    
    # Run extraction
    result = await extract_paper_simple("test.pdf")
    
    # Verify configuration was used
    # (Check logs or behavior that proves chunk_size=1000 was used)
    
    # Verify metrics were collected
    llm_summary = collector.get_llm_summary()
    assert llm_summary.total_requests > 0
    
    # Verify events were published
    event_types = [type(e).__name__ for e in events]
    assert "ExtractionStarted" in event_types
    assert "ExtractionCompleted" in event_types

@pytest.mark.asyncio
async def test_performance_impact():
    """Ensure new infrastructure doesn't degrade performance."""
    # Baseline without events/metrics
    start = time.time()
    await extract_paper_simple("test.pdf")
    baseline_time = time.time() - start
    
    # With full infrastructure
    get_event_bus().subscribe_all(MetricsEventHandler())
    start = time.time()
    await extract_paper_simple("test.pdf")
    infra_time = time.time() - start
    
    # Should not add more than 5% overhead
    assert infra_time < baseline_time * 1.05
```

## Day 5: Documentation & Rollout

### Morning: Documentation

**Tasks:**
1. Update DEVELOPER_GUIDE.md with new patterns
2. Create configuration reference
3. Document event system
4. Add metrics guide

**Documentation Updates:**

```markdown
# Configuration Reference

## Environment Variables

All configuration can be set via environment variables:

- `HCI_EXTRACTION_MAX_FILE_SIZE_MB`: Maximum PDF file size (default: 50)
- `HCI_EXTRACTION_TIMEOUT_SECONDS`: PDF extraction timeout (default: 30.0)
- `HCI_ANALYSIS_CHUNK_SIZE`: Text chunk size for LLM (default: 10000)
- `HCI_ANALYSIS_MAX_CONCURRENT`: Concurrent section processing (default: 3)
- `HCI_RETRY_MAX_ATTEMPTS`: Maximum retry attempts (default: 3)
- `HCI_CACHE_ENABLED`: Enable caching (default: false)

## Configuration Override

```bash
# Via environment
export HCI_ANALYSIS_CHUNK_SIZE=5000
python -m hci_extractor extract paper.pdf

# Via config file
python -m hci_extractor extract paper.pdf --config-file my-config.yaml

# Via command line
python -m hci_extractor extract paper.pdf --config-override analysis.chunk_size=5000
```

# Event System

## Available Events

- `ExtractionStarted`: Published when PDF extraction begins
- `ExtractionCompleted`: Published when PDF extraction succeeds
- `SectionProcessingStarted`: Published for each section
- `SectionProcessingCompleted`: Published when section is processed

## Subscribing to Events

```python
from hci_extractor.core.events import get_event_bus, ExtractionCompleted

class MyHandler:
    def handle(self, event: ExtractionCompleted):
        print(f"Extracted {event.pages_extracted} pages")

get_event_bus().subscribe(ExtractionCompleted, MyHandler())
```
```

### Afternoon: Rollout & Monitoring

**Tasks:**
1. Deploy changes incrementally
2. Monitor for regressions
3. Collect metrics on improvements
4. Team handoff

**Rollout Plan:**

1. **Phase 1**: Configuration only
   - Deploy configuration system
   - Verify all hardcoded values removed
   - Monitor for any behavior changes

2. **Phase 2**: Metrics collection
   - Enable metrics collection
   - Remove mutable state from providers
   - Verify metrics accuracy

3. **Phase 3**: Event system
   - Enable event publishing
   - Add logging handler
   - Monitor event flow

4. **Phase 4**: Utility extraction
   - Deploy JSON recovery utility
   - Deploy retry handler
   - Verify error handling

## Success Metrics

### Quantitative
- [ ] 0 hardcoded configuration values
- [ ] 0 mutable state in providers
- [ ] 100% test coverage for new components
- [ ] <5% performance overhead
- [ ] 0 breaking changes

### Qualitative
- [ ] Easier to configure for different environments
- [ ] Better visibility into system behavior
- [ ] Cleaner, more maintainable code
- [ ] Foundation for future improvements

## Risk Mitigation

1. **Configuration Migration**
   - Risk: Existing deployments break
   - Mitigation: Defaults match current hardcoded values

2. **Performance Impact**
   - Risk: Event system adds overhead
   - Mitigation: Async publishing, optional handlers

3. **API Changes**
   - Risk: Breaking changes for users
   - Mitigation: Optional parameters, backwards compatibility

## Week 1 Deliverables

1. **Configuration Service** ✅
   - Centralized configuration
   - Environment-based settings
   - Override capabilities

2. **Metrics Collection** ✅
   - Immutable metrics
   - No provider state
   - Cost tracking

3. **Event System** ✅
   - Domain events
   - Event bus
   - Decoupled handlers

4. **Extracted Utilities**
   - JSON recovery handler
   - Unified retry logic
   - Reduced code duplication

5. **Comprehensive Tests**
   - Unit tests for all new components
   - Integration tests
   - Performance benchmarks

6. **Documentation**
   - Configuration reference
   - Event system guide
   - Migration instructions

This foundation sets up the project for long-term success by establishing patterns that promote low coupling, high cohesion, and immutable design throughout the system.