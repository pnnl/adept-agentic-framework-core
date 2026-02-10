#!/bin/bash
# Quick activation script for Podman Python environment

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv-podman"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Run ./bootstrap-podman-env.sh first"
    exit 1
fi

echo "Activating Podman Python environment..."
source "$VENV_DIR/bin/activate"
echo "✓ Environment activated"
echo ""
echo "Python: $(which python)"
echo "Podman: $(which podman)"
echo ""
