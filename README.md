# HCIBrain

**Academic Paper Analysis System**

An AI-powered system for extracting and highlighting key research components from academic papers. The system identifies research goals, methodologies, and results using large language models to assist in academic paper review and analysis.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-19.0-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)

---

## Overview

HCIBrain processes PDF research papers and automatically identifies and categorizes key academic components:

- **Research Goals** - Objectives, research questions, and hypotheses
- **Methods** - Approaches, techniques, and methodologies  
- **Results** - Findings, outcomes, and empirical data
- **Plain Language Summaries** - Accessible explanations for broader audiences

### System Features

- Smart PDF processing with automatic text chunking for large documents
- Interactive web interface with filtering and navigation capabilities
- Mobile-responsive design for cross-platform access
- Hexagonal architecture with comprehensive test coverage
- Security-focused implementation with input sanitization

---

## Installation and Setup

### Prerequisites

- Python 3.11 or higher with pip
- Node.js 18 or higher with npm
- Google Gemini API key (obtain from [Google AI Studio](https://aistudio.google.com/app/apikey))

### System Setup

1. **Clone and initialize the repository:**

```bash
git clone https://github.com/yourusername/hcibrain.git
cd hcibrain
```

2. **Setup backend environment:**

```bash
cd packages/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

3. **Setup frontend environment:**

```bash
cd ../frontend
npm install
cd ../..
```

4. **Configure API access:**

```bash
cp packages/backend/config.template.yaml packages/backend/config.yaml
```

Edit `packages/backend/config.yaml` with your API credentials:

```yaml
api:
  provider_type: "gemini"
  gemini_api_key: "your-api-key-here"
  timeout_seconds: 30.0
  max_retries: 3
```

### Application Startup

Start both backend and frontend services:

```bash
# Complete startup with quality checks
./hcibrain.sh

# Quick startup without linting
./hcibrain.sh --skip-lint
```

Access the web interface at [http://localhost:5173](http://localhost:5173)

---

## System Usage

### Web Interface

The primary interface provides:

- PDF upload with file validation
- Real-time processing status updates
- Color-coded highlighting system for different content types
- Interactive filtering controls for content categories
- Automatic table of contents generation and navigation
- Responsive layout for various screen sizes

### API Integration

REST API endpoints for programmatic access:

```bash
# System health verification
curl http://localhost:8000/api/v1/health

# Document processing
curl -X POST http://localhost:8000/api/v1/extract/markup \
  -F "file=@document.pdf"

# API documentation
curl http://localhost:8000/docs
```

---

## Architecture

### System Structure

The system implements hexagonal architecture principles with clear separation between domain logic and infrastructure concerns:

```
packages/
├── backend/                 # Python FastAPI Backend
│   ├── src/hci_extractor/
│   │   ├── core/           # Domain Logic and Business Rules
│   │   ├── infrastructure/ # External Service Adapters
│   │   ├── providers/      # LLM Provider Integrations  
│   │   ├── web/           # REST API and WebSocket Interface
│   │   └── utils/         # Utility Functions and Helpers
│   ├── tests/             # Comprehensive Test Suite
│   ├── config.yaml        # System Configuration
│   └── prompts/           # LLM Prompt Templates
└── frontend/               # React TypeScript Frontend
    ├── src/
    │   ├── App.tsx        # Main Application Component
    │   ├── ErrorBoundary.tsx  # Error Handling
    │   └── constants.ts   # Configuration Constants
    └── dist/              # Production Build Output
```

### Design Principles

- **Immutable Data Structures** - All objects are frozen and immutable
- **Dependency Injection** - Comprehensive DI container with no global state
- **Event-Driven Architecture** - Loose coupling through domain events
- **Type Safety** - Complete TypeScript and Python type annotations
- **Test-Driven Development** - Comprehensive test coverage with architecture compliance verification

---

## Development

### Project Organization

The monorepo structure separates concerns between:

- **Backend** (`packages/backend/`) - Python FastAPI application with domain logic
- **Frontend** (`packages/frontend/`) - React TypeScript single-page application
- **Configuration** - Shared configuration files and development scripts

### Development Workflow

1. **Code Quality Enforcement** - All code must pass linting and type checking
2. **Test-Driven Development** - Comprehensive test suite with architectural compliance testing
3. **Security-First Approach** - Input validation and XSS protection measures
4. **Performance Optimization** - Asynchronous processing and efficient memory management

### Testing

Execute the test suite:

```bash
# Backend comprehensive testing
cd packages/backend
source venv/bin/activate
python -m pytest

# Frontend build verification
cd packages/frontend
npm run build

# Complete system quality verification
./hcibrain.sh lint
```

### Code Quality Standards

The system enforces strict quality standards:

- **Python**: Ruff for linting and formatting
- **TypeScript**: ESLint for code quality verification
- **Architecture**: Automated compliance testing for design principles
- **Security**: Input validation and content sanitization

---

## Configuration

### Environment Variables

```bash
# Required configuration
GEMINI_API_KEY=your-api-key-here

# Optional settings
HCI_LOG_LEVEL=INFO
HCI_MAX_FILE_SIZE=50MB
HCI_TIMEOUT_SECONDS=30
```

### Configuration File Options

The `config.yaml` file supports comprehensive system customization:

```yaml
api:
  provider_type: "gemini"
  gemini_api_key: "${GEMINI_API_KEY}"
  timeout_seconds: 30.0
  max_retries: 3

extraction:
  max_file_size_mb: 50
  chunk_size: 12000
  chunk_overlap: 200

analysis:
  confidence_threshold: 0.50
  max_concurrent_sections: 3
  temperature: 0.1
```

---

## API Reference

### REST Endpoints

#### System Health Check
```http
GET /api/v1/health
```

Returns system status and availability information.

#### Document Markup Extraction
```http
POST /api/v1/extract/markup
Content-Type: multipart/form-data

file: PDF document (required)
```

**Response Format:**
```json
{
  "paper_full_text_with_markup": "<goal confidence=\"0.95\">Research objective</goal>",
  "paper_info": {
    "title": "Document Title",
    "authors": ["Author Name"],
    "paper_id": "unique-identifier"
  },
  "plain_language_summary": "Research summary description",
  "processing_time_seconds": 45.2
}
```

### WebSocket Interface

Real-time progress updates available via WebSocket connection:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/progress');

// Progress update format
{
  "type": "progress",
  "data": {
    "progress": 0.75,
    "message": "Processing section 3 of 4",
    "stage": "analysis"
  }
}
```

---

## Performance Characteristics

### Processing Benchmarks

- **Small Documents** (under 5 pages): 15-30 seconds
- **Medium Documents** (5-15 pages): 30-90 seconds  
- **Large Documents** (15+ pages): 90-300 seconds

Performance varies based on document complexity, API response latency, and system resources.

### Optimization Features

- **Chunked Processing** - Handles large documents without memory constraints
- **Asynchronous Operations** - Non-blocking I/O for improved responsiveness
- **Immutable Object Design** - Efficient memory utilization and garbage collection
- **Intelligent Caching** - Reduces redundant API requests

---

## Security Implementation

### Security Measures

- **Input Validation** - Comprehensive file type, size, and content verification
- **HTML Sanitization** - DOMPurify integration prevents cross-site scripting attacks
- **Credential Management** - Environment-based secret management with no hardcoded keys
- **Rate Limiting** - API request throttling to prevent abuse and quota exhaustion
- **Error Sanitization** - Prevents sensitive information disclosure in error responses

---

## Development Guidelines

### Contributing Standards

1. **Repository Setup** - Fork the repository and create feature branches
2. **Development Environment** - Follow the installation and setup procedures
3. **Quality Verification** - Execute `./hcibrain.sh lint` before submitting changes
4. **Test Coverage** - Include comprehensive tests for new functionality
5. **Documentation** - Update relevant documentation for system changes

### Code Standards

- **Python Development** - Adhere to PEP 8, include type hints, write comprehensive docstrings
- **TypeScript Development** - Use strict mode, avoid `any` types, implement proper error handling
- **Architecture Compliance** - Maintain hexagonal architecture design principles
- **Testing Requirements** - All new functionality must include corresponding test coverage

---

## System Diagnostics

### Troubleshooting Common Issues

**Backend Service Issues:**
- Verify API key configuration in `config.yaml`
- Check service logs in `backend.log` for detailed error information
- Confirm Python virtual environment activation

**Frontend Application Issues:**
- Verify Node.js dependencies are installed with `npm install`
- Check TypeScript compilation with `npm run build`
- Review browser console for JavaScript errors

**Processing Performance Issues:**
- Large documents require extended processing time
- Verify network connectivity for API requests
- Monitor system resource utilization during processing

### Diagnostic Commands

```bash
# Service status verification
./hcibrain.sh status

# Comprehensive quality verification
./hcibrain.sh lint

# Log file examination
tail -f backend.log frontend.log
```

---

## License

This project is licensed under the MIT License. See the LICENSE file for complete terms and conditions.

---

## Contact and Support

**Author:** Nicolai Brodersen Hansen  
**Website:** [https://www.nbhansen.dk](https://www.nbhansen.dk)

For technical support, please review the troubleshooting section and examine system logs before reporting issues.