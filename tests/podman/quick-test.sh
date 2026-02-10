#!/bin/bash
# Quick smoke test for Podman deployment
# Fast validation without comprehensive checks

GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

CHAPTER="${1:-0}"

echo "Quick smoke test for Chapter $CHAPTER..."
echo ""

# Check containers
echo -n "Checking containers... "
case "$CHAPTER" in
    0)
        if sudo podman ps | grep -qE "(ollama_ch00|agentic_mcp_server_ch00|agentic_streamlit_app_ch00|agentic_jupyterlab_ch00)"; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗ Not all containers running${NC}"
            exit 1
        fi
        ;;
    1)
        if sudo podman ps | grep -qE "(agentic_mcp_server|agentic_streamlit_app)"; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗ Not all containers running${NC}"
            exit 1
        fi
        ;;
esac

# Check for critical errors
echo -n "Checking for critical errors... "
ERROR_COUNT=$(sudo podman ps -a --format "{{.Names}}" | grep "agentic" | xargs -I {} sudo podman logs --tail 20 {} 2>&1 | grep -ciE "ModuleNotFoundError|RuntimeError.*failed|critical|fatal" || echo "0")

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Found $ERROR_COUNT critical errors${NC}"
    exit 1
fi

# Quick endpoint check
case "$CHAPTER" in
    0)
        echo -n "Checking MCP server... "
        if curl -sf --max-time 3 http://localhost:8080/health > /dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
            exit 1
        fi
        ;;
esac

echo ""
echo -e "${GREEN}✓ Smoke test passed${NC}"
