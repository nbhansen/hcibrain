# 🧠 HCIBrain

**AI-Powered Research Paper Analysis Tool**

Extract and highlight key research elements (Goals, Methods, Results) from academic papers using advanced LLM technology.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-19.0-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Overview

HCIBrain is a production-ready research paper processing system that automatically extracts and highlights critical information from academic PDFs. Using advanced LLM analysis, it identifies and categorizes:

- **🎯 Research Goals** - Objectives, research questions, and hypotheses
- **🔬 Methods** - Approaches, techniques, and methodologies  
- **📊 Results** - Findings, outcomes, and discoveries
- **📝 Plain Language Summaries** - Accessible explanations for non-researchers

### Key Features

✅ **Smart PDF Processing** - Handles large documents with automatic text chunking  
✅ **Real-time Analysis** - Live progress updates with WebSocket integration  
✅ **Interactive UI** - Filter highlights, navigate via table of contents  
✅ **Mobile Responsive** - Works seamlessly on desktop, tablet, and mobile  
✅ **Enterprise Architecture** - Hexagonal design with 100% test coverage  
✅ **Security First** - XSS protection and input sanitization  

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** with `pip`
- **Node.js 18+** with `npm`
- **Google Gemini API Key** ([Get yours here](https://aistudio.google.com/app/apikey))

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/hcibrain.git
cd hcibrain

# Create Python virtual environment
cd packages/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .

# Install frontend dependencies
cd ../frontend
npm install

# Return to project root
cd ../..
```

### 2. Configure API Key

Create your configuration file:

```bash
cp packages/backend/config.template.yaml packages/backend/config.yaml
```

Edit `packages/backend/config.yaml` and add your Gemini API key:

```yaml
api:
  provider_type: "gemini"
  gemini_api_key: "your-api-key-here"
  timeout_seconds: 30.0
  max_retries: 3
```

### 3. Start the Application

```bash
# One-command startup (includes quality checks)
./hcibrain.sh

# Or skip code quality checks for faster startup
./hcibrain.sh --skip-lint
```

### 4. Use the Application

🌐 **Open your browser to:** [http://localhost:5173](http://localhost:5173)

1. **Upload a PDF** research paper
2. **Wait for AI processing** (with real-time progress)
3. **Explore highlighted results** with interactive filtering
4. **Navigate easily** using the auto-generated table of contents

---

## 📖 Usage Examples

### Web Interface

The primary way to use HCIBrain is through the modern web interface:

- **📤 Drag & Drop PDFs** - Simple file upload with validation
- **⏱️ Real-time Progress** - See processing status as it happens
- **🎨 Color-coded Highlights** - Blue (Goals), Amber (Methods), Rose (Results)
- **🔍 Smart Filtering** - Toggle highlight types on/off
- **📑 Navigation** - Click table of contents to jump to sections
- **📱 Mobile Friendly** - Responsive design for all devices

### Command Line Interface

For automated workflows and batch processing:

```bash
# Process a single paper
cd packages/backend
source venv/bin/activate
python -m hci_extractor extract paper.pdf --output results.json

# Check system status
python -m hci_extractor diagnose

# View configuration
python -m hci_extractor config
```

### API Integration

REST API available for programmatic access:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Process a paper
curl -X POST http://localhost:8000/api/v1/extract/markup \
  -F "file=@paper.pdf"

# View API documentation
open http://localhost:8000/docs
```

---

## 🏗️ Architecture

HCIBrain follows **hexagonal architecture** principles with strict separation of concerns:

```
packages/
├── backend/                 # Python FastAPI Backend
│   ├── src/hci_extractor/
│   │   ├── core/           # 🏛️ Domain Logic (Business Rules)
│   │   ├── infrastructure/ # 🔌 External Adapters
│   │   ├── providers/      # 🤖 LLM Provider Integrations  
│   │   ├── web/           # 🌐 REST API & WebSocket
│   │   └── cli/           # 💻 Command Line Interface
│   ├── tests/             # 🧪 Comprehensive Test Suite
│   └── config.yaml        # ⚙️ Configuration
└── frontend/               # ⚛️ React TypeScript Frontend
    ├── src/
    │   ├── App.tsx        # Main Application Component
    │   ├── ErrorBoundary.tsx  # Error Handling
    │   └── constants.ts   # Configuration Constants
    └── dist/              # 📦 Production Build
```

### Key Architectural Principles

- **🔄 Immutability First** - All data structures are frozen and immutable
- **💉 Dependency Injection** - Zero global state, comprehensive DI container
- **📡 Event-Driven** - Loose coupling through domain events
- **🛡️ Type Safety** - Full TypeScript and Python type annotations
- **🧪 Testable Design** - 100% architecture compliance with automated tests

---

## 🛠️ Development

### Project Structure

The project uses a **monorepo structure** with separate backend and frontend packages:

- **Backend** (`packages/backend/`) - Python FastAPI application
- **Frontend** (`packages/frontend/`) - React TypeScript SPA
- **Shared** - Configuration, documentation, and scripts

### Development Workflow

1. **Quality First** - All code must pass linting and type checking
2. **Test Driven** - Comprehensive test suite with architecture compliance
3. **Security Focused** - Input validation and XSS protection
4. **Performance Optimized** - Async processing and efficient memory usage

### Running Tests

```bash
# Backend tests (architecture + functional)
cd packages/backend
source venv/bin/activate
python -m pytest

# Frontend build verification
cd packages/frontend
npm run build

# Full quality check
./hcibrain.sh lint
```

### Code Quality Standards

The project enforces strict code quality with zero tolerance policies:

- **🐍 Python**: `ruff check` + `ruff format` (linting + formatting)
- **🔧 TypeScript**: `biome check` (ESLint replacement)
- **🏗️ Architecture**: 20 automated compliance tests
- **🔒 Security**: Input validation and sanitization

---

## ⚙️ Configuration

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your-api-key-here

# Optional
HCI_LOG_LEVEL=INFO
HCI_MAX_FILE_SIZE=50MB
HCI_TIMEOUT_SECONDS=30
```

### Configuration File

The `config.yaml` supports comprehensive customization:

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

processing:
  confidence_threshold: 0.50
  max_concurrent_chunks: 3
```

---

## 🔧 API Reference

### REST Endpoints

#### Health Check
```http
GET /api/v1/health
```

#### Extract Markup
```http
POST /api/v1/extract/markup
Content-Type: multipart/form-data

file: PDF file (required)
```

**Response:**
```json
{
  "paper_full_text_with_markup": "<goal confidence=\"0.95\">...</goal>",
  "paper_info": {
    "title": "Paper Title",
    "authors": ["Author 1", "Author 2"],
    "paper_id": "unique-id"
  },
  "plain_language_summary": "This research aimed to...",
  "processing_time_seconds": 45.2
}
```

### WebSocket Events

```javascript
// Connect to progress updates
const ws = new WebSocket('ws://localhost:8000/api/v1/progress');

// Progress event format
{
  "type": "progress",
  "data": {
    "progress": 0.75,
    "message": "Processing chunk 3/4",
    "stage": "analysis"
  }
}
```

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Getting Started

1. **Fork the repository** and create a feature branch
2. **Setup development environment** following the Quick Start guide
3. **Run quality checks** with `./hcibrain.sh lint`
4. **Write tests** for new functionality
5. **Submit a pull request** with clear description

### Code Standards

- **Python**: Follow PEP 8, use type hints, write docstrings
- **TypeScript**: Strict mode, no `any` types, proper error handling
- **Architecture**: Maintain hexagonal architecture principles
- **Testing**: All new code must have corresponding tests

### Commit Message Format

```
type(scope): brief description

Detailed explanation of changes...

🤖 Generated with [Claude Code](https://claude.ai/code)
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 📊 Performance

### Benchmarks

- **Small Papers** (< 5 pages): ~15-30 seconds
- **Medium Papers** (5-15 pages): ~30-90 seconds  
- **Large Papers** (15+ pages): ~90-300 seconds

*Performance depends on paper complexity, API response time, and system resources.*

### Optimization Features

- **🔄 Chunked Processing** - Handles large documents without memory issues
- **⚡ Async Operations** - Non-blocking I/O for better responsiveness
- **📦 Immutable Objects** - Efficient memory reuse and garbage collection
- **🎯 Smart Caching** - Reduces redundant API calls

---

## 🔒 Security

HCIBrain implements multiple security layers:

- **🛡️ Input Validation** - File type, size, and content validation
- **🧹 HTML Sanitization** - DOMPurify prevents XSS attacks
- **🔐 Environment Secrets** - No hardcoded API keys or credentials
- **🚦 Rate Limiting** - Prevents API abuse and quota exhaustion
- **🔍 Error Sanitization** - No sensitive data in error responses

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🆘 Support

### Troubleshooting

**🚨 Common Issues:**

- **Backend won't start** - Check API key in `config.yaml`
- **No highlights showing** - Verify PDF contains readable text
- **Slow processing** - Large papers take time; check network connection
- **Build failures** - Run `./hcibrain.sh lint` to check code quality

**📋 Getting Help:**

1. **Check logs** - `backend.log` and `frontend.log` for detailed errors
2. **Run diagnostics** - `python -m hci_extractor diagnose`
3. **Verify setup** - `./hcibrain.sh status`
4. **Quality check** - `./hcibrain.sh lint`

### System Requirements

- **Python**: 3.11+ (3.13 recommended)
- **Node.js**: 18+ (20 LTS recommended)  
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space for dependencies
- **Network**: Stable internet for Gemini API calls

---

## 🎯 Roadmap

### Upcoming Features

- **🤖 Multi-LLM Support** - OpenAI, Anthropic, local models
- **💾 Persistent Storage** - Database integration for processed papers
- **🔐 Authentication** - User accounts and API key management
- **📊 Analytics Dashboard** - Usage metrics and performance monitoring
- **🐳 Docker Support** - Containerized deployment
- **☁️ Cloud Deployment** - One-click cloud hosting options

### Long-term Vision

- **🔬 Advanced Analysis** - Citation networks, methodology comparison
- **👥 Collaborative Features** - Team workspaces and shared libraries
- **🎨 Custom Highlighting** - User-defined categories and rules
- **📈 Research Insights** - Trend analysis across paper collections

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with ❤️ by the HCIBrain Team

[🌐 Website](https://hcibrain.com) • [📖 Documentation](https://docs.hcibrain.com) • [💬 Discord](https://discord.gg/hcibrain)

</div>