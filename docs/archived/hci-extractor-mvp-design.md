# HCI Paper Extractor MVP Design

## Overview

A minimal viable product for extracting and classifying claims, findings, and methods from HCI academic papers using LLM-driven analysis. The system focuses on verbatim extraction to maintain academic integrity while leveraging LLMs for identification and classification.

## Use Cases

### Primary Use Case: Literature Review Support
**Goal**: Extract structured information from HCI papers to support systematic literature reviews

**Workflow**:
1. Researcher uploads PDF papers (10-50 papers typically)
2. System extracts all claims, findings, and methods verbatim
3. Researcher exports to CSV/Excel for analysis
4. Manual synthesis identifies patterns across papers

**Example Output for Literature Review**:
- All claims about "gesture recognition accuracy"
- All findings with p-values < 0.05
- All user study methods with N > 20 participants

### Secondary Use Cases

#### 1. Research Gap Identification
- Extract all claims across papers
- Identify what hasn't been studied
- Find conflicting claims between papers

#### 2. Method Replication
- Extract detailed methodology sections
- Compare study designs across papers
- Identify best practices for user studies

#### 3. Meta-Analysis Preparation
- Extract all quantitative findings
- Collect effect sizes and sample sizes
- Prepare data for statistical meta-analysis

#### 4. Thesis/Dissertation Writing
- Quickly find relevant claims to cite
- Ensure comprehensive coverage of literature
- Track which papers support which arguments

### Non-Goals (What This MVP Won't Do)
- **Summarization**: We extract verbatim, not summarize
- **Synthesis**: Manual work, not automated
- **Quality Assessment**: No automatic paper quality scoring
- **Citation Network Analysis**: Focus on content, not references
- **Real-time Collaboration**: Single-user tool

## Core Architecture Principles

- **Single Responsibility**: Each component does one thing well
- **Minimal Dependencies**: Use stdlib where possible, add packages only when essential
- **Data-First**: Focus on getting quality extractions, not fancy UI
- **Extensible**: Easy to add new LLM providers or export formats

## System Components

```
hci-paper-extractor/
├── src/
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py      # PDF to text conversion
│   │   └── section_parser.py     # Identify paper sections
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract LLM interface
│   │   ├── gemini_adapter.py    # Gemini API implementation
│   │   └── prompts.py           # Prompt templates
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Data models
│   ├── storage/
│   │   ├── __init__.py
│   │   └── json_store.py       # Simple JSON persistence
│   └── main.py                  # CLI entry point
├── data/                        # Input PDFs
├── output/                      # Extracted results
├── requirements.txt
└── README.md
```

## Data Models

```python
# models/schemas.py
from dataclasses import dataclass
from typing import List, Optional, Literal
from datetime import datetime

@dataclass
class Paper:
    paper_id: str
    title: str
    authors: List[str]
    venue: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    file_path: str = ""

@dataclass
class ExtractedElement:
    element_id: str
    paper_id: str
    element_type: Literal["claim", "finding", "method"]
    text: str
    section: str
    confidence: float
    evidence_type: Literal["quantitative", "qualitative", "theoretical"]
    page_number: Optional[int] = None
    # Statistical fields - only populated for findings
    statistical_significance: Optional[bool] = None
    p_value: Optional[str] = None
    effect_size: Optional[str] = None
    sample_size: Optional[int] = None
```

## Implementation Plan

### Phase 1: PDF Processing (Week 1)

#### 1.1 PDF Text Extraction
- Use PyMuPDF (lightweight, good text preservation)
- Extract text with page numbers
- Basic section detection using common headers

#### 1.2 Section Parser
- Regex-based section identification
- Handle variations (e.g., "METHODS" vs "Methodology")
- Return structured sections with text

```python
# Example section patterns
SECTION_PATTERNS = {
    "abstract": r"(?i)^abstract",
    "introduction": r"(?i)^(1\.?\s*)?introduction",
    "related_work": r"(?i)^(2\.?\s*)?(related work|background|literature review)",
    "methods": r"(?i)^(3\.?\s*)?(method|methodology|study design|procedure)",
    "results": r"(?i)^(4\.?\s*)?(results|findings|analysis)",
    "discussion": r"(?i)^(5\.?\s*)?(discussion|implications|limitations)"
}
```

### Phase 2: LLM Integration (Week 1-2)

#### 2.1 Abstract LLM Interface
```python
from abc import ABC, abstractmethod

class BaseLLM(ABC):
    @abstractmethod
    async def extract_elements(self, text: str, section: str) -> List[ExtractedElement]:
        pass
```

#### 2.2 Gemini API Implementation
- Use standard Gemini API with API key authentication
- Structured output using JSON mode
- Simple retry logic for reliability
- Minimal setup complexity

```python
# Example setup
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")
```

#### 2.3 Prompt Engineering
Section-specific prompts with few-shot examples:

