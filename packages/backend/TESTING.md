# Testing Strategy - HCIBrain Backend

## Overview

This document describes the comprehensive testing strategy for the HCIBrain backend system. Our approach follows Test-Driven Development (TDD) principles, writing tests first to define expected behavior, then implementing code to make tests pass.

## Testing Philosophy

- **Test-First Development**: All new functionality starts with failing tests that define expected behavior
- **Clean Architecture Testing**: Tests follow the hexagonal architecture, testing each layer independently
- **Immutable Design Validation**: Tests ensure all objects remain immutable and frozen
- **Real-World Scenarios**: Tests simulate actual usage patterns and edge cases

## Test Structure

### Core Functionality Tests

#### 1. PDF Extraction Tests (`test_pdf_extraction.py`)
**Purpose**: Validates PDF text extraction using PyMuPDF

**What it tests**:
- Successful PDF content extraction from valid files
- Error handling for non-existent files
- Rejection of non-PDF file types
- Extracted content structure (full_text, metadata, pages)
- Performance limits (file size, processing time)
- Memory usage bounds

**Key scenarios**:
- Academic papers with complex formatting
- Large PDFs requiring chunked processing
- Corrupted or malformed PDF files
- Security validation of PDF content

#### 2. LLM Markup Generation Tests (`test_llm_markup.py`)
**Purpose**: Validates LLM-powered markup generation for academic content

**What it tests**:
- Successful markup generation with Gemini API
- Text chunking for large documents
- Markup format validation (goal/method/result tags)
- Confidence score validation (0.50-0.99 range)
- API failure handling and retries
- Empty text handling
- Rate limiting compliance

**Expected markup format**:
```html
<goal confidence="0.92">research objective text</goal>
<method confidence="0.88">methodology description</method>
<result confidence="0.94">findings and outcomes</result>
```

#### 3. Web API Tests (`test_web_api_tdd.py`)
**Purpose**: Validates FastAPI web endpoints and integration

**What it tests**:
- Health endpoint availability and response format
- Markup extraction endpoint validation
- File upload handling (PDF validation, size limits)
- Error response formatting (JSON structure)
- CORS configuration for frontend compatibility
- Concurrent request handling
- Request timeout management
- **Single-chunk extraction workflow** (ootest.pdf, ~33s)
- **Multi-chunk extraction workflow** (ootest_big.pdf, 5-10 min)

**API endpoints tested**:
- `GET /api/v1/health` - System health check
- `POST /api/v1/extract/markup` - PDF markup extraction

**PDF Processing Test Coverage**:
- **Fast Test** (single-chunk): 6,238 chars → 1 chunk, 33 seconds
- **Comprehensive Test** (multi-chunk): 22,997 chars → 2 chunks, validates chunking + rate limiting

#### 4. Configuration Tests (`test_configuration_tdd.py`)
**Purpose**: Validates YAML configuration loading and validation

**What it tests**:
- YAML file parsing and loading
- Configuration object immutability
- Environment variable overrides
- Default value application
- Required field validation
- Type conversion (strings to numbers)
- API key validation
- Numerical range validation
- Provider type validation

**Configuration sections**:
- API settings (provider, keys, timeouts)
- Extraction settings (file limits, normalization)
- Analysis settings (chunking, concurrency, LLM parameters)
- Retry configuration (attempts, backoff)
- Export and general settings

#### 5. Dependency Injection Tests (`test_dependency_injection_tdd.py`)
**Purpose**: Validates dependency injection container and service wiring

**What it tests**:
- DI container creation and configuration
- Service singleton patterns (EventBus)
- Provider instantiation based on config
- Dependency wiring between services
- Different provider type support
- Error handling for invalid configurations
- Resource cleanup and lifecycle management
- Concurrent access safety

**Services managed**:
- EventBus (singleton)
- LLMProvider (per config)
- MarkupPromptLoader
- Configuration services

### Legacy Test Files

