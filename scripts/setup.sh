#!/bin/bash

# HCI Paper Extractor - One-Command Setup Script
# Follows CLAUDE.md principles: minimal dependencies, clear error handling, user-friendly

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
check_project_directory() {
    if [[ ! -f "pyproject.toml" ]] || [[ ! -d "src/hci_extractor" ]]; then
        print_error "This script must be run from the HCI Paper Extractor project root directory."
        print_error "Make sure you're in the directory containing pyproject.toml and src/hci_extractor/"
        exit 1
    fi
}

# Check Python version
check_python() {
    print_step "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        print_error "Please install Python 3.9+ from https://python.org"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.9"
    
    if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
        print_error "Python $required_version or higher is required. Found: $python_version"
        print_error "Please upgrade Python from https://python.org"
        exit 1
    fi
    
    print_success "Python $python_version detected"
}

# Create virtual environment
setup_venv() {
    print_step "Setting up virtual environment..."
    
    # Remove existing venv if it exists and user confirms
    if [[ -d "venv" ]]; then
        print_warning "Virtual environment already exists."
        read -p "Remove existing venv and create fresh? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
            print_success "Removed existing virtual environment"
        else
            print_success "Using existing virtual environment"
            return 0
        fi
    fi
    
    python3 -m venv venv
    print_success "Virtual environment created"
}

# Activate virtual environment and install dependencies
install_dependencies() {
    print_step "Installing dependencies..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip first
    python -m pip install --upgrade pip
    
    # Install the package in development mode
    pip install -e .
    
    print_success "Dependencies installed successfully"
}

# Setup API key
setup_api_key() {
    print_step "Setting up API key..."
    
    if [[ -f ".env" ]]; then
        if grep -q "GEMINI_API_KEY" .env; then
            existing_key=$(grep "GEMINI_API_KEY" .env | cut -d'=' -f2)
            if [[ -n "$existing_key" && "$existing_key" != "your-api-key-here" ]]; then
                print_success "API key already configured in .env file"
                return 0
            fi
        fi
    fi
    
    echo
    echo "You need a Google Gemini API key to use this tool."
    echo "Get your free API key at: https://makersuite.google.com/app/apikey"
    echo
    read -p "Enter your Gemini API key (or press Enter to skip): " api_key
    
    if [[ -n "$api_key" ]]; then
        echo "GEMINI_API_KEY=$api_key" > .env
        print_success "API key saved to .env file"
    else
        print_warning "API key setup skipped. You can add it later to .env file:"
        print_warning "echo 'GEMINI_API_KEY=your-api-key' > .env"
    fi
}

# Test installation
test_installation() {
    print_step "Testing installation..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Test basic CLI functionality
    if python -m hci_extractor --help > /dev/null 2>&1; then
        print_success "CLI interface working correctly"
    else
        print_error "CLI interface test failed"
        return 1
    fi
    
    # Test API key if configured
    if [[ -f ".env" ]] && grep -q "GEMINI_API_KEY" .env; then
        api_key=$(grep "GEMINI_API_KEY" .env | cut -d'=' -f2)
        if [[ -n "$api_key" && "$api_key" != "your-api-key-here" ]]; then
            print_step "Testing API key configuration..."
            # We don't actually test the API to avoid using quota, just validate format
            if [[ ${#api_key} -gt 20 ]]; then
                print_success "API key format looks valid"
            else
                print_warning "API key may be invalid (too short)"
            fi
        fi
    fi
}

# Main setup function
main() {
    echo
    echo "=========================================="
    echo "  HCI Paper Extractor - Setup Script"
    echo "=========================================="
    echo
    echo "This script will:"
    echo "1. Check Python installation"
    echo "2. Create virtual environment"
    echo "3. Install dependencies"
    echo "4. Configure API key"
    echo "5. Test installation"
    echo
    
    check_project_directory
    check_python
    setup_venv
    install_dependencies
    setup_api_key
    test_installation
    
    echo
    echo "=========================================="
    print_success "Setup complete! 🎉"
    echo "=========================================="
    echo
    echo "🚀 Ready to try the new progress tracking features!"
    echo
    echo "QUICK TEST (copy-paste these commands):"
    echo "----------------------------------------"
    echo "# 1. Activate the virtual environment"
    echo "source venv/bin/activate"
    echo
    echo "# 2. Test with the included sample paper (watch the progress bars!)"
    echo "python -m hci_extractor extract autisticadults.pdf --output test_results.csv"
    echo
    echo "# 3. View the extracted results (CSV format auto-detected from extension!)"
    echo "head -20 test_results.csv"
    echo
    echo "# 4. For help and all commands"
    echo "python -m hci_extractor --help"
    echo "----------------------------------------"
    echo
    if [[ ! -f ".env" ]] || ! grep -q "GEMINI_API_KEY" .env; then
        echo "⚠️  Remember to add your API key to .env file:"
        echo "   echo 'GEMINI_API_KEY=your-api-key' > .env"
        echo
    fi
    echo "You'll see beautiful progress bars with:"
    echo "• 🔄 Real-time PDF extraction progress"
    echo "• 🔍 Section detection status"  
    echo "• 🤖 LLM analysis with ETA calculations"
    echo "• ✅ Completion summary with statistics"
    echo
    echo "🔧 Need help? Try these commands:"
    echo "• python -m hci_extractor setup    # Interactive setup wizard"
    echo "• python -m hci_extractor doctor   # Diagnose issues"
    echo
    echo "Happy researching! 📚"
    echo
}

# Handle errors gracefully
trap 'print_error "Setup failed. Check the error messages above."; exit 1' ERR

# Run main function
main "$@"