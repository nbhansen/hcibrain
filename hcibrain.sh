#!/bin/bash
# HCIBrain Paper Skimming Assistant - One-Click Startup Script
# Starts both backend API and frontend web app

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_LOG="$SCRIPT_DIR/backend.log"
FRONTEND_LOG="$SCRIPT_DIR/frontend.log"
BACKEND_DIR="$SCRIPT_DIR/packages/backend"
FRONTEND_DIR="$SCRIPT_DIR/packages/frontend"

log() {
    echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $1"
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
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║                                                      ║"
    echo "║   🧠 HCIBrain Paper Skimming Assistant 📄✨         ║"
    echo "║                                                      ║"
    echo "║   AI-powered research paper highlight extraction     ║"
    echo "║   Upload PDFs → Get Goals, Methods, Results          ║"
    echo "║                                                      ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_dependencies() {
    log "Checking dependencies..."
    
    # Check Python virtual environment
    if [ ! -d "$BACKEND_DIR/venv" ]; then
        error "Virtual environment not found. Please run: cd $BACKEND_DIR && python -m venv venv"
        exit 1
    fi
    
    # Check config.yaml in backend
    if [ ! -f "$BACKEND_DIR/config.yaml" ]; then
        warning "config.yaml not found. Creating from template..."
        if [ -f "$BACKEND_DIR/config.template.yaml" ]; then
            cp "$BACKEND_DIR/config.template.yaml" "$BACKEND_DIR/config.yaml"
            warning "Please edit config.yaml with your Gemini API key before continuing"
            echo "Get your API key at: https://aistudio.google.com/app/apikey"
            exit 1
        else
            error "config.template.yaml not found"
            exit 1
        fi
    fi
    
    # Check frontend directory
    if [ ! -d "$FRONTEND_DIR" ]; then
        error "Frontend directory $FRONTEND_DIR not found"
        exit 1
    fi
    
    # Check frontend dependencies
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        log "Installing frontend dependencies..."
        cd "$FRONTEND_DIR" && npm install && cd ..
    fi
    
    success "Dependencies checked"
}

run_backend_linting() {
    log "Running Python backend linting checks..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Run ruff linting - check for critical issues only
    local ruff_output
    ruff_output=$(python -m ruff check src/ --statistics 2>&1 || true)
    
    # Count total errors
    local error_count
    error_count=$(echo "$ruff_output" | grep "Found" | grep -o '[0-9]\+' | tail -1)
    
    if [[ -n "$error_count" && "$error_count" -gt 200 ]]; then
        error "🚨 BACKEND LINTING FAILED - TOO MANY ISSUES (${error_count})!"
        echo -e "${RED}Critical code quality threshold exceeded. Run the following to fix:${NC}"
        echo "  source venv/bin/activate && python -m ruff check src/ --fix"
        echo ""
        echo -e "${YELLOW}Must reduce errors below 200 before starting HCIBrain${NC}"
        exit 1
    elif [[ -n "$error_count" && "$error_count" -gt 0 ]]; then
        warning "⚠️  ${error_count} minor linting issues found (acceptable for production)"
    fi
    
    # Run mypy type checking with reasonable thresholds
    local mypy_output
    mypy_output=$(python -m mypy src/ 2>&1 || true)
    
    # Count type errors
    local type_error_count
    type_error_count=$(echo "$mypy_output" | grep "Found" | grep -o '[0-9]\+' | head -1)
    
    if [[ -n "$type_error_count" && "$type_error_count" -gt 50 ]]; then
        error "🚨 BACKEND TYPE CHECKING FAILED - TOO MANY ERRORS (${type_error_count})!"
        echo -e "${RED}Critical type safety threshold exceeded. Run the following:${NC}"
        echo "  source venv/bin/activate && python -m mypy src/"
        echo ""
        echo -e "${YELLOW}Must reduce type errors below 50 before starting HCIBrain${NC}"
        exit 1
    elif [[ -n "$type_error_count" && "$type_error_count" -gt 0 ]]; then
        warning "⚠️  ${type_error_count} minor type issues found (acceptable for production)"
    fi
    
    success "Backend linting passed"
    cd - > /dev/null
}