#### `test_web_api.py` - Basic Web API Tests
**Status**: Legacy, being replaced by TDD version
**Purpose**: Minimal API connectivity validation

#### `test_llm_markup.py` - LLM Provider Tests  
**Status**: Legacy, being enhanced by TDD version
**Purpose**: Basic provider functionality testing

## Testing Strategy

### 1. Test-Driven Development Cycle

```
Red → Green → Refactor
├── Write failing test (defines expected behavior)
├── Implement minimal code to make test pass
└── Refactor code while keeping tests green
```

### 2. Testing Layers

**Unit Tests** (Fast, Isolated):
- Individual service methods
- Configuration parsing
- Data validation
- Error handling

**Integration Tests** (Medium speed):
- Service interactions through DI container
- API endpoint workflows
- External service mocking

**End-to-End Tests** (Slower):
- Complete PDF processing workflows
- Real API responses (with test keys)
- Performance benchmarks

### 3. Test Categories

**Functional Tests**:
- Core business logic validation
- Input/output verification
- Error condition handling

**Architectural Tests**:
- Immutability enforcement
- Dependency injection validation
- Interface compliance

**Performance Tests**:
- Processing time limits
- Memory usage bounds
- Concurrency handling

**Security Tests**:
- Input validation
- API key protection
- File upload safety

## Running Tests

### All Tests
```bash
source venv/bin/activate
python -m pytest tests/ -v
```

### TDD Tests Only
```bash
python -m pytest tests/test_*_tdd.py -v
```

### With Coverage
```bash
python -m pytest tests/ --cov=src/hci_extractor --cov-report=html
```

### Performance Tests
```bash
python -m pytest tests/ -k "performance" -v
```

## Test Data and Fixtures

### PDF Test Files
- `sample_academic_paper.pdf` - Standard academic format
- `large_paper.pdf` - Tests file size limits
- `malformed.pdf` - Tests error handling

### Mock Responses
- Gemini API responses for consistent testing
- Error scenarios for resilience testing
- Performance data for benchmarking

### Configuration Fixtures
- Valid configurations for each provider type
- Invalid configurations for error testing
- Environment variable scenarios

## Quality Gates

### Before Code Merge
- [ ] All existing tests pass
- [ ] New functionality has corresponding tests
- [ ] Test coverage remains above 85%
- [ ] No security vulnerabilities in test code
- [ ] Performance tests within acceptable limits

### CI/CD Pipeline Tests
- [ ] Lint checks (Ruff formatting and rules)
- [ ] Type checking (MyPy)
- [ ] Security scanning (Bandit)
- [ ] Dependency checking
- [ ] Test execution and coverage reporting

## Test Maintenance

### Regular Reviews
- Quarterly test effectiveness review
- Remove obsolete tests after refactoring
- Update test data for new scenarios
- Performance benchmark updates

### Documentation Updates
- Keep test descriptions current
- Document new testing patterns
- Update examples and fixtures
- Maintain troubleshooting guides

## Future Enhancements

### Planned Test Additions
- Load testing for concurrent users
- Integration tests with real LLM providers
- Automated security penetration testing
- Performance regression detection

### Testing Tools
- Property-based testing with Hypothesis
- Mutation testing for test quality
- Visual regression testing for markup output
- Automated test generation

## Troubleshooting

### Common Test Issues
- **Virtual environment**: Always use `source venv/bin/activate`
- **Import errors**: Check PYTHONPATH and package structure
- **API key tests**: Use test keys or proper mocking
- **File permissions**: Ensure test files are readable
- **Timeout issues**: Adjust test timeouts for slow systems

### Debug Commands
```bash
# Run specific test with output
python -m pytest tests/test_web_api_tdd.py::TestWebAPIEndpoints::test_health_endpoint_exists -v -s

# Run with pdb debugging
python -m pytest tests/test_configuration_tdd.py --pdb

# Show test execution times
python -m pytest tests/ --durations=10
```