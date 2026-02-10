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

# Configure Podman storage for NFS compatibility
echo ""
echo "Configuring Podman storage..."
mkdir -p ~/.config/containers
mkdir -p /tmp/podman-storage-$USER
mkdir -p /tmp/podman-run-$USER

cat > ~/.config/containers/storage.conf << 'STORAGE_EOF'
[storage]
driver = "vfs"
graphroot = "/tmp/podman-storage-$USER"
runroot = "/tmp/podman-run-$USER"

[storage.options]
# VFS driver with local temporary storage
# Avoids NFS permission and xattr issues
# Works on network filesystems
STORAGE_EOF

# Expand USER variable
sed -i "s/\$USER/$USER/g" ~/.config/containers/storage.conf 2>/dev/null || true

echo "✓ Podman storage configured at /tmp/podman-storage-$USER"
echo "  Driver: vfs (NFS-compatible)"

# Check for subuid/subgid configuration
echo ""
echo "Checking rootless configuration..."
if ! grep -q "^$USER:" /etc/subuid 2>/dev/null; then
    echo "⚠️  Warning: No subuid ranges found for user $USER"
    echo "   This may cause issues with some container images"
    echo ""
    echo "   To fix (requires sudo/admin):"
    echo "   sudo usermod --add-subuids 100000-165535 $USER"
    echo "   sudo usermod --add-subgids 100000-165535 $USER"
    echo "   podman system migrate"
    echo ""
    echo "   Alternative: Use rootful Podman (run scripts with sudo -E)"
    echo ""
else
    echo "✓ Subuid/subgid ranges configured"
fi

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
