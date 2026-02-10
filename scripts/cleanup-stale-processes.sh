#!/bin/bash
# Cleanup script for stale Podman processes and containers

BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}  Cleaning up stale Podman processes and containers${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script requires sudo${NC}"
    echo "Run with: sudo ./cleanup-stale-processes.sh"
    exit 1
fi

# Step 1: Stop and remove all containers
echo -e "${YELLOW}Step 1: Stopping all running containers...${NC}"
RUNNING=$(podman ps -q)
if [ -n "$RUNNING" ]; then
    echo "Found running containers:"
    podman ps --format "table {{.Names}}\t{{.Status}}"
    echo ""
    podman stop $(podman ps -q)
    echo -e "${GREEN}✓ Containers stopped${NC}"
else
    echo "No running containers found"
fi
echo ""

# Step 2: Remove all containers
echo -e "${YELLOW}Step 2: Removing all containers...${NC}"
ALL_CONTAINERS=$(podman ps -aq)
if [ -n "$ALL_CONTAINERS" ]; then
    echo "Found containers to remove:"
    podman ps -a --format "table {{.Names}}\t{{.Status}}"
    echo ""
    podman rm -f $(podman ps -aq)
    echo -e "${GREEN}✓ Containers removed${NC}"
else
    echo "No containers to remove"
fi
echo ""

# Step 3: Kill stale sudo processes
echo -e "${YELLOW}Step 3: Killing stale sudo/podman-compose processes...${NC}"
STALE_PIDS=$(ps aux | grep -E "sudo.*start-chapter-resources-podman|podman-compose.*up" | grep -v grep | awk '{print $2}')
if [ -n "$STALE_PIDS" ]; then
    echo "Found stale processes:"
    ps aux | grep -E "sudo.*start-chapter-resources-podman|podman-compose.*up" | grep -v grep | awk '{print $2, $11, $12, $13, $14, $15}'
    echo ""
    for pid in $STALE_PIDS; do
        echo "Killing PID $pid..."
        kill -9 $pid 2>/dev/null || true
    done
    echo -e "${GREEN}✓ Stale processes killed${NC}"
else
    echo "No stale processes found"
fi
echo ""

# Step 4: Kill all bash processes related to start-chapter scripts (any status)
echo -e "${YELLOW}Step 4: Killing bash processes running start-chapter scripts...${NC}"
BASH_PIDS=$(ps aux | grep -E "/bin/bash.*start-chapter-resources-podman\.sh" | grep -v grep | awk '{print $2}')
if [ -n "$BASH_PIDS" ]; then
    echo "Found bash processes:"
    ps aux | grep -E "/bin/bash.*start-chapter-resources-podman\.sh" | grep -v grep
    echo ""
    for pid in $BASH_PIDS; do
        echo "Killing PID $pid..."
        kill -9 $pid 2>/dev/null || true
    done
    echo -e "${GREEN}✓ Bash processes killed${NC}"
else
    echo "No bash processes found"
fi
echo ""

# Step 5: Verify cleanup
echo -e "${YELLOW}Step 5: Verifying cleanup...${NC}"
REMAINING=$(podman ps -aq | wc -l)
STALE_REMAINING=$(ps aux | grep -E "start-chapter-resources-podman|podman-compose.*up" | grep -v grep | wc -l)

echo "Containers remaining: $REMAINING"
echo "Stale processes remaining: $STALE_REMAINING"
echo ""

if [ "$REMAINING" -eq 0 ] && [ "$STALE_REMAINING" -eq 0 ]; then
    echo -e "${GREEN}✓ Cleanup successful!${NC}"
else
    echo -e "${YELLOW}⚠ Some processes/containers may remain${NC}"
    if [ "$REMAINING" -gt 0 ]; then
        echo "Remaining containers:"
        podman ps -a
    fi
    if [ "$STALE_REMAINING" -gt 0 ]; then
        echo "Remaining processes:"
        ps aux | grep -E "start-chapter-resources-podman|podman-compose.*up" | grep -v grep
    fi
fi

echo ""
echo -e "${BLUE}================================================================${NC}"
echo -e "${GREEN}Cleanup complete!${NC}"
echo -e "${BLUE}================================================================${NC}"
