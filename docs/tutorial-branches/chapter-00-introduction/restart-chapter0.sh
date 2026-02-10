#!/bin/bash
echo "Stopping existing containers..."
sudo env "PATH=$PATH" podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml down

echo ""
echo "Starting with new configuration..."
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
