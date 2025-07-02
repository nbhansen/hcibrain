# HCI Paper Extractor - Development Makefile
# Provides convenient shortcuts for common development tasks

.PHONY: help setup install test test-quick lint run clean dev demo

# Default target
help:
	@echo "🔧 HCI Paper Extractor Development Commands"
	@echo "============================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup      - Set up development environment from scratch"
	@echo "  make install    - Install/update dependencies"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test       - Run all tests with coverage"
	@echo "  make test-quick - Run tests without coverage (faster)"
	@echo "  make lint       - Run code formatting and quality checks"
	@echo ""
	@echo "Running:"
	@echo "  make run        - Show CLI help"
	@echo "  make demo       - Run demo extraction (requires PDF in data/)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean      - Clean build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make test"
	@echo "  make run ARGS='parse paper.pdf --output results.json'"
	@echo "  make demo PDF=data/sample.pdf"

# Check virtual environment
check-venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "❌ Virtual environment not activated!"; \
		echo "💡 Run: source venv/bin/activate"; \
		exit 1; \
	fi
	@echo "✅ Virtual environment active"

# Set up development environment
setup:
	@echo "🚀 Setting up development environment..."
	@if [ ! -d "venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python -m venv venv; \
	fi
	@echo "⚡ Activating virtual environment and installing dependencies..."
	@echo "💡 Run 'source venv/bin/activate' then 'make install'"

# Install dependencies
install: check-venv
	@echo "📦 Installing dependencies..."
	pip install --upgrade pip
	pip install -e .
	pip install -e ".[dev]"
	@echo "✅ Dependencies installed!"

# Run all tests with coverage
test: check-venv
	@echo "🧪 Running tests with coverage..."
	pytest tests/ -v --cov=src/hci_extractor --cov-report=term-missing
	@echo "✅ Tests completed!"

# Quick tests without coverage
test-quick: check-venv
	@echo "⚡ Running quick tests..."
	pytest tests/ -v
	python scripts/test.py
	@echo "✅ Quick tests completed!"

# Code quality checks
lint: check-venv
	@echo "🔍 Running code quality checks..."
	@echo "🎨 Formatting with black..."
	black src/ tests/
	@echo "📋 Checking imports with ruff..."
	ruff check src/ tests/ --fix
	@echo "🔍 Type checking with mypy..."
	mypy src/ --ignore-missing-imports
	@echo "✅ Code quality checks completed!"

# Run CLI tool
run: check-venv
	@if [ -z "$(ARGS)" ]; then \
		python -m hci_extractor --help; \
	else \
		python -m hci_extractor $(ARGS); \
	fi

# Demo extraction
demo: check-venv
	@if [ -n "$(PDF)" ]; then \
		echo "🔬 Running demo extraction on $(PDF)..."; \
		python -m hci_extractor parse "$(PDF)" --output demo_output.json; \
		echo "✅ Demo results saved to demo_output.json"; \
	elif ls data/*.pdf 1> /dev/null 2>&1; then \
		PDF=$$(ls data/*.pdf | head -1); \
		echo "🔬 Running demo extraction on $$PDF..."; \
		python -m hci_extractor parse "$$PDF" --output demo_output.json; \
		echo "✅ Demo results saved to demo_output.json"; \
	else \
		echo "❌ No PDF found. Usage: make demo PDF=path/to/paper.pdf"; \
	fi

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned build artifacts!"

# Development mode (placeholder)
dev: check-venv
	@echo "🔧 Development mode..."
	@echo "💡 For now, running quick tests. File watching not implemented yet."
	make test-quick