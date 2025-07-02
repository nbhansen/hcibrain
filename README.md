# HCI Paper Extractor

A tool for extracting structured content from HCI academic papers using LLM-driven analysis.

## Quick Start

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
hci-extractor --version
```

## Development Status

🚧 **Currently in development** - Phase 1: PDF Processing Foundation

## Project Structure

```
src/hci_extractor/     # Main package
tests/                 # Test suite
data/                  # Input PDFs (ignored by git)
output/                # Extracted results (ignored by git)
```

## License

TBD