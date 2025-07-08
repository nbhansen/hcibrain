#!/bin/bash
# Quick API Health Check - No API key required

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo
echo -e "${BLUE}===================================${NC}"
echo -e "${BLUE} HCIBrain Quick Health Check${NC}"
echo -e "${BLUE}===================================${NC}"
echo

# Start server
log "Starting server..."
source venv/bin/activate
nohup uvicorn hci_extractor.web.app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
SERVER_PID=$!

# Wait for server
log "Waiting for server to start..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health &> /dev/null; then
        success "Server started (PID: $SERVER_PID)"
        break
    fi
    sleep 1
done

# Test endpoints
log "Testing health endpoint..."
curl -s http://localhost:8000/api/v1/health | (command -v jq >/dev/null && jq . || cat)
echo

log "Testing config endpoint..."
curl -s http://localhost:8000/api/v1/config | (command -v jq >/dev/null && jq . || cat)
echo

success "Health check complete!"

# Cleanup
log "Stopping server..."
kill $SERVER_PID
rm server.log 2>/dev/null || true

echo
success "Quick test completed successfully!"
echo "For full testing with PDF extraction, run: ./test_api.sh"