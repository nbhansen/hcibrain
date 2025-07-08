#!/bin/bash
# Configuration Setup Script for HCIBrain YAML Configuration

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

setup_config_file() {
    log "Setting up YAML configuration..."
    
    if [[ -f config.yaml ]]; then
        success "config.yaml file already exists"
        
        # Check if it has a placeholder API key
        if grep -q "your-gemini-api-key-here" config.yaml; then
            warning "API key is still set to placeholder value"
        else
            success "API key appears to be configured"
            return 0
        fi
    fi
    
    echo
    echo "=========================================="
    echo "Google Gemini API Key Setup Required"
    echo "=========================================="
    echo
    echo "To use HCIBrain extraction functionality, you need a Google Gemini API key."
    echo
    echo "Steps to get your API key:"
    echo "1. Go to: https://aistudio.google.com/app/apikey"
    echo "2. Create a new API key"
    echo "3. Copy the key"
    echo
    
    read -p "Do you have a Gemini API key? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -n "Enter your Gemini API key: "
        read -s api_key
        echo
        
        # Update the config.yaml file with the API key
        if [[ -f config.yaml ]]; then
            # Replace the placeholder key
            sed -i "s/your-gemini-api-key-here/$api_key/" config.yaml
        else
            # This shouldn't happen since config.yaml should exist, but just in case
            warning "config.yaml not found. Run this script from the project root."
            return 1
        fi
        
        success "API key added to config.yaml"
    else
        warning "API key not configured. Some tests may fail."
        echo "You can add it later by editing config.yaml:"
        echo "  api:"
        echo "    gemini_api_key: \"your-api-key-here\""
    fi
    
    echo
    log "Configuration file ready: config.yaml"
}

check_dependencies() {
    log "Checking system dependencies..."
    
    # Check if bc is installed (for performance timing)
    if ! command -v bc &> /dev/null; then
        warning "bc is not installed. Install with: sudo dnf install bc"
        echo "This is needed for performance timing in tests."
    fi
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        warning "jq is not installed. Install with: sudo dnf install jq"
        echo "This is recommended for better JSON output formatting."
    fi
    
    success "Dependency check complete"
}

show_next_steps() {
    echo
    echo "=========================================="
    echo "Setup Complete! Next Steps:"
    echo "=========================================="
    echo
    echo "1. Run API tests:"
    echo "   ./test_api.sh"
    echo
    echo "2. Quick test (no PDF download):"
    echo "   ./test_api.sh --quick --no-download"
    echo
    echo "3. Keep server running for manual testing:"
    echo "   ./test_api.sh --keep-server"
    echo
    echo "4. View help:"
    echo "   ./test_api.sh --help"
    echo
    echo "Configuration file location: config.yaml"
    echo "Edit this file to customize settings."
    echo
    echo "Optional: Install recommended packages:"
    echo "   sudo dnf install jq bc"
    echo
}

main() {
    echo
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE} HCIBrain Configuration Setup${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
    
    setup_config_file
    check_dependencies
    show_next_steps
}

main "$@"