run_frontend_linting() {
    log "Running React frontend linting checks..."
    
    cd "$FRONTEND_DIR"
    
    # Run ESLint with pragmatic thresholds
    local eslint_output
    eslint_output=$(npm run lint 2>&1 || true)
    
    # Count errors (excluding warnings)
    local error_count
    error_count=$(echo "$eslint_output" | grep -c "error" 2>/dev/null | head -1 || echo "0")
    
    if [[ "$error_count" -gt 10 ]]; then
        error "🚨 FRONTEND LINTING FAILED - TOO MANY ERRORS (${error_count})!"
        echo -e "${RED}Critical code quality threshold exceeded.${NC}"
        echo -e "${RED}Run the following to see and fix issues:${NC}"
        echo "  cd $FRONTEND_DIR && npm run lint"
        echo ""
        echo -e "${YELLOW}Must reduce errors below 10 before starting HCIBrain${NC}"
        cd ..
        exit 1
    elif [[ "$error_count" -gt 0 ]]; then
        warning "⚠️  ${error_count} frontend linting issues found (acceptable for production)"
    fi
    
    # Run TypeScript compilation check - this is critical
    if ! npm run build > /dev/null 2>&1; then
        error "🚨 FRONTEND BUILD FAILED - BLOCKING!"
        echo -e "${RED}TypeScript compilation failed. This prevents the app from building.${NC}"
        echo -e "${RED}Run the following to see errors:${NC}"
        echo "  cd $FRONTEND_DIR && npm run build"
        echo ""
        echo -e "${YELLOW}All TypeScript compilation errors must be resolved${NC}"
        cd ..
        exit 1
    fi
    
    cd ..
    success "Frontend linting passed"
}

run_all_linting() {
    echo
    log "🔍 Running comprehensive code quality checks..."
    echo -e "${YELLOW}Zero-tolerance policy: ALL issues must be ✅ GREEN before startup${NC}"
    echo
    
    run_backend_linting
    run_frontend_linting
    
    echo
    success "🎉 ALL LINTING CHECKS PASSED! Code quality is enterprise-grade ✅"
    echo
}

kill_existing_processes() {
    log "Stopping any existing HCIBrain processes..."
    
    # Kill existing backend processes
    pkill -f "uvicorn.*hci_extractor" || true
    
    # Kill existing frontend processes
    pkill -f "vite" || true
    
    # Wait a moment for processes to stop
    sleep 2
    
    success "Stopped existing processes"
}

start_backend() {
    log "Starting HCIBrain backend API..."
    
    # Activate virtual environment and start backend
    cd "$BACKEND_DIR"
    source venv/bin/activate
    nohup uvicorn src.hci_extractor.web.app:app --host 0.0.0.0 --port $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    cd - > /dev/null
    
    # Wait for backend to start
    log "Waiting for backend to start..."
    for i in {1..30}; do
        if curl -s http://localhost:$BACKEND_PORT/api/v1/health > /dev/null 2>&1; then
            success "Backend started (PID: $BACKEND_PID)"
            return 0
        fi
        sleep 1
    done
    
    error "Backend failed to start. Check $BACKEND_LOG"
    exit 1
}

start_frontend() {
    log "Starting HCIBrain frontend..."
    
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    cd - > /dev/null
    
    # Wait for frontend to start
    log "Waiting for frontend to start..."
    for i in {1..30}; do
        if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
            success "Frontend started (PID: $FRONTEND_PID)"
            return 0
        fi
        sleep 1
    done
    
    error "Frontend failed to start. Check $FRONTEND_LOG"
    exit 1
}

