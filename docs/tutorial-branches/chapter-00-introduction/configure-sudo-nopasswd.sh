#!/bin/bash
# Script to configure passwordless sudo for Podman operations
# Run with: sudo ./configure-sudo-nopasswd.sh

if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

USERNAME="${SUDO_USER:-$(whoami)}"

echo "Configuring passwordless sudo for user: $USERNAME"
echo ""

# Create sudoers.d file for this user
SUDOERS_FILE="/etc/sudoers.d/podman-${USERNAME}"

cat > "$SUDOERS_FILE" << EOF
# Passwordless sudo for Podman operations
# Created: $(date)
# User: $USERNAME

# Option 1: Allow ALL sudo commands without password (LESS SECURE)
# $USERNAME ALL=(ALL) NOPASSWD: ALL

# Option 2: Allow only specific Podman commands without password (MORE SECURE - RECOMMENDED)
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/podman
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/podman-compose
$USERNAME ALL=(ALL) NOPASSWD: /usr/local/bin/podman-compose
$USERNAME ALL=(ALL) NOPASSWD: /home/$USERNAME/.local/bin/podman-compose
EOF

# Set correct permissions (required for sudoers.d files)
chmod 0440 "$SUDOERS_FILE"

# Validate sudoers syntax
if visudo -c -f "$SUDOERS_FILE" > /dev/null 2>&1; then
    echo "✓ Sudoers configuration created successfully: $SUDOERS_FILE"
    echo ""
    echo "You can now run podman commands without sudo password:"
    echo "  sudo podman ps"
    echo "  sudo podman-compose up -d"
    echo "  sudo env \"PATH=\$PATH\" ./start-chapter-resources-podman.sh"
    echo ""
    echo "To test, open a NEW terminal and run: sudo podman ps"
else
    echo "✗ Error: Invalid sudoers syntax, removing file"
    rm -f "$SUDOERS_FILE"
    exit 1
fi

# Show current file contents
echo "Current configuration:"
cat "$SUDOERS_FILE"
