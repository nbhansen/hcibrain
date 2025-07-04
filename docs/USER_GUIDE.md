# HCI Paper Extractor - User Guide for Researchers

**A practical guide for academic researchers using the HCI Paper Extractor for literature analysis.**

## Overview

The HCI Paper Extractor automates the extraction of research elements (claims, findings, methods, artifacts) from academic papers, enabling systematic literature reviews and meta-analyses with consistent accuracy.

## Setup

### 1. Installation
```bash
# Clone and install
git clone <repository-url>
cd hci-paper-extractor
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

### 2. API Key Configuration
```bash
# Get free API key: https://makersuite.google.com/app/apikey
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

### 3. Verify Installation
```bash
venv/bin/python -m hci_extractor --help
```

## Common Research Workflows

### Single Paper Analysis

**Quick Analysis:**
```bash
# Basic extraction with console output
venv/bin/python -m hci_extractor extract paper.pdf

# Save results for later analysis
venv/bin/python -m hci_extractor extract paper.pdf --output results.json
```

**Quality Check:**
```bash
# Verify PDF is processable before analysis
venv/bin/python -m hci_extractor validate paper.pdf
```

### Systematic Literature Review

**Step 1: Batch Processing**
```bash
# Process all papers in a folder
venv/bin/python -m hci_extractor batch literature_papers/ raw_results/

# Control processing speed (default: 3 concurrent)
venv/bin/python -m hci_extractor batch literature_papers/ raw_results/ --max-concurrent 2
```

**Step 2: Export for Analysis**
```bash
# All data to CSV for Excel/R/Python
venv/bin/python -m hci_extractor export raw_results/ --format csv --output complete_analysis.csv

# High-confidence findings only
venv/bin/python -m hci_extractor export raw_results/ --format csv --min-confidence 0.8 --element-types finding --output findings.csv

# Claims for thematic analysis
venv/bin/python -m hci_extractor export raw_results/ --format csv --element-types claim --output claims.csv
```

### Meta-Analysis Preparation

**Extract Quantitative Data:**
```bash
# Quantitative findings with statistics
venv/bin/python -m hci_extractor export results/ --format csv --evidence-types quantitative --output quantitative_data.csv

# Methods for methodology comparison
venv/bin/python -m hci_extractor export results/ --format csv --element-types method --output methods.csv
```

## Understanding the Output

### Element Types
- **claim**: Research hypotheses, assertions, design principles
- **finding**: Study results, user behavior observations, performance metrics
- **method**: Research approaches, experimental procedures, evaluation techniques
- **artifact**: Systems, prototypes, tools, frameworks created

### Evidence Types
- **quantitative**: Numbers, statistics, measurements (e.g., "34% faster")
- **qualitative**: Interviews, observations, thematic analysis (e.g., "users expressed frustration")
- **theoretical**: Conceptual frameworks, models, principles
- **mixed**: Combination of quantitative and qualitative evidence

### Confidence Scores
- **0.9-1.0**: High confidence - likely accurate classification
- **0.7-0.8**: Medium confidence - consider manual review
- **0.5-0.7**: Lower confidence - prioritize for manual verification

## Practical Tips

### Best Practices

**File Management:**
- Keep original PDFs in organized folders by conference/year
- Use descriptive output folder names (`chi2023_results`, `accessibility_papers`)
- Maintain .env file in project root for API key

**Quality Control:**
- Start with `validate` command for problematic PDFs
- Use `--min-confidence 0.8` for high-quality datasets
- Manually review elements with confidence < 0.7

**Performance:**
- Use `--max-concurrent 2` for large batches to avoid API limits
- Process 10-20 papers at a time for manageable results
- Complex papers (>20 pages) may take 30-60 seconds each

### Troubleshooting

**Common Issues:**

*"No module named hci_extractor"*
- Solution: Activate virtual environment first (`source venv/bin/activate`)

*"GEMINI_API_KEY environment variable is required"*
- Solution: Create .env file with your API key

*"Processing timeout after 60s"*
- Solution: Very large sections automatically chunk, wait for completion

*"Invalid JSON response"*
- Solution: System automatically recovers, some elements may be skipped

**PDF Issues:**
- Password-protected: Remove password before processing
- Scanned images: Use OCR tool first to create text layer
- Corrupted files: Check file integrity, re-download if needed

## Advanced Usage

### Filtering and Export Options

**By Confidence:**
```bash
# High confidence only
--min-confidence 0.8

# All confidence levels
--min-confidence 0.0
```

**By Element Type:**
```bash
# Multiple types
--element-types claim,finding

# Single type
--element-types method
```

**By Evidence Type:**
```bash
# Quantitative only
--evidence-types quantitative

# Multiple types
--evidence-types quantitative,qualitative
```

### Integration with Analysis Tools

**Excel:**
- Import CSV directly with Data > From Text/CSV
- Use filters and pivot tables for analysis
- Sort by confidence for quality assessment

**R:**
```r
# Load data
data <- read.csv("results.csv")

# Filter high confidence findings
findings <- subset(data, element_type == "finding" & confidence >= 0.8)

# Analyze by evidence type
table(findings$evidence_type)
```

**Python:**
```python
import pandas as pd

# Load data
df = pd.read_csv("results.csv")

# High confidence claims
claims = df[(df['element_type'] == 'claim') & (df['confidence'] >= 0.8)]

# Group by paper
by_paper = df.groupby('paper_title').size()
```

## Research Workflow Examples

### Accessibility Literature Review

```bash
# 1. Batch process accessibility papers
venv/bin/python -m hci_extractor batch accessibility_papers/ accessibility_results/

# 2. Export findings for analysis
venv/bin/python -m hci_extractor export accessibility_results/ --format csv --element-types finding --output accessibility_findings.csv

# 3. Export methods for systematic comparison
venv/bin/python -m hci_extractor export accessibility_results/ --format csv --element-types method --min-confidence 0.8 --output accessibility_methods.csv
```

### VR/AR Technology Analysis

```bash
# 1. Process recent VR/AR papers
venv/bin/python -m hci_extractor batch vr_ar_papers/ vr_results/

# 2. Extract artifacts (systems/prototypes)
venv/bin/python -m hci_extractor export vr_results/ --format csv --element-types artifact --output vr_systems.csv

# 3. Get quantitative performance data
venv/bin/python -m hci_extractor export vr_results/ --format csv --evidence-types quantitative --output vr_performance.csv
```

## Academic Integrity

The tool maintains strict academic integrity:
- **100% verbatim extraction** - Never paraphrases or summarizes
- **Source tracking** - Every element includes page number and section
- **Transparency** - Confidence scores enable quality assessment
- **Reproducibility** - Consistent results across multiple runs

Use extracted text with proper citations to source papers. The tool assists analysis but does not replace careful reading and synthesis.

---

*Ready to accelerate your literature review? Start with a single paper to familiarize yourself with the output format, then scale to batch processing for your full literature corpus.*