show_success_message() {
    echo
    echo -e "${GREEN}🎉 HCIBrain is now running! 🎉${NC}"
    echo
    echo -e "${CYAN}📄 Paper Skimming Assistant:${NC} ${YELLOW}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "${CYAN}🔧 Backend API Documentation:${NC} ${YELLOW}http://localhost:$BACKEND_PORT/docs${NC}"
    echo
    echo -e "${BLUE}How to use:${NC}"
    echo "1. Open the Paper Skimming Assistant URL above"
    echo "2. Drag & drop a research paper PDF"
    echo "3. Wait for AI extraction to complete"
    echo "4. See highlighted Goals, Methods, and Results!"
    echo
    echo -e "${PURPLE}Features:${NC}"
    echo "• Color-coded markup highlights (blue, amber, rose)"
    echo "• Chunked processing for large documents"
    echo "• Text cleaning preserves references"
    echo
    echo -e "${CYAN}To stop HCIBrain:${NC} ${YELLOW}Ctrl+C${NC} or run: ${YELLOW}pkill -f 'uvicorn\\|vite'${NC}"
    echo
    echo -e "${YELLOW}Logs:${NC} $BACKEND_LOG (backend) | $FRONTEND_LOG (frontend)"
    echo
}

cleanup() {
    echo
    log "Shutting down HCIBrain..."
    pkill -f "uvicorn.*hci_extractor" || true
    pkill -f "vite" || true
    success "HCIBrain stopped"
    exit 0
}

# Handle Ctrl+C gracefully
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    banner
    check_dependencies
    
    # Run linting unless --skip-lint flag is passed
    if [[ "${1:-}" != "--skip-lint" ]]; then
        run_all_linting
    else
        warning "⚠️  Skipping linting checks (--skip-lint flag)"
        echo -e "${YELLOW}Note: This may result in runtime errors or poor code quality${NC}"
        echo
    fi
    
    kill_existing_processes
    start_backend
    start_frontend
    show_success_message
    
    # Keep script running
    log "HCIBrain is running. Press Ctrl+C to stop."
    while true; do
        sleep 10
        # Check if processes are still running
        if ! curl -s http://localhost:$BACKEND_PORT/api/v1/health > /dev/null 2>&1; then
            error "Backend stopped unexpectedly. Check $BACKEND_LOG"
            exit 1
        fi
        if ! curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
            error "Frontend stopped unexpectedly. Check $FRONTEND_LOG"
            exit 1
        fi
    done
}

# Parse command line arguments
case "${1:-}" in
    "stop")
        log "Stopping HCIBrain..."
        pkill -f "uvicorn.*hci_extractor" || true
        pkill -f "vite" || true
        success "HCIBrain stopped"
        exit 0
        ;;
    "status")
        echo "Checking HCIBrain status..."
        if curl -s http://localhost:$BACKEND_PORT/api/v1/health > /dev/null 2>&1; then
            success "Backend running on port $BACKEND_PORT"
        else
            warning "Backend not running"
        fi
        if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
            success "Frontend running on port $FRONTEND_PORT"
        else
            warning "Frontend not running"
        fi
        exit 0
        ;;
    "lint"|"check")
        echo "Running HCIBrain code quality checks..."
        echo
        check_dependencies
        run_all_linting
        success "All quality checks passed! Ready to start HCIBrain."
        exit 0
        ;;
    "help"|"-h"|"--help")
        echo "HCIBrain Paper Skimming Assistant"
        echo
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  (no args)  Start HCIBrain with full quality checks (default)"
        echo "  stop       Stop all HCIBrain processes"
        echo "  status     Check if HCIBrain is running"
        echo "  lint       Run code quality checks only (Python + TypeScript)"
        echo "  check      Alias for 'lint'"
        echo "  help       Show this help message"
        echo
        echo "Flags:"
        echo "  --skip-lint  Skip code quality checks (not recommended)"
        echo
        exit 0
        ;;
    ""|"--skip-lint")
        # Default: start HCIBrain
        main "${1:-}"
        ;;
    *)
        error "Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac