# Phase 2: LLM Integration - Detailed Implementation Plan

## 📊 Current Status
**Phase 2 Progress**: 3/8 steps completed (37.5%)  
**Last Updated**: Current session  
**Next Priority**: Step 4 - Section Analysis Prompts

### ✅ Completed Steps
- **Step 1**: Core Data Models (Paper, ExtractedElement, ExtractionResult)
- **Step 2**: LLM Provider Abstraction (Base classes, error handling, retry logic)
- **Step 3**: Gemini API Integration (Full implementation with academic prompts)

### 🚧 In Progress
- Development tooling and documentation (completed alongside implementation)

### 📋 Remaining Steps
- **Step 4**: Section Analysis Prompts (High Priority)
- **Step 5**: Extraction Pipeline with Validation (High Priority) 
- **Step 6**: Enhanced Section Detection (Medium Priority)
- **Step 7**: CLI Integration for LLM Analysis (Medium Priority)
- **Step 8**: Testing and Validation Suite (High Priority)

---

## Overview
Phase 2 integrates LLM-driven analysis to extract and classify claims, findings, and methods from academic paper sections while maintaining verbatim accuracy and immutable design principles.

**Duration**: 3-4 days  
**Goal**: LLM-powered extraction of structured elements from PDF sections  
**Success Criteria**: >90% classification accuracy with 100% verbatim extraction

---

## Step 1: Core Data Models for LLM Analysis ✅ COMPLETED
**Timeline**: Day 1 (1-2 hours)  
**Priority**: Critical Foundation
**Status**: ✅ Completed - All data models implemented and tested

### Tasks Breakdown
- [x] Add Paper and ExtractedElement dataclasses to models
- [x] Update type imports for Literal types
- [x] Add UUID generation for unique identifiers
- [x] Create validation logic for confidence scores and element types
- [x] Update model exports and imports

### Data Models to Implement
```python
@dataclass(frozen=True)
class Paper:
    paper_id: str
    title: str
    authors: tuple[str, ...]
    venue: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    file_path: str = ""

@dataclass(frozen=True)
class ExtractedElement:
    element_id: str
    paper_id: str
    element_type: Literal["claim", "finding", "method"]
    text: str
    section: str
    confidence: float
    evidence_type: Literal["quantitative", "qualitative", "theoretical", "unknown"]
    page_number: Optional[int] = None
    
    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

@dataclass(frozen=True)
class ExtractionResult:
    paper: Paper
    elements: tuple[ExtractedElement, ...]
    extraction_metadata: dict[str, Any]
    created_at: datetime
```

---

## Step 2: LLM Provider Abstraction ✅ COMPLETED
**Timeline**: Day 1 (2-3 hours)  
**Priority**: Critical - Foundation for extensibility
**Status**: ✅ Completed - Full abstraction layer with retry logic and error handling

### Tasks Breakdown
- [x] Create abstract base class for LLM providers
- [x] Define standard interface for text analysis
- [x] Add rate limiting and retry logic
- [x] Implement response validation and error handling
- [x] Add configuration management for API keys

