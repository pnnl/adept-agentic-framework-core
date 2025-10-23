#!/bin/bash

# NOTE: This script was originally configured for internal PNNL GitLab/Tanuki registry.
# It has been updated to use GitHub Container Registry (ghcr.io).
# You will need to authenticate with GitHub (gh auth login) before using this script.
# See: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry


# Define the target registry
REGISTRY="ghcr.io/pnnl/adept-agentic-framework-core"

# --- Main script execution ---

# Check if an image name was provided as an argument
if [ -z "$1" ]; then
    echo "Usage: $0 <image_name>"
    echo "Example: $0 agentic_framework-hpc_mcp_server"
    exit 1
fi

IMAGE_NAME="$1"
SOURCE_IMAGE="${IMAGE_NAME}:latest"
TARGET_IMAGE="${REGISTRY}/${IMAGE_NAME}:latest"

# First, log in to the Docker registry
echo "--- Logging in to ${REGISTRY%%/*} ---"
docker login "${REGISTRY%%/*}"
if [ $? -ne 0 ]; then
    echo "Error: Docker login failed. Please check your credentials."
    exit 1
fi

echo "--- Tagging ${SOURCE_IMAGE} as ${TARGET_IMAGE} ---"
docker tag "${SOURCE_IMAGE}" "${TARGET_IMAGE}"
if [ $? -ne 0 ]; then
    echo "Error: Failed to tag image ${SOURCE_IMAGE}"
    exit 1
fi

echo "--- Pushing ${TARGET_IMAGE} ---"
docker push "${TARGET_IMAGE}"
if [ $? -ne 0 ]; then
    echo "Error: Failed to push image ${TARGET_IMAGE}"
    exit 1
fi

echo "--- Successfully pushed ${IMAGE_NAME} to ${REGISTRY} ---"

## List of local images (as of 2025-07-07):
# (base) rigo160@WE47740 agentic_framework % docker image list
# REPOSITORY                                  TAG                IMAGE ID       CREATED         SIZE
# agentic_framework-hpc_mcp_server            latest             aa5ceda20bbf   4 days ago      26.1GB
# agentic_framework-mcp_server                latest             34871ad0c2bb   4 days ago      9.18GB
# agentic_framework-streamlit_app             latest             ac1c069bad10   4 days ago      3.68GB
# agentic_framework-sandbox_mcp_server        latest             fa7984e18432   4 days ago      3.01GB

## To push an image to the registry, use the following command:
# Example: scripts/docker-push_to_gitlab_tanuki.sh agentic_framework-hpc_mcp_server