```python
EXTRACTION_PROMPT = """
Extract claims, findings, and methods from this HCI paper section.

Section: {section_name}
Text: {section_text}

Instructions:
1. Extract VERBATIM text - do not paraphrase or summarize
2. Classify each extraction as "claim", "finding", or "method"
3. For findings, identify if statistical data is present

Return JSON array with:
- element_type: "claim", "finding", or "method"
- text: exact extracted text (must appear verbatim in source)
- evidence_type: "quantitative", "qualitative", or "theoretical"
- confidence: 0.0-1.0
- p_value: extract if present (findings only)
- sample_size: extract if present (findings only)

Examples:
[Few-shot examples here]
"""
```

#### 2.4 Gemini Adapter Implementation
```python
# llm/gemini_adapter.py
import google.generativeai as genai
import json
from typing import List
import os

class GeminiAdapter(BaseLLM):
    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        
    async def extract_elements(self, text: str, section: str) -> List[ExtractedElement]:
        prompt = EXTRACTION_PROMPT.format(
            section_name=section,
            section_text=text
        )
        
        # Configure for JSON output
        generation_config = {
            "temperature": 0.1,  # Low temp for consistency
            "response_mime_type": "application/json"
        }
        
        response = await self.model.generate_content_async(
            prompt,
            generation_config=generation_config
        )
        
        return self._parse_response(response.text)
```

### Phase 3: Core Pipeline (Week 2)

#### 3.1 Main Processing Flow
```python
# Pseudocode for main pipeline
async def process_paper(pdf_path: Path) -> None:
    # Extract text and metadata
    paper = extract_metadata(pdf_path)
    sections = parse_sections(pdf_path)
    
    # Process each section
    all_elements = []
    for section in sections:
        elements = await llm.extract_elements(section.text, section.name)
        all_elements.extend(elements)
    
    # Save results
    store.save(paper, all_elements)
```

#### 3.2 Storage Layer
- JSON files per paper
- Single aggregated export file
- UUID generation for IDs

### Phase 4: Export & CLI (Week 3)

#### 4.1 Export Formats
- **JSON**: Complete data with all fields
- **CSV**: Flattened format for Excel/Sheets analysis
- **Markdown**: Human-readable summaries

#### 4.2 CLI Interface
```bash
# Single paper extraction
python -m hci_extractor extract paper.pdf

# Batch processing
python -m hci_extractor batch input_dir/ output_dir/

# Export results
python -m hci_extractor export output_dir/ --format csv
```

## Key Design Decisions

### Why JSON Storage?
- No schema migrations needed
- Human-readable for debugging
- Easy to version control
- Trivial to implement

### Why Section-Based Processing?
- Improves LLM accuracy with context
- Reduces token usage
- Enables section-specific prompts

### Why Verbatim Extraction?
- Preserves academic integrity
- Enables accurate citation tracking
- Avoids LLM hallucination risks

## MVP Limitations (Acceptable for V1)

- No real-time progress tracking
- No web UI (CLI only)
- No automatic paper metadata extraction from CrossRef
- No duplicate detection
- Single-threaded processing

## Dependencies

```txt
# requirements.txt
pymupdf>=1.23.0              # PDF text extraction
google-generativeai>=0.3.0   # Gemini API
pydantic>=2.0.0              # Data validation
click>=8.0.0                 # CLI framework
python-dotenv>=1.0.0         # Environment management
```

## Environment Setup

```bash
# Create .env file
echo "GEMINI_API_KEY=your-api-key-here" > .env

# Install dependencies
pip install -r requirements.txt

# Run extractor
python -m hci_extractor extract paper.pdf
```

## Example Output Structure

```json
{
  "paper": {
    "paper_id": "uuid-here",
    "title": "Evaluating Touch Input Methods for VR",
    "authors": ["Smith, J.", "Doe, A."],
    "year": 2024,
    "file_path": "data/smith2024.pdf"
  },
  "extracted_elements": [
    {
      "element_id": "uuid-here",
      "paper_id": "paper-uuid",
      "element_type": "finding",
      "text": "Participants completed tasks 23% faster (t(28)=3.45, p<0.01) using the haptic feedback condition",
      "section": "results",
      "confidence": 0.95,
      "evidence_type": "quantitative",
      "page_number": 7,
      "statistical_significance": true,
      "p_value": "p<0.01",
      "sample_size": 29
    }
  ]
}
```

## Next Steps After MVP

1. Add more LLM providers (OpenAI, Anthropic)
2. Implement batch processing with progress bars
3. Add paper metadata lookup via DOI
4. Create simple web viewer for results
5. Add inter-rater reliability metrics
6. Implement caching for LLM calls
7. Add extraction quality metrics

## Success Metrics

- Extraction accuracy: >90% precision for element classification
- Processing speed: <30 seconds per paper
- Verbatim accuracy: 100% (extracted text must exist in source)
- Export compatibility: Works with Excel, R, and Python analysis tools