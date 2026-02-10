#!/bin/bash

# ==============================================================================
# ADEPT Tutorial Lifecycle Management Script (Podman Edition)
#
# This script provides a safe and interactive way to manage Podman
# resources for each tutorial chapter. It handles startup, graceful
# shutdown, and cleanup of containers and networks.
#
# CHAPTER 3 SPECIAL REQUIREMENTS:
# - REQUIRES ROOTFUL PODMAN for sandbox functionality
# - The sandbox_mcp_server uses nsjail which needs privileged mode
# - Run with: sudo -E ./start-chapter-resources-podman.sh
# ==============================================================================

# --- Configuration and Setup ---
# Color codes for better output
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m' # No Color

# Function to print a formatted header
print_header() {
    echo -e "${BLUE}=======================================================${NC}"
    echo -e "${BLUE}  ADEPT Chapter 3 Resource Manager (Podman - ROOTFUL) ${NC}"
    echo -e "${BLUE}  Chapter: ${PWD##*/} ${NC}"
    echo -e "${BLUE}=======================================================${NC}"
}

# Function to print rootful warning
print_rootful_warning() {
    echo -e "${YELLOW}=====================================================================${NC}"
    echo -e "${YELLOW}  WARNING: Chapter 3 requires ROOTFUL Podman for sandbox functionality${NC}"
    echo -e "${YELLOW}=====================================================================${NC}"
    echo ""
    echo -e "The ${BLUE}sandbox_mcp_server${NC} uses nsjail which requires elevated privileges."
    echo ""
    echo -e "${GREEN}To run this chapter with Podman, use:${NC}"
    echo -e "  ${YELLOW}sudo -E ./start-chapter-resources-podman.sh${NC}"
    echo ""
    echo -e "${GREEN}Alternative:${NC} If uncomfortable with rootful mode, use Docker instead:"
    echo -e "  ${YELLOW}./start-chapter-resources.sh${NC}"
    echo ""
    echo -e "${RED}SECURITY NOTE:${NC} Rootful Podman grants extended host privileges."
    echo -e "Only use in trusted development environments."
    echo ""
}

# --- Check Prerequisites ---
check_prerequisites() {
    echo "Checking prerequisites..."

    if ! command -v podman &> /dev/null; then
        echo -e "${RED}Error: Podman not found.${NC}"
        echo "Please install Podman: https://podman.io/getting-started/installation"
        exit 1
    fi

    if ! command -v podman-compose &> /dev/null; then
        echo -e "${RED}Error: podman-compose not found.${NC}"
        echo "Install with: pip install podman-compose"
        exit 1
    fi

    echo -e "${GREEN}✓ Podman $(podman --version | awk '{print $3}')${NC}"
    echo -e "${GREEN}✓ podman-compose $(podman-compose --version 2>&1 | head -n1)${NC}"
    echo ""
}

# --- Check for rootful mode ---
check_rootful_mode() {
    print_rootful_warning

    # Check if running as root or with sudo
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Error: This chapter requires rootful Podman mode.${NC}"
        echo -e "${RED}Please run with: ${YELLOW}sudo -E ./start-chapter-resources-podman.sh${NC}"
        echo ""
        exit 1
    fi

    # Confirm user wants to proceed
    read -p "$(echo -e ${YELLOW}"Continue with rootful Podman? (y/N) "${NC})" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted by user.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Running in rootful mode${NC}"
    echo ""
}

# --- Auto-detect Compose files ---
BASE_COMPOSE_FILE="docker-compose.yaml"
PODMAN_OVERLAY_FILE="docker-compose.podman.yaml"
OPENWEBUI_OVERLAY_FILE="docker-compose-openwebui.yaml"
COMPOSE_BIN="podman-compose"
COMPOSE_CMD="$COMPOSE_BIN"

if [ -f "$BASE_COMPOSE_FILE" ]; then
    COMPOSE_CMD+=" -f $BASE_COMPOSE_FILE"
else
    echo -e "${RED}Error: Base file '$BASE_COMPOSE_FILE' not found. Exiting.${NC}"
    exit 1
fi

