# HCI Paper Extractor

Extract structured academic content from HCI research papers using LLM analysis.

## What It Does

- Extracts claims, findings, methods, and artifacts from PDF research papers
- Maintains verbatim accuracy (no paraphrasing)
- Exports to CSV, JSON, or Markdown formats
- Supports batch processing
- Provides both CLI and web interfaces

## Installation

### Quick Setup
```bash
git clone <repository-url>
cd hci-paper-extractor
./scripts/setup.sh  # Linux/macOS
# or scripts\setup.bat on Windows
```

### Manual Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

Get your free API key: https://makersuite.google.com/app/apikey

## Usage

### Web Interface (New!)

Start the web server:
```bash
source venv/bin/activate
python -m hci_extractor serve
```

Then open http://localhost:8000 in your browser.

**API Endpoints:**
- Upload PDFs at `POST /api/v1/extract`
- View API docs at http://localhost:8000/docs
- Real-time progress via WebSocket at `/api/v1/ws/progress/{session_id}`

### Command Line Interface

**Basic extraction:**
```bash
source venv/bin/activate

# Extract to CSV (best for analysis)
python -m hci_extractor extract paper.pdf --output results.csv

# Extract to JSON (complete data)
python -m hci_extractor extract paper.pdf --output results.json

# Extract to Markdown (human readable)
python -m hci_extractor extract paper.pdf --output results.md
```

**Batch processing:**
```bash
# Process multiple papers
python -m hci_extractor batch papers_folder/ results_folder/

# Export batch results to CSV
python -m hci_extractor export results_folder/ --format csv --output analysis.csv
```

**System diagnostics:**
```bash
python -m hci_extractor doctor      # Check system health
python -m hci_extractor validate paper.pdf  # Test specific PDF
python -m hci_extractor quickstart  # Interactive guide
```

## Output Format

### JSON Structure
```json
{
  "paper": {
    "paper_id": "uuid",
    "title": "Paper Title",
    "authors": ["Author 1", "Author 2"],
    "file_path": "path/to/paper.pdf"
  },
  "elements": [
    {
      "element_id": "uuid",
      "element_type": "finding",
      "text": "Users completed tasks 34% faster with the new interface",
      "section": "results",
      "confidence": 0.95,
      "evidence_type": "quantitative",
      "page_number": 5
    }
  ]
}
```

### CSV Columns
- `paper_id`, `paper_title`, `authors`
- `element_id`, `element_type`, `text`, `section`
- `confidence`, `evidence_type`, `page_number`

## Configuration

### Profiles
```bash
# View available profiles
python -m hci_extractor profiles

# Use predefined settings
python -m hci_extractor extract paper.pdf --profile thorough
python -m hci_extractor extract paper.pdf --profile quick_scan
```

### Custom Parameters
```bash
python -m hci_extractor extract paper.pdf \
  --chunk-size 15000 \
  --timeout 90 \
  --max-retries 5 \
  --temperature 0.1
```

### Environment Variables
```bash
# API Configuration
GEMINI_API_KEY=your-api-key-here

# Processing Configuration
HCI_CHUNK_SIZE=10000
HCI_TIMEOUT=60
HCI_MAX_RETRIES=3
HCI_TEMPERATURE=0.1
HCI_LOG_LEVEL=INFO
```

## Academic Workflow Examples

### Systematic Literature Review
```bash
# 1. Process all papers
python -m hci_extractor batch literature_papers/ raw_results/

# 2. Export high-confidence findings
python -m hci_extractor export raw_results/ --format csv --min-confidence 0.8 --element-type finding --output findings.csv

# 3. Export claims for analysis
python -m hci_extractor export raw_results/ --format csv --element-type claim --output claims.csv
```

### Single Paper Analysis
```bash
# Quick analysis workflow
python -m hci_extractor extract paper.pdf --output analysis.csv
# Open analysis.csv in Excel/R/Python for further analysis
```

## Troubleshooting

**API Key Issues:**
```bash
python -m hci_extractor doctor    # Check system health
echo "GEMINI_API_KEY=your-key" > .env
```

**PDF Processing Issues:**
```bash
python -m hci_extractor validate paper.pdf  # Test if PDF is processable
python -m hci_extractor extract paper.pdf --log-level DEBUG  # Detailed logging
```

**Performance Issues:**
```bash
# Reduce concurrency
python -m hci_extractor batch papers/ results/ --max-concurrent 1

# Increase timeout for large papers
python -m hci_extractor extract paper.pdf --timeout 120
```

## Development

### Requirements
- Python 3.9+
- Virtual environment
- Gemini API key

### Setup
```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
black src/ tests/
mypy src/
```

## Key Features

### Technical
- **Hexagonal Architecture**: Clean separation of concerns
- **Dependency Injection**: Testable and maintainable code
- **Immutable Design**: Thread-safe data structures
- **Type Safety**: Full mypy compliance
- **Error Recovery**: Automatic retry and JSON repair

### Academic
- **Verbatim Extraction**: No paraphrasing or summarization
- **Source Tracking**: Page numbers and section references
- **Confidence Scoring**: Quality assessment for manual review
- **Evidence Classification**: Quantitative, qualitative, theoretical, mixed

### User Experience
- **Real-time Progress**: Section-by-section processing updates
- **Multiple Formats**: CSV, JSON, Markdown exports
- **Batch Processing**: Concurrent paper processing
- **Interactive Setup**: Guided configuration and troubleshooting
- **Web Interface**: Browser-based alternative to CLI

## Status

**Current Version**: Production Ready (July 2025)
- ✅ Core extraction functionality validated
- ✅ CLI interface with 98% test success rate
- ✅ Web API with real-time progress tracking
- ✅ Batch processing and export capabilities
- ✅ Academic integrity and verbatim accuracy

**Next Development**: Frontend web interface for the API

## License

TBD