#!/bin/bash
# Verify all Chapter 0 services are healthy

BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}  ADEPT Chapter 0 - Service Health Check${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

# Check container status
echo -e "${YELLOW}=== Container Status ===${NC}"
sudo podman ps --filter "name=ch00" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Function to check HTTP endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local use_ssl=$3

    echo -n "Checking $name... "

    if [ "$use_ssl" = "true" ]; then
        if curl -fsk --max-time 5 "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ OK${NC}"
            return 0
        else
            echo -e "${RED}✗ FAILED${NC}"
            return 1
        fi
    else
        if curl -fs --max-time 5 "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ OK${NC}"
            return 0
        else
            echo -e "${RED}✗ FAILED${NC}"
            return 1
        fi
    fi
}

# Check all services
echo -e "${YELLOW}=== Service Health Checks ===${NC}"

check_endpoint "Ollama API (11434)" "http://localhost:11434/api/tags" false
check_endpoint "MCP Server (8080)" "http://localhost:8080/health" false
check_endpoint "Streamlit SSL (8501)" "https://localhost:8501" true
check_endpoint "JupyterLab (8888)" "http://localhost:8888" false

echo ""
echo -e "${YELLOW}=== MCP Server Database Check ===${NC}"
if sudo podman exec agentic_mcp_server_ch00 ls -la /app/data/agentic_framework.db 2>/dev/null; then
    echo -e "${GREEN}✓ SQLite database exists${NC}"
else
    echo -e "${YELLOW}⚠ SQLite database not yet created (will be created on first use)${NC}"
fi

echo ""
echo -e "${YELLOW}=== ChromaDB Check ===${NC}"
if sudo podman exec agentic_mcp_server_ch00 ls -la /app/data/persistent_chroma_db/ 2>/dev/null | head -5; then
    echo -e "${GREEN}✓ ChromaDB directory accessible${NC}"
else
    echo -e "${RED}✗ ChromaDB directory not accessible${NC}"
fi

echo ""
echo -e "${BLUE}=======================================================${NC}"
echo -e "${GREEN}Health check complete!${NC}"
echo ""
echo "Access services at:"
echo "  - Streamlit:  https://localhost:8501 (or your SSH forwarded port)"
echo "  - JupyterLab: http://localhost:8888"
echo "  - Ollama:     http://localhost:11434"
echo "  - MCP Server: http://localhost:8080"
echo -e "${BLUE}=======================================================${NC}"