### LLM Interface Design
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def analyze_section(
        self, 
        section_text: str, 
        section_type: str,
        context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Analyze a paper section and return extracted elements."""
        pass
    
    @abstractmethod
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate LLM response format."""
        pass
    
    @abstractmethod
    def get_rate_limit_delay(self) -> float:
        """Return seconds to wait between requests."""
        pass
```

### Rate Limiting Strategy
- Implement exponential backoff for API errors
- Respect provider-specific rate limits
- Add configurable delays between requests
- Track API usage and costs

---

## Step 3: Gemini API Integration ✅ COMPLETED
**Timeline**: Day 1-2 (3-4 hours)  
**Priority**: High - Primary LLM provider
**Status**: ✅ Completed - Full Gemini integration with academic-optimized prompts

### Tasks Breakdown
- [x] Add google-generativeai dependency
- [x] Implement GeminiProvider class
- [x] Add API key management from environment
- [x] Configure Gemini 1.5 Flash model settings
- [x] Implement JSON output mode with low temperature
- [x] Add error handling for API failures

### Gemini Implementation Strategy
```python
import google.generativeai as genai
from typing import List, Dict, Any

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.generation_config = {
            "temperature": 0.1,  # Low temperature for consistent output
            "response_mime_type": "application/json"
        }
    
    async def analyze_section(self, section_text: str, section_type: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        # Build section-specific prompt
        prompt = self._build_prompt(section_text, section_type, context)
        
        # Generate response with retry logic
        response = await self._generate_with_retry(prompt)
        
        # Parse and validate JSON response
        return self._parse_response(response)
```

### Configuration Requirements
- API key from environment variable GEMINI_API_KEY
- Model configuration optimized for academic text analysis
- JSON schema enforcement for structured output
- Timeout and retry configuration

---

## Step 4: Section Analysis Prompts
**Timeline**: Day 2 (4-5 hours)  
**Priority**: Critical - Core LLM functionality

### Tasks Breakdown
- [ ] Design section-specific prompt templates
- [ ] Create few-shot examples for each element type
- [ ] Add context about academic paper structure
- [ ] Implement prompt building with dynamic context
- [ ] Test prompts on sample HCI paper sections

### Prompt Design Strategy

#### Core Prompt Template
```python
SYSTEM_PROMPT = """
You are an expert at analyzing academic HCI papers. Your task is to extract specific elements from paper sections while maintaining exact verbatim accuracy.

CRITICAL RULES:
1. Extract text EXACTLY as written - never paraphrase or summarize
2. Only extract text that clearly fits the requested element type
3. Provide confidence scores based on clarity of classification
4. Include page numbers when available from context

ELEMENT TYPES:
- claim: Assertions, hypotheses, or statements about relationships
- finding: Results, outcomes, or discovered patterns from studies  
- method: Approaches, techniques, or procedures used in research

EVIDENCE TYPES:
- quantitative: Numbers, statistics, measurements
- qualitative: Interviews, observations, thematic analysis
- theoretical: Conceptual frameworks, models, theories
- unknown: Cannot determine from context
"""

SECTION_PROMPTS = {
    "abstract": "Focus on high-level claims and key findings. Be selective - only extract the most significant statements.",
    "introduction": "Look for research claims, hypotheses, and theoretical frameworks. Avoid background information.",
    "related_work": "Extract claims about existing research and identified gaps or limitations.",
    "methodology": "Focus on specific methods, procedures, and approaches used in the study.", 
    "results": "Extract specific findings, outcomes, and discovered patterns.",
    "discussion": "Look for interpretations, implications, and claims about meaning of results.",
    "conclusion": "Extract final claims, key findings, and stated contributions."
}
```

#### Few-Shot Examples
```python
FEW_SHOT_EXAMPLES = [
    {
        "section_text": "We found that users completed tasks 23% faster with the new interface (p<0.01).",
        "extracted_elements": [
            {
                "element_type": "finding",
                "text": "users completed tasks 23% faster with the new interface (p<0.01)",
                "evidence_type": "quantitative",
                "confidence": 0.95
            }
        ]
    },
    {
        "section_text": "Our approach combines machine learning with user feedback to improve recommendation accuracy.",
        "extracted_elements": [
            {
                "element_type": "method", 
                "text": "combines machine learning with user feedback to improve recommendation accuracy",
                "evidence_type": "theoretical",
                "confidence": 0.90
            }
        ]
    }
]
```

### Prompt Optimization
- Test prompts on diverse HCI paper sections
- Iterate based on extraction accuracy
- Balance precision vs recall for different element types
- Optimize for consistent confidence scoring

---

## Step 5: Extraction Pipeline Implementation
**Timeline**: Day 2-3 (4-5 hours)  
**Priority**: High - Core processing logic

### Tasks Breakdown
- [ ] Create SectionAnalyzer class for LLM processing
- [ ] Implement section-by-section analysis workflow
- [ ] Add verbatim validation against source text
- [ ] Build confidence aggregation and filtering
- [ ] Create extraction result compilation
- [ ] Add progress tracking for multi-section analysis

### Pipeline Architecture
```python
class SectionAnalyzer:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.min_confidence = 0.7
    
    async def analyze_paper(self, pdf_content: PdfContent, paper: Paper) -> ExtractionResult:
        """Analyze all sections of a paper and extract elements."""
        
        # Parse sections from PDF content
        sections = self._parse_sections(pdf_content)
        
        # Analyze each section with LLM
        all_elements = []
        for section in sections:
            elements = await self._analyze_section(section, paper)
            all_elements.extend(elements)
        
        # Validate and filter results
        validated_elements = self._validate_elements(all_elements, pdf_content)
        
        # Compile final results
        return ExtractionResult(
            paper=paper,
            elements=tuple(validated_elements),
            extraction_metadata=self._build_metadata(sections, all_elements),
            created_at=datetime.now()
        )
    
    def _validate_elements(self, elements: List[ExtractedElement], pdf_content: PdfContent) -> List[ExtractedElement]:
        """Ensure extracted text exists verbatim in source."""
        validated = []
        for element in elements:
            if self._text_exists_in_source(element.text, pdf_content):
                validated.append(element)
            else:
                logger.warning(f"Verbatim validation failed for element: {element.element_id}")
        return validated
```

### Verbatim Validation Strategy
- Use character-level position tracking from Phase 1
- Fuzzy matching for minor whitespace differences
- Strict validation ensures academic integrity
- Log validation failures for prompt improvement

---

## Step 6: Section Detection Enhancement
**Timeline**: Day 3 (2-3 hours)  
**Priority**: Medium-High - Improved section parsing

### Tasks Breakdown
- [ ] Enhance regex patterns from Phase 1 plan
- [ ] Add confidence scoring for section detection
- [ ] Handle edge cases like combined sections
- [ ] Add fallback strategies for unclear sections
- [ ] Integrate with LLM pipeline

### Section Detection Improvements
```python
class EnhancedSectionParser:
    def __init__(self):
        self.section_patterns = {
            "abstract": [
                r"(?i)^\s*(abstract|summary)\s*$",
                r"(?i)^\s*(1\.\s*)?abstract\s*$"
            ],
            "introduction": [
                r"(?i)^\s*(1\.\s*)?introduction\s*$",
                r"(?i)^\s*(i\.\s*)?introduction\s*$"
            ],
            # ... enhanced patterns for all sections
        }
    
    def parse_sections_with_confidence(self, pdf_content: PdfContent) -> List[SectionInfo]:
        """Parse sections with confidence scores."""
        sections = []
        for section_match in self._find_section_headers(pdf_content):
            confidence = self._calculate_section_confidence(section_match)
            sections.append(SectionInfo(
                name=section_match.section_type,
                text=section_match.text,
                confidence=confidence,
                start_page=section_match.start_page,
                end_page=section_match.end_page
            ))
        return sections
```

---

## Step 7: CLI Integration for LLM Analysis
**Timeline**: Day 3-4 (2-3 hours)  
**Priority**: Medium - User interface

### Tasks Breakdown
- [ ] Add extract command with LLM analysis
- [ ] Implement batch processing for multiple papers
- [ ] Add configuration options for LLM provider
- [ ] Create progress reporting for long operations
- [ ] Add output formatting options

### CLI Commands to Add
```bash
# Single paper LLM extraction
python -m hci_extractor extract paper.pdf --llm --output results.json

# Batch processing
python -m hci_extractor batch papers/ --llm --output-dir results/

# Configuration options
python -m hci_extractor extract paper.pdf --llm --provider gemini --min-confidence 0.8

# Debugging and validation
python -m hci_extractor extract paper.pdf --llm --verbose --validate-verbatim
```

### CLI Implementation
```python
@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--llm", is_flag=True, help="Enable LLM-based element extraction")
@click.option("--provider", default="gemini", help="LLM provider to use")
@click.option("--min-confidence", default=0.7, help="Minimum confidence for extraction")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output JSON file")
def extract(pdf_path: Path, llm: bool, provider: str, min_confidence: float, output: Optional[Path]) -> None:
    """Extract structured elements from academic papers."""
    
    if llm:
        # Initialize LLM provider
        llm_provider = create_llm_provider(provider)
        analyzer = SectionAnalyzer(llm_provider)
        
        # Process paper with LLM analysis
        result = await analyzer.analyze_paper(pdf_content, paper)
        
        # Output results
        save_extraction_result(result, output)
    else:
        # Fall back to PDF-only processing from Phase 1
        process_pdf_only(pdf_path, output)
```

---

## Step 8: Testing and Validation
**Timeline**: Day 4 (3-4 hours)  
**Priority**: High - Quality assurance

### Tasks Breakdown
- [ ] Create test cases for LLM integration
- [ ] Add mock LLM provider for testing
- [ ] Test verbatim validation logic
- [ ] Validate extraction accuracy on sample papers
- [ ] Add performance benchmarks
- [ ] Test error handling and retry logic

### Test Categories
```python
# Unit tests for data models
def test_extracted_element_validation():
    """Test confidence score validation."""
    
def test_paper_immutability():
    """Test immutable design patterns."""

# Integration tests for LLM analysis  
def test_gemini_provider_integration():
    """Test Gemini API integration."""
    
def test_section_analysis_pipeline():
    """Test end-to-end section analysis."""

# Validation tests
def test_verbatim_accuracy():
    """Ensure extracted text exists in source."""
    
def test_element_classification_accuracy():
    """Validate >90% classification precision."""
```

---

## Dependencies to Add ✅ COMPLETED

```toml
# ✅ Already added to pyproject.toml dependencies
dependencies = [
    "click>=8.0.0",
    "python-dotenv>=1.0.0",
    "pymupdf>=1.24.0",
    "google-generativeai>=0.3.0",  # ✅ Gemini API
    "aiohttp>=3.9.0",              # ✅ Async HTTP for API calls
]
```

---

## Success Criteria for Phase 2

### Functional Requirements
- [ ] Extract claims, findings, methods with >90% classification accuracy
- [ ] Maintain 100% verbatim accuracy (no paraphrasing)
- [ ] Process typical HCI papers in <30 seconds
- [ ] Handle API rate limits and errors gracefully
- [ ] Support multiple section types with appropriate prompts

### Quality Requirements  
- [ ] >90% test coverage for LLM integration
- [ ] Comprehensive error handling for API failures
- [ ] Immutable data structures throughout pipeline
- [ ] Type safety with mypy validation
- [ ] Clear logging and debugging capabilities

### Integration Requirements
- [ ] CLI commands work end-to-end with LLM analysis
- [ ] JSON output compatible with analysis workflows
- [ ] Batch processing handles multiple papers efficiently
- [ ] Configuration management for API keys and settings

---

## Risk Mitigation

### Technical Risks
**Risk**: LLM API costs become prohibitive  
**Mitigation**: Implement section-based processing, configurable confidence thresholds, local caching

**Risk**: Classification accuracy below 90%  
**Mitigation**: Iterative prompt optimization, few-shot example refinement, fallback to high-confidence only

**Risk**: API rate limits disrupt batch processing  
**Mitigation**: Intelligent backoff, progress persistence, resumable operations

### Quality Risks
**Risk**: Verbatim validation fails due to text differences  
**Mitigation**: Fuzzy matching for whitespace, character position mapping, manual review tools

**Risk**: Extraction speed exceeds 30 seconds per paper  
**Mitigation**: Parallel section processing, API optimization, progress reporting

---

## Phase 2 Completion Checklist

- [ ] All 8 steps completed with deliverables
- [ ] LLM provider abstraction implemented and tested
- [ ] Gemini integration working with API key management
- [ ] Section analysis prompts optimized for HCI papers
- [ ] Extraction pipeline maintains verbatim accuracy
- [ ] CLI commands support LLM-based analysis
- [ ] >90% classification accuracy on test papers
- [ ] Comprehensive test suite covering LLM integration
- [ ] Error handling tested with API failures
- [ ] Ready for Phase 3 pipeline integration

---

**Next Phase**: Phase 3 will focus on async processing, robust error handling, and progress tracking for production-ready batch processing of multiple papers.