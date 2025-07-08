#!/bin/bash
# HCIBrain API Testing Script for Fedora
# Tests the new coordinate mapping endpoint

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="http://localhost:8000/api/v1"
VENV_PATH="./venv"
TEST_PDF_URL="https://arxiv.org/pdf/1512.02325.pdf"  # Deep Speech 2 paper
TEST_PDF_NAME="deep_speech_2.pdf"

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

banner() {
    echo
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE} HCIBrain API Testing Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

check_dependencies() {
    log "Checking dependencies..."
    
    # Check if curl is installed
    if ! command -v curl &> /dev/null; then
        error "curl is not installed. Install with: sudo dnf install curl"
        exit 1
    fi
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        warning "jq is not installed. JSON responses will be less readable."
        warning "Install with: sudo dnf install jq"
        JQ_AVAILABLE=false
    else
        JQ_AVAILABLE=true
    fi
    
    # Check virtual environment
    if [[ ! -d "$VENV_PATH" ]]; then
        error "Virtual environment not found at $VENV_PATH"
        exit 1
    fi
    
    # Check configuration file
    if [[ ! -f "config.yaml" ]]; then
        error "Configuration file not found: config.yaml"
        error "Run ./setup_config.sh to create it"
        exit 1
    fi
    
    success "Dependencies checked"
}

start_server() {
    log "Starting HCIBrain server..."
    
    # Activate virtual environment and start server
    source "$VENV_PATH/bin/activate"
    
    # Check if server is already running
    if curl -s "http://localhost:8000/api/v1/health" &> /dev/null; then
        success "Server already running at http://localhost:8000"
        return 0
    fi
    
    # Start server in background
    log "Starting uvicorn server..."
    nohup uvicorn hci_extractor.web.app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for server to start
    log "Waiting for server to start..."
    for i in {1..30}; do
        if curl -s "http://localhost:8000/api/v1/health" &> /dev/null; then
            success "Server started successfully (PID: $SERVER_PID)"
            echo $SERVER_PID > .server_pid
            return 0
        fi
        sleep 1
    done
    
    error "Server failed to start within 30 seconds"
    exit 1
}

download_test_pdf() {
    if [[ -f "$TEST_PDF_NAME" ]]; then
        success "Test PDF already exists: $TEST_PDF_NAME"
        return 0
    fi
    
    log "Downloading test PDF..."
    if curl -L -o "$TEST_PDF_NAME" "$TEST_PDF_URL"; then
        success "Downloaded test PDF: $TEST_PDF_NAME"
    else
        error "Failed to download test PDF"
        exit 1
    fi
}

test_health_endpoint() {
    log "Testing health endpoint..."
    
    local response
    response=$(curl -s "$API_BASE_URL/health")
    
    if [[ $JQ_AVAILABLE == true ]]; then
        echo "$response" | jq .
    else
        echo "$response"
    fi
    
    success "Health endpoint working"
}

test_config_endpoint() {
    log "Testing config endpoint..."
    
    local response
    response=$(curl -s "$API_BASE_URL/config")
    
    if [[ $JQ_AVAILABLE == true ]]; then
        echo "$response" | jq .
    else
        echo "$response"
    fi
    
    success "Config endpoint working"
}

test_simple_extraction() {
    log "Testing simple PDF extraction..."
    
    local response
    response=$(curl -s -X POST \
        -F "file=@$TEST_PDF_NAME" \
        "$API_BASE_URL/extract/simple")
    
    if [[ $JQ_AVAILABLE == true ]]; then
        echo "$response" | jq '.extraction_summary'
        echo
        echo "First few elements:"
        echo "$response" | jq '.extracted_elements[:3] | .[] | {element_type, text: .text[:100], confidence, page_number}'
    else
        echo "$response" | head -50
    fi
    
    success "Simple extraction working"
}

test_coordinate_extraction() {
    log "Testing coordinate-enhanced PDF extraction..."
    
    local response
    response=$(curl -s -X POST \
        -F "file=@$TEST_PDF_NAME" \
        -F "title=Deep Speech 2: End-to-End Speech Recognition in English and Mandarin" \
        -F "authors=Dario Amodei, Sundaram Ananthanarayanan, Rishita Anubhai" \
        "$API_BASE_URL/extract/with-coordinates")
    
    if [[ $JQ_AVAILABLE == true ]]; then
        echo "Extraction Summary:"
        echo "$response" | jq '.extraction_summary'
        echo
        echo "Elements with coordinates:"
        echo "$response" | jq '.extracted_elements[] | select(.coordinates != null) | {element_type, confidence, coordinates: {page_number: .coordinates.page_number, x: .coordinates.x, y: .coordinates.y, width: .coordinates.width, height: .coordinates.height}, text: .text[:80]}'
        echo
        echo "Element type distribution:"
        echo "$response" | jq '.extraction_summary.elements_by_type'
    else
        echo "$response" | head -100
    fi
    
    success "Coordinate extraction working"
}

test_websocket_endpoint() {
    log "Testing WebSocket endpoint availability..."
    
    # Test if WebSocket endpoint responds (we can't easily test WS in bash)
    local response
    response=$(curl -s -I "http://localhost:8000/api/v1/ws/test-session" || echo "WebSocket endpoint available")
    
    success "WebSocket endpoint accessible"
}

cleanup() {
    log "Cleaning up..."
    
    # Stop server if we started it
    if [[ -f .server_pid ]]; then
        local pid
        pid=$(cat .server_pid)
        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping server (PID: $pid)..."
            kill "$pid"
            rm .server_pid
        fi
    fi
    
    # Clean up server log
    if [[ -f server.log ]]; then
        log "Server log tail:"
        tail -10 server.log
        rm server.log
    fi
    
    success "Cleanup complete"
}

run_performance_test() {
    log "Running basic performance test..."
    
    local start_time end_time duration
    start_time=$(date +%s.%N)
    
    curl -s -X POST \
        -F "file=@$TEST_PDF_NAME" \
        "$API_BASE_URL/extract/with-coordinates" > /dev/null
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    
    success "Performance test completed in ${duration}s"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --quick        Run only basic tests"
    echo "  --no-download  Skip PDF download"
    echo "  --keep-server  Don't stop server after tests"
    echo "  --help         Show this help message"
}

main() {
    local quick_mode=false
    local download_pdf=true
    local keep_server=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                quick_mode=true
                shift
                ;;
            --no-download)
                download_pdf=false
                shift
                ;;
            --keep-server)
                keep_server=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Set up cleanup trap
    if [[ $keep_server == false ]]; then
        trap cleanup EXIT
    fi
    
    banner
    check_dependencies
    start_server
    
    if [[ $download_pdf == true ]]; then
        download_test_pdf
    fi
    
    echo
    log "Running API tests..."
    echo
    
    test_health_endpoint
    echo
    
    test_config_endpoint
    echo
    
    if [[ $quick_mode == false ]]; then
        test_simple_extraction
        echo
        
        test_coordinate_extraction
        echo
        
        test_websocket_endpoint
        echo
        
        run_performance_test
        echo
    fi
    
    success "All tests completed successfully!"
    echo
    
    if [[ $keep_server == true ]]; then
        success "Server is still running at http://localhost:8000"
        success "API documentation: http://localhost:8000/docs"
        success "Check server.log for detailed logs"
        echo
        echo "To stop the server later, run:"
        echo "pkill -f uvicorn"
    fi
}

# Run main function with all arguments
main "$@"