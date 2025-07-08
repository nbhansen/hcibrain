# 🧠 HCIBrain Paper Skimming Assistant - Quick Start

## One-Command Startup

```bash
./hcibrain.sh
```

That's it! The script will:
- ✅ Check all dependencies
- ✅ Start the backend API server
- ✅ Start the frontend web app  
- ✅ Give you the URL to access your paper skimming assistant

## First Time Setup

1. **Get a Google Gemini API key** (free): https://aistudio.google.com/app/apikey

2. **Configure the system**:
   ```bash
   cp config.template.yaml config.yaml
   # Edit config.yaml and add your Gemini API key
   ```

3. **Start HCIBrain**:
   ```bash
   ./hcibrain.sh
   ```

## Usage

Once running, open the provided URL (usually http://localhost:3000) and:

1. **Upload a PDF** - Drag & drop any research paper
2. **Wait for extraction** - AI analyzes and finds key elements  
3. **See highlights** - Goals (blue), Methods (amber), Results (rose)
4. **Customize** - Adjust opacity, count, confidence threshold

## Commands

```bash
./hcibrain.sh         # Start HCIBrain
./hcibrain.sh stop    # Stop all processes
./hcibrain.sh status  # Check if running
./hcibrain.sh help    # Show help
```

## What You Get

- 🔥 **Real PDF rendering** with PDF.js
- 🤖 **AI-powered extraction** using Google Gemini
- 🎯 **Smart highlighting** of Goals, Methods, Results
- 🎨 **Interactive controls** for opacity, filtering, confidence
- 📊 **Extraction summaries** with confidence scores
- 🚀 **Modern UI** built with Next.js + Tailwind CSS

## Troubleshooting

**Backend won't start?**
- Check your Gemini API key in `config.yaml`
- Ensure virtual environment exists: `python -m venv venv`

**Frontend won't start?**
- Install dependencies: `cd academic-paper-skimming-assistant && npm install`

**PDF extraction fails?**
- Verify your Gemini API key is valid
- Check the PDF isn't password protected
- Ensure PDF has extractable text (not just images)

## Architecture

- **Backend**: FastAPI + PyMuPDF + Google Gemini LLM
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS  
- **Integration**: REST API with coordinate mapping for highlights
- **Configuration**: Single YAML file for all settings

Built following hexagonal architecture with immutable design patterns. 🏗️✨