# Always add Podman overlay if it exists
if [ -f "$PODMAN_OVERLAY_FILE" ]; then
    echo -e "${GREEN}Info: Podman overlay file '$PODMAN_OVERLAY_FILE' found and will be used.${NC}"
    COMPOSE_CMD+=" -f $PODMAN_OVERLAY_FILE"
else
    echo -e "${YELLOW}Warning: Podman overlay file '$PODMAN_OVERLAY_FILE' not found.${NC}"
    echo -e "${YELLOW}Some Podman-specific configurations may be missing.${NC}"
fi

# Add OpenWebUI overlay if present
if [ -f "$OPENWEBUI_OVERLAY_FILE" ]; then
    echo -e "${GREEN}Info: OpenWebUI overlay file '$OPENWEBUI_OVERLAY_FILE' found and will be used.${NC}"
    COMPOSE_CMD+=" -f $OPENWEBUI_OVERLAY_FILE"
fi

echo -e "${GREEN}Using command: ${YELLOW}${COMPOSE_CMD}${NC}"
echo ""

# --- Cleanup Function ---
# This function is called when the script exits or is interrupted.
cleanup() {
    echo ""
    echo -e "${YELLOW}-------------------------------------------------------${NC}"
    echo -e "${YELLOW}Caught exit signal. Shutting down and cleaning up...${NC}"
    echo -e "${YELLOW}-------------------------------------------------------${NC}"

    echo -e "Stopping and removing containers..."
    $COMPOSE_CMD down --remove-orphans
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to bring down containers. Please check Podman status.${NC}"
    else
        echo -e "${GREEN}Containers stopped and removed successfully.${NC}"
    fi

    # Ask before pruning networks
    read -p "$(echo -e ${YELLOW}"Do you want to prune unused Podman networks? (y/N) "${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Pruning unused networks..."
        podman network prune -f
        echo -e "${GREEN}Network prune complete.${NC}"
    fi

    # Ask before pruning images (this is a global, aggressive action)
    read -p "$(echo -e ${RED}"DANGER: Prune ALL unused Podman images? This affects your entire system. (y/N) "${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Pruning ALL unused images..."
        podman image prune -a -f
        echo -e "${GREEN}Image prune complete.${NC}"
    fi

    echo -e "${GREEN}Cleanup finished. Goodbye!${NC}"
    # Restore cursor
    tput cnorm
}

# --- Trap Exit Signal ---
# The 'trap' command sets up a command to be executed when the script
# receives a specific signal. Here, we catch EXIT, SIGINT (Ctrl+C), and SIGTERM.
trap cleanup EXIT SIGINT SIGTERM

# --- Main Script Logic ---
print_header
check_prerequisites
check_rootful_mode

# Check for existing containers for this project
echo "Checking for existing resources for this project..."
# Use 'podman-compose ps' which is project-aware
RUNNING_CONTAINERS=$($COMPOSE_CMD ps -q 2>/dev/null)

if [ -n "$RUNNING_CONTAINERS" ]; then
    echo -e "${YELLOW}Warning: Found existing containers for this chapter.${NC}"
    $COMPOSE_CMD ps
    read -p "$(echo -e ${YELLOW}"Do you want to tear down these existing resources before starting? (y/N) "${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Tearing down existing resources..."
        $COMPOSE_CMD down --remove-orphans
        echo -e "${GREEN}Teardown complete.${NC}"
    else
        echo -e "${RED}Aborted by user. Please manually manage existing resources before running this script again.${NC}"
        # Untrap the cleanup function before exiting to prevent it from running
        trap - EXIT SIGINT SIGTERM
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}Starting services with Podman (rootful). Press ${YELLOW}Ctrl+C${GREEN} to stop and clean up.${NC}"
echo -e "Building images if necessary and starting containers..."
echo ""

# Hide cursor for cleaner log output
tput civis

# Run podman-compose in the foreground. The script will wait here until
# the user presses Ctrl+C, which will be caught by our trap.
$COMPOSE_CMD up --build --remove-orphans

# The script will only reach here if 'podman-compose up' exits on its own,
# which is unlikely for server processes. The trap handles the main exit path.
# The cleanup function will be called automatically due to the EXIT trap.
