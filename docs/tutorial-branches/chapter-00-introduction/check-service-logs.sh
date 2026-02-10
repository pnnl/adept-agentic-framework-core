#!/bin/bash
# Cross-reference service logs for Chapter 0
# Monitors all services and highlights errors

BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}  ADEPT Chapter 0 - Service Log Monitor${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

# Check if running as root (for rootful Podman)
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script requires sudo to access rootful Podman containers${NC}"
    echo "Run with: sudo ./check-service-logs.sh"
    exit 1
fi

# Define service containers
CONTAINERS=(
    "ollama_ch00"
    "agentic_mcp_server_ch00"
    "agentic_streamlit_app_ch00"
    "agentic_jupyterlab_ch00"
)

# Function to get container status
get_container_status() {
    local container=$1
    if podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
        echo -e "${GREEN}RUNNING${NC}"
    elif podman ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
        echo -e "${RED}STOPPED${NC}"
    else
        echo -e "${YELLOW}NOT FOUND${NC}"
    fi
}

# Check all container statuses
echo -e "${YELLOW}=== Container Status ===${NC}"
for container in "${CONTAINERS[@]}"; do
    status=$(get_container_status "$container")
    printf "%-35s %b\n" "$container" "$status"
done
echo ""

# Function to get last N lines and filter errors
check_service_logs() {
    local container=$1
    local lines=${2:-50}

    echo -e "${BLUE}=== $container (last $lines lines) ===${NC}"

    if ! podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
        echo -e "${YELLOW}Container not running. Showing last logs before exit:${NC}"
        podman logs --tail $lines "$container" 2>&1 || echo -e "${RED}No logs available${NC}"
    else
        # Get logs and highlight errors
        podman logs --tail $lines "$container" 2>&1 | while IFS= read -r line; do
            if echo "$line" | grep -iE "(error|exception|failed|fatal|critical|traceback)" > /dev/null; then
                echo -e "${RED}$line${NC}"
            elif echo "$line" | grep -iE "(warning|warn)" > /dev/null; then
                echo -e "${YELLOW}$line${NC}"
            elif echo "$line" | grep -iE "(success|started|listening|ready)" > /dev/null; then
                echo -e "${GREEN}$line${NC}"
            else
                echo "$line"
            fi
        done
    fi
    echo ""
}

# Parse command line arguments
MODE=${1:-"summary"}
LINES=${2:-50}

case "$MODE" in
    summary|s)
        echo -e "${YELLOW}=== Log Summary Mode (errors and warnings only) ===${NC}"
        echo ""
        for container in "${CONTAINERS[@]}"; do
            echo -e "${BLUE}=== $container - Errors/Warnings ===${NC}"
            if podman ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
                podman logs --tail 100 "$container" 2>&1 | grep -iE "(error|exception|failed|fatal|critical|warning|warn|traceback)" | tail -20 || echo -e "${GREEN}No errors or warnings found${NC}"
            else
                echo -e "${YELLOW}Container not found${NC}"
            fi
            echo ""
        done
        ;;

    full|f)
        echo -e "${YELLOW}=== Full Log Mode (last $LINES lines per service) ===${NC}"
        echo ""
        for container in "${CONTAINERS[@]}"; do
            check_service_logs "$container" "$LINES"
        done
        ;;

    follow|tail|t)
        echo -e "${YELLOW}=== Follow Mode (live tail all services) ===${NC}"
        echo "Press Ctrl+C to stop"
        echo ""
        # Follow all logs with service labels
        for container in "${CONTAINERS[@]}"; do
            if podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
                podman logs -f "$container" 2>&1 | sed "s/^/[$container] /" &
            fi
        done
        wait
        ;;

    health|h)
        echo -e "${YELLOW}=== Health Check Mode ===${NC}"
        echo ""

        # Ollama
        echo -e "${BLUE}Ollama (port 11434):${NC}"
        curl -f http://localhost:11434/api/tags 2>/dev/null && echo -e "${GREEN}✓ Responding${NC}" || echo -e "${RED}✗ Not responding${NC}"
        echo ""

        # MCP Server
        echo -e "${BLUE}MCP Server (port 8080):${NC}"
        curl -f http://localhost:8080/health 2>/dev/null && echo -e "${GREEN}✓ Responding${NC}" || echo -e "${RED}✗ Not responding${NC}"
        echo ""

        # Streamlit
        echo -e "${BLUE}Streamlit (port 8501, SSL):${NC}"
        curl -fk https://localhost:8501 2>/dev/null && echo -e "${GREEN}✓ Responding${NC}" || echo -e "${RED}✗ Not responding${NC}"
        echo ""

        # JupyterLab
        echo -e "${BLUE}JupyterLab (port 8888):${NC}"
        curl -f http://localhost:8888 2>/dev/null && echo -e "${GREEN}✓ Responding${NC}" || echo -e "${RED}✗ Not responding${NC}"
        echo ""
        ;;

    *)
        echo "Usage: $0 [mode] [lines]"
        echo ""
        echo "Modes:"
        echo "  summary|s     Show only errors and warnings (default)"
        echo "  full|f        Show last N lines from each service (default 50)"
        echo "  follow|tail|t Follow logs in real-time"
        echo "  health|h      Check service health endpoints"
        echo ""
        echo "Examples:"
        echo "  sudo ./check-service-logs.sh           # Summary of errors"
        echo "  sudo ./check-service-logs.sh full 100  # Last 100 lines each"
        echo "  sudo ./check-service-logs.sh follow    # Live tail"
        echo "  sudo ./check-service-logs.sh health    # Check endpoints"
        exit 0
        ;;
esac

echo -e "${BLUE}=======================================================${NC}"
echo -e "${GREEN}Log check complete${NC}"
echo -e "${BLUE}=======================================================${NC}"
