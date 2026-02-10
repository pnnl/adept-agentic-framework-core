#!/bin/bash
# Bootstrap script for Podman Python environment
# Creates a virtual environment with Podman Python libraries

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv-podman"

echo "=========================================="
echo "Podman Python Environment Bootstrap"
echo "=========================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION"

# Check if Podman is installed
if ! command -v podman &> /dev/null; then
    echo "Error: podman not found. Please install Podman 4.0+"
    exit 1
fi

PODMAN_VERSION=$(podman --version | awk '{print $3}')
echo "✓ Found Podman $PODMAN_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created at: $VENV_DIR"
else
    echo ""
    echo "✓ Virtual environment already exists at: $VENV_DIR"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip wheel setuptools

# Install Podman Python libraries
echo ""
echo "Installing Podman Python libraries..."
pip install \
    podman \
    podman-compose \
    python-dotenv \
    pyyaml

# Install additional useful libraries for container management
echo ""
echo "Installing additional libraries..."
pip install \
    requests \
    rich

echo ""
echo "=========================================="
echo "Installation Summary"
echo "=========================================="
echo ""
pip list | grep -E "podman|dotenv|yaml|requests|rich"

echo ""
echo "=========================================="
echo "Bootstrap Complete!"
echo "=========================================="
echo ""
echo "To activate this environment in the future, run:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To deactivate when done:"
echo "  deactivate"
echo ""
echo "Podman Python API documentation:"
echo "  https://podman-py.readthedocs.io/"
echo ""

# Create activation helper script
cat > "$SCRIPT_DIR/activate-podman-env.sh" << 'ACTIVATE_EOF'
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
ACTIVATE_EOF

chmod +x "$SCRIPT_DIR/activate-podman-env.sh"

echo "✓ Created activation helper: ./activate-podman-env.sh"
echo ""
