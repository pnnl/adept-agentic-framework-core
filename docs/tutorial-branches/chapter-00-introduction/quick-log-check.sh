#!/bin/bash
# Quick log check without sudo requirement (for viewing logs)
# Note: Container must be running or have been running

CONTAINERS=(
    "agentic_ollama_ch00"
    "agentic_mcp_server_ch00"
    "agentic_streamlit_app_ch00"
    "agentic_jupyterlab_ch00"
)

echo "=== Cross-Reference Service Logs ==="
echo ""

for container in "${CONTAINERS[@]}"; do
    echo "=== $container - Last 30 lines with errors highlighted ==="

    # Try both with and without sudo
    if command -v podman >/dev/null 2>&1; then
        podman logs --tail 30 "$container" 2>&1 | grep -iE "(error|exception|failed|fatal|critical|warning|traceback|started|listening|ready)" || echo "No significant logs found"
    else
        sudo podman logs --tail 30 "$container" 2>&1 | grep -iE "(error|exception|failed|fatal|critical|warning|traceback|started|listening|ready)" || echo "No significant logs found"
    fi

    echo ""
    echo "---"
    echo ""
done

echo "=== Service Status ==="
sudo podman ps -a --filter "name=agentic_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
