# HCIBrain API Testing Guide

## Quick Start

### 1. Health Check (No API Key Required)
```bash
./quick_test.sh
```
This tests basic server functionality and endpoint availability.

### 2. Configuration Setup (For Full Testing)
```bash
./setup_config.sh
```
This will guide you through setting up the Gemini API key in config.yaml needed for PDF extraction.

### 3. Full API Testing
```bash
./test_api.sh
```
Comprehensive test of all endpoints including PDF extraction with coordinates.

## Testing Scripts

### `quick_test.sh`
- **Purpose**: Basic health check without API key
- **Tests**: Server startup, health endpoint, config endpoint
- **Runtime**: ~10 seconds
- **Requirements**: None

### `setup_config.sh`
- **Purpose**: Configuration wizard for YAML setup
- **Features**: Updates config.yaml file, guides API key setup
- **Requirements**: Google Gemini API key (optional)

### `test_api.sh`
- **Purpose**: Comprehensive API testing
- **Tests**: Health, config, PDF extraction, coordinate mapping
- **Runtime**: ~60 seconds (includes PDF download)
- **Requirements**: Gemini API key

## Test Options

### Quick Mode
```bash
./test_api.sh --quick
```
Runs only basic health and config tests.

### No Download
```bash
./test_api.sh --no-download
```
Skips PDF download (assumes `deep_speech_2.pdf` exists).

### Keep Server Running
```bash
./test_api.sh --keep-server
```
Leaves server running for manual testing.

## Manual Testing

After running `./test_api.sh --keep-server`, you can:

1. **Visit API Documentation**: http://localhost:8000/docs
2. **Test Endpoints Manually**:
   ```bash
   # Health check
   curl http://localhost:8000/api/v1/health
   
   # Upload PDF for extraction
   curl -X POST \
     -F "file=@your_paper.pdf" \
     "http://localhost:8000/api/v1/extract/with-coordinates"
   ```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/health` | GET | Server health check |
| `/api/v1/config` | GET | Configuration info |
| `/api/v1/extract/simple` | POST | Basic PDF extraction |
| `/api/v1/extract/with-coordinates` | POST | PDF extraction with coordinates |
| `/api/v1/extract` | POST | PDF extraction with metadata |
| `/api/v1/ws/{session_id}` | WebSocket | Progress tracking |

## Expected Outputs

### Health Check
```json
{
  "status": "healthy",
  "service": "hci-extractor-api"
}
```

### Coordinate Extraction
```json
{
  "paper": {
    "paper_id": "uuid-string",
    "title": "Paper Title",
    "authors": ["Author 1", "Author 2"]
  },
  "extraction_summary": {
    "total_elements": 45,
    "elements_by_type": {
      "claim": 20,
      "finding": 15,
      "method": 10
    },
    "average_confidence": 0.89
  },
  "extracted_elements": [
    {
      "element_id": "uuid",
      "element_type": "finding",
      "text": "Extracted text here...",
      "confidence": 0.95,
      "coordinates": {
        "page_number": 1,
        "x": 72.0,
        "y": 156.8,
        "width": 420.2,
        "height": 12.0,
        "char_start": 1250,
        "char_end": 1380
      }
    }
  ]
}
```

## Troubleshooting

### Server Won't Start
- Check if port 8000 is already in use: `lsof -i :8000`
- Ensure virtual environment is activated
- Check dependencies: `pip list | grep -E "(fastapi|uvicorn)"`

### API Key Issues
- Verify `config.yaml` file exists and contains valid `gemini_api_key`
- Test API key at: https://aistudio.google.com/app/apikey
- Check for typos in the key
- Ensure API key is not set to placeholder value

### PDF Processing Fails
- Ensure PDF is not password-protected
- Check file size (max 50MB by default)
- Verify PDF has extractable text (not just images)

### Coordinate Mapping Issues
- Check that text was successfully extracted from PDF
- Fuzzy matching threshold may need adjustment
- Some elements may not get coordinates if text matching fails

## Performance Notes

- **Health Check**: < 1 second
- **Simple Extraction**: 5-30 seconds depending on PDF size
- **Coordinate Extraction**: 10-60 seconds (adds coordinate mapping)
- **PDF Download**: 5-15 seconds depending on connection

## Dependencies

### System (Fedora)
```bash
sudo dnf install curl jq bc
```

### Python (via venv)
- All dependencies auto-installed via `pip install -e .`
- Key packages: fastapi, uvicorn, fuzzywuzzy, pymupdf

## Security Notes

- Server runs on localhost only
- API keys stored in `config.yaml` (should be gitignored)
- No authentication required for testing
- CORS enabled for frontend development