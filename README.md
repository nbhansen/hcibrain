# 🧠 HCIBrain Paper Skimming Assistant

**AI-powered research paper highlight extraction for HCI researchers**

Upload PDFs → Get highlighted Goals, Methods, and Results with precise coordinate mapping!

## 🚀 Quick Start

```bash
# One-command startup (includes quality checks)
./hcibrain.sh

# Just run without linting
./hcibrain.sh --skip-lint

# Check code quality only
./hcibrain.sh lint
```

**Access the app**: http://localhost:5173  
**API documentation**: http://localhost:8000

## 📁 Monorepo Structure

```
hcibrain/
├── packages/
│   ├── backend/          # Python FastAPI backend
│   │   ├── src/          # Source code
│   │   ├── tests/        # Test files  
│   │   ├── prompts/      # AI extraction prompts
│   │   ├── config.yaml   # Configuration
│   │   └── venv/         # Python virtual environment
│   └── frontend/         # React + Vite TypeScript frontend
│       ├── src/          # Source code
│       │   ├── App.tsx   # Main application
│       │   └── App.css   # Styling
│       └── package.json  # Dependencies
├── hcibrain.sh          # One-click startup script
├── package.json         # Monorepo configuration
└── docs/               # Documentation
```

## 🛠️ Development

### Backend (Python FastAPI)
```bash
cd packages/backend
source venv/bin/activate
uvicorn src.hci_extractor.web.app:app --reload
```

### Frontend (React + Vite TypeScript)  
```bash
cd packages/frontend
npm run dev
```

### Quality Checks
```bash
# Backend linting
cd packages/backend && source venv/bin/activate
python -m ruff check src/ --fix
python -m mypy src/

# Frontend linting  
cd packages/frontend
npm run lint
```

## ✨ Features

- **AI-powered extraction** using Google Gemini
- **HTML markup generation** with inline highlighting
- **Three-category system**: Goals, Methods, Results
- **Chunked processing** for large academic papers
- **Text cleaning** removes academic artifacts while preserving references
- **Enterprise-grade code quality** with comprehensive linting
- **Type-safe throughout** Python + TypeScript

## 🏗️ Architecture

- **Backend**: FastAPI + PyMuPDF + Google Gemini
- **Frontend**: React + Vite + TypeScript + CSS
- **Quality**: Ruff + MyPy + ESLint linting with zero-tolerance policy
- **Config**: YAML-based configuration with template system
- **Design**: Hexagonal architecture with dependency injection

## 📋 Requirements

- **Python 3.9+** with virtual environment
- **Node.js 18+** with npm
- **Google Gemini API key** (free tier available)

## 🔧 Configuration

1. Copy `packages/backend/config.template.yaml` to `packages/backend/config.yaml`
2. Add your Gemini API key
3. Customize extraction settings as needed

## 🧪 Testing

### Quick Health Check
```bash
./quick_test.sh          # Basic health check (no API key needed)
```

### Configuration Setup
```bash
./setup_config.sh        # Interactive config setup wizard
```

### Full API Testing
```bash
./test_api.sh            # Comprehensive API testing with PDF extraction
./test_api.sh --quick     # Quick health and config tests only
./test_api.sh --keep-server  # Leave server running for manual testing
```

## 📚 Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [Development Guidelines](./CLAUDE.md)
- [Code Review Findings](./CODEREVIEW.md)

## 🎯 Current Status

**Production Ready!** ✅
- All linting issues resolved (Python + TypeScript)
- Full architecture compliance with hexagonal design
- Complete immutability implementation
- Frontend follows React/TypeScript best practices
- Comprehensive quality gates enforced

---

**Made with ❤️ for HCI researchers who want to skim papers efficiently**