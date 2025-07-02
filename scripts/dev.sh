#!/bin/bash
# Development helper script for HCI Paper Extractor
# Usage: ./scripts/dev.sh [command]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
echo_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
echo_success() { echo -e "${GREEN}✅ $1${NC}"; }
echo_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
echo_error() { echo -e "${RED}❌ $1${NC}"; }

# Check if in virtual environment
check_venv() {
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        echo_error "Virtual environment not activated!"
        echo_info "Run: source venv/bin/activate"
        exit 1
    fi
    echo_success "Virtual environment active: $VIRTUAL_ENV"
}

# Install dependencies
install() {
    echo_info "Installing dependencies..."
    check_venv
    pip install -e .
    pip install -e ".[dev]"
    echo_success "Dependencies installed!"
}

# Run all tests
test() {
    echo_info "Running tests..."
    check_venv
    pytest tests/ -v --cov=src/hci_extractor --cov-report=term-missing
    echo_success "Tests completed!"
}

# Run quick tests (no coverage)
test_quick() {
    echo_info "Running quick tests..."
    check_venv
    pytest tests/ -v
    echo_success "Quick tests completed!"
}

# Run code quality checks
lint() {
    echo_info "Running code quality checks..."
    check_venv
    
    echo_info "Formatting with black..."
    black src/ tests/
    
    echo_info "Checking imports with ruff..."
    ruff check src/ tests/ --fix
    
    echo_info "Type checking with mypy..."
    mypy src/
    
    echo_success "Code quality checks completed!"
}

# Run the CLI tool
run() {
    echo_info "Running HCI Extractor CLI..."
    check_venv
    
    if [ $# -eq 0 ]; then
        python -m hci_extractor --help
    else
        python -m hci_extractor "$@"
    fi
}

# Extract from a sample PDF (if available)
demo() {
    echo_info "Running demo extraction..."
    check_venv
    
    # Look for sample PDFs
    if ls data/*.pdf 1> /dev/null 2>&1; then
        sample_pdf=$(ls data/*.pdf | head -1)
        echo_info "Using sample PDF: $sample_pdf"
        python -m hci_extractor parse "$sample_pdf" --output demo_output.json
        echo_success "Demo extraction saved to demo_output.json"
    else
        echo_warning "No sample PDFs found in data/ directory"
        echo_info "Usage: ./scripts/dev.sh demo path/to/paper.pdf"
        if [ $# -gt 0 ]; then
            python -m hci_extractor parse "$1" --output demo_output.json
            echo_success "Demo extraction saved to demo_output.json"
        fi
    fi
}

# Clean build artifacts
clean() {
    echo_info "Cleaning build artifacts..."
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info/
    rm -rf .pytest_cache/
    rm -rf __pycache__/
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    echo_success "Cleaned build artifacts!"
}

# Setup development environment from scratch
setup() {
    echo_info "Setting up development environment..."
    
    # Check if venv exists
    if [ ! -d "venv" ]; then
        echo_info "Creating virtual environment..."
        python -m venv venv
    fi
    
    echo_info "Activating virtual environment..."
    source venv/bin/activate
    
    echo_info "Upgrading pip..."
    pip install --upgrade pip
    
    install
    echo_success "Development environment setup complete!"
    echo_warning "Don't forget to activate the virtual environment: source venv/bin/activate"
}

# Development server with file watching (future enhancement)
dev() {
    echo_info "Development mode - running tests on file changes..."
    check_venv
    echo_warning "File watching not implemented yet. Running tests once..."
    test_quick
}

# Show help
help() {
    echo_info "HCI Paper Extractor Development Scripts"
    echo ""
    echo "Available commands:"
    echo "  setup       - Set up development environment from scratch"
    echo "  install     - Install/update dependencies"
    echo "  test        - Run all tests with coverage"
    echo "  test-quick  - Run tests without coverage (faster)"
    echo "  lint        - Run code formatting and quality checks"
    echo "  run [args]  - Run the CLI tool"
    echo "  demo [pdf]  - Run demo extraction on sample PDF"
    echo "  clean       - Clean build artifacts"
    echo "  dev         - Development mode (future: file watching)"
    echo "  help        - Show this help"
    echo ""
    echo "Examples:"
    echo "  ./scripts/dev.sh setup"
    echo "  ./scripts/dev.sh test"
    echo "  ./scripts/dev.sh run parse paper.pdf --output results.json"
    echo "  ./scripts/dev.sh demo data/sample_paper.pdf"
}

# Main command dispatcher
case "${1:-help}" in
    setup)      setup ;;
    install)    install ;;
    test)       test ;;
    test-quick) test_quick ;;
    lint)       lint ;;
    run)        shift; run "$@" ;;
    demo)       shift; demo "$@" ;;
    clean)      clean ;;
    dev)        dev ;;
    help)       help ;;
    *)          echo_error "Unknown command: $1"; help; exit 1 ;;
esac