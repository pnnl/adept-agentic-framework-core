#!/bin/bash
# Configure Podman to search Docker Hub for unqualified images
# This fixes the "Repo not found" error when pulling images like jupyter/scipy-notebook
#
# Usage: sudo ./configure-podman-registries.sh

set -e

REGISTRIES_CONF_CONTENT='# Podman registries configuration
# This file specifies which registries to search for images
# when using unqualified image names (e.g., "jupyter/scipy-notebook")
#
# Created: 2026-02-09 to fix Docker Hub image pulling for ADEPT Framework

# Unqualified image search registries
# Search docker.io (Docker Hub) first for compatibility with Docker Compose files
unqualified-search-registries = ["docker.io"]

# Docker Hub registry configuration
[[registry]]
location = "docker.io"
# No authentication required for public images
'

echo "================================================================"
echo "Configuring Podman Registries for Docker Hub"
echo "================================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo to configure rootful Podman."
    echo "Usage: sudo ./configure-podman-registries.sh"
    exit 1
fi

# Create root's containers config directory
echo "Creating /root/.config/containers directory..."
mkdir -p /root/.config/containers

# Write registries configuration for root
echo "Writing registries configuration to /root/.config/containers/registries.conf..."
cat > /root/.config/containers/registries.conf << 'EOF'
# Podman registries configuration
# This file specifies which registries to search for images
# when using unqualified image names (e.g., "jupyter/scipy-notebook")
#
# Created: 2026-02-09 to fix Docker Hub image pulling for ADEPT Framework

# Unqualified image search registries
# Search docker.io (Docker Hub) first for compatibility with Docker Compose files
unqualified-search-registries = ["docker.io"]

# Docker Hub registry configuration
[[registry]]
location = "docker.io"
# No authentication required for public images
EOF

echo ""
echo "✓ Configuration complete!"
echo ""
echo "Podman will now search docker.io (Docker Hub) for unqualified images."
echo "You can now run: sudo env \"PATH=\$PATH\" ./start-chapter-resources-podman.sh"
echo ""
