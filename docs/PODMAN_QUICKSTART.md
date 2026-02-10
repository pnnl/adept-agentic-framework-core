# Podman Quick Start Guide

Complete guide to get Podman up and running for ADEPT Framework, including solutions for common HPC/NFS environment issues.

> **⚠️ CRITICAL: Network/LDAP User Limitation**
>
> **If you have a high UID (>100000), you MUST use rootful Podman (sudo) for ALL chapters.**
>
> Rootless Podman does not work with network/LDAP users due to newuidmap limitations. This is a known unfixable issue.
>
> **Check your UID:**
> ```bash
> id -u  # If > 100000, use rootful mode (sudo) for all steps below
> ```
>
> **All launch commands below must use:** `sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh`

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Bootstrap Process](#bootstrap-process)
4. [Launching Chapters](#launching-chapters)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Operating System:** Linux (Rocky, RHEL, Ubuntu, Fedora, etc.)
- **Podman:** 4.0+ (preferably 5.0+)
- **Python:** 3.9+
- **Sudo access:** Required for subuid/subgid configuration (one-time)

---

## Installation

### Step 1: Install Podman

**Rocky Linux / RHEL:**
```bash
sudo dnf install -y podman
```

**Ubuntu / Debian:**
```bash
sudo apt-get update
sudo apt-get install -y podman
```

**Fedora:**
```bash
sudo dnf install -y podman
```

**Verify installation:**
```bash
podman --version
# Should show: podman version 5.x.x or 4.x.x
```

---

## Bootstrap Process

The `bootstrap-podman-env.sh` script automates the complete setup process.

### Step 2: Run Bootstrap Script

From the project root directory:

```bash
./bootstrap-podman-env.sh
```

**What the bootstrap script does:**

1. **Validates prerequisites**
   - Checks Python 3.9+
   - Checks Podman 4.0+

2. **Configures Podman storage**
   - Creates `/tmp/podman-storage-$USER` directory (local, non-NFS)
   - Sets VFS storage driver (NFS-compatible)
   - Updates `~/.config/containers/storage.conf`

3. **Checks rootless configuration**
   - Verifies subuid/subgid ranges
   - Warns if not configured (with fix instructions)

4. **Creates Python virtual environment**
   - Location: `.venv-podman`
   - Installs: podman, podman-compose, python-dotenv, pyyaml, requests, rich

5. **Generates helper scripts**
   - Creates `activate-podman-env.sh` for quick activation

**Expected Output:**
```
==========================================
Podman Python Environment Bootstrap
==========================================

✓ Found Python 3.9.x
✓ Found Podman 5.6.0

Configuring Podman storage...
✓ Podman storage configured at /tmp/podman-storage-rigo160
  Driver: vfs (NFS-compatible)

Checking rootless configuration...
⚠️  Warning: No subuid ranges found for user rigo160
   (Instructions provided)

Creating Python virtual environment...
✓ Virtual environment created

...

==========================================
Bootstrap Complete!
==========================================
```

### Step 3: Configure Subuid/Subgid (If Needed)

If the bootstrap warned about missing subuid/subgid ranges, configure them:

```bash
# Add subuid and subgid ranges (requires sudo)
sudo usermod --add-subuids 100000-165535 $USER
sudo usermod --add-subgids 100000-165535 $USER

# Verify configuration
grep $USER /etc/subuid /etc/subgid

# Migrate Podman to use new ranges
podman system migrate
```

**Expected output after migration:**
```
/etc/subuid:rigo160:100000:65536
/etc/subgid:rigo160:100000:65536
```

### Step 4: Test Podman

```bash
# Activate the environment
source .venv-podman/bin/activate

# Test basic functionality
podman run --rm hello-world
```

**Expected output:**
```
!... Hello Podman World ...!
[ASCII art]
```

If this succeeds, Podman is fully configured and ready!

---

## Launching Chapters

### Activate Environment (Required Each Session)

```bash
# From project root
source .venv-podman/bin/activate

# OR use the helper script
source ./activate-podman-env.sh
```

**Verify activation:**
```bash
which podman-compose
# Should show: /path/to/.venv-podman/bin/podman-compose
```

### Launch Commands

**For Standard Users (UID < 100000):**
If rootless Podman works for you, simply run the scripts directly:
```bash
cd docs/tutorial-branches/chapter-XX-name
./start-chapter-resources-podman.sh
```

**For Network/LDAP Users (UID > 100000) - REQUIRED:**
All chapters must use rootful Podman with PATH preservation:
```bash
cd docs/tutorial-branches/chapter-XX-name
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

### Launch Chapter 0 (Introduction)

**Interactive mode (foreground):**
```bash
cd docs/tutorial-branches/chapter-00-introduction

# Standard users:
./start-chapter-resources-podman.sh

# Network users (high UID):
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh

# Press Ctrl+C to stop
```

**Background mode with logging:**
```bash
cd docs/tutorial-branches/chapter-00-introduction

# Create logs directory
mkdir -p ../../../logs

# Standard users:
nohup bash -c 'source ../../../.venv-podman/bin/activate && ./start-chapter-resources-podman.sh' \
  > ../../../logs/chapter-00-podman-$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Network users (high UID):
nohup sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh \
  > ../../../logs/chapter-00-podman-$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Note the PID
echo $! > ../../../logs/chapter-00-podman.pid

# View log in real-time
tail -f ../../../logs/chapter-00-podman-*.log
```

### Launch Chapter 1 (Main Architecture)

```bash
cd docs/tutorial-branches/chapter-01-main

# Standard users:
./start-chapter-resources-podman.sh

# Network users (high UID):
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

### Launch Chapter 2 (HPC MCP Server)

```bash
cd docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot

# Standard users:
./start-chapter-resources-podman.sh

# Network users (high UID):
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

### Launch Chapter 3 (Sandbox) - Rootful ALWAYS Required

Chapter 3 requires rootful Podman for ALL users due to nsjail privileged mode requirement:

```bash
cd docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent

# All users MUST use sudo:
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

---

## Troubleshooting

### Issue: "insufficient UIDs or GIDs available"

**Error:**
```
potentially insufficient UIDs or GIDs available in user namespace
Check /etc/subuid and /etc/subgid
```

**Solution:**
Configure subuid/subgid ranges (see Step 3 above).

---

### Issue: "lsetxattr: operation not supported"

**Error:**
```
lsetxattr /path/to/storage: operation not supported
```

**Cause:** NFS home directory doesn't support extended attributes.

**Solution:**
The bootstrap script already configures local storage at `/tmp/podman-storage-$USER`. If you still see this, ensure:

```bash
# Verify storage configuration
cat ~/.config/containers/storage.conf

# Should show:
# graphroot = "/tmp/podman-storage-rigo160"
# driver = "vfs"
```

---

### Issue: "can't merge value of [platform]"

**Error:**
```
ValueError: can't merge value of [platform] of type <class 'str'> and <class 'NoneType'>
```

**Cause:** Older issue with overlay files setting `platform: null`.

**Solution:**
This has been fixed in the latest overlay files. Update your branch:
```bash
git pull origin feature-add-podman-support
```

---

### Issue: Build fails with "short-name resolution"

**Error:**
```
short-name resolution enforced but cannot prompt without a TTY
```

**Solution:**
Configure container registries to use fully qualified names:

```bash
# Edit or create ~/.config/containers/registries.conf
cat >> ~/.config/containers/registries.conf << 'EOF'
unqualified-search-registries = ["docker.io", "quay.io"]

[[registry]]
location = "docker.io"
[[registry]]
location = "quay.io"
EOF
```

---

### Issue: Containers won't start - "permission denied"

**Cause:** SELinux or permission issues on NFS.

**Solutions:**

1. **Check SELinux status:**
   ```bash
   getenforce
   # If enforcing, may need adjustments
   ```

2. **Verify overlay file is loaded:**
   ```bash
   cd docs/tutorial-branches/chapter-XX
   ls -l docker-compose.podman.yaml
   # Should exist
   ```

3. **Try rootful mode instead:**
   ```bash
   sudo -E ./start-chapter-resources-podman.sh
   ```

---

### Issue: "Operation not permitted" in rootless mode

**Cause:** Some operations require elevated privileges.

**Solution:**
Use rootful Podman with sudo:
```bash
sudo -E bash -c 'source /path/to/.venv-podman/bin/activate && ./start-chapter-resources-podman.sh'
```

---

## Verification Commands

### Check Podman Status

```bash
# Podman version
podman --version

# Podman info
podman info | head -30

# Storage configuration
cat ~/.config/containers/storage.conf

# Subuid/subgid configuration
grep $USER /etc/subuid /etc/subgid
```

### Check Running Containers

```bash
# List all containers
podman ps -a

# List by project
podman ps -a | grep agentic

# Container logs
podman logs agentic_mcp_server_ch00

# Follow logs
podman logs -f agentic_streamlit_app_ch00
```

### Check Environment

```bash
# Verify virtual environment is activated
which podman-compose
# Should show: /path/to/.venv-podman/bin/podman-compose

# Check installed packages
pip list | grep podman
```

---

## Complete Setup Checklist

- [ ] Podman installed (4.0+)
- [ ] Bootstrap script executed: `./bootstrap-podman-env.sh`
- [ ] Storage configured: `/tmp/podman-storage-$USER`
- [ ] Subuid/subgid configured (if bootstrap warned)
- [ ] Test passed: `podman run --rm hello-world`
- [ ] Virtual environment activated: `source .venv-podman/bin/activate`
- [ ] podman-compose accessible: `which podman-compose`
- [ ] Ready to launch chapters!

---

## Quick Reference

### One-Time Setup
```bash
# 1. Install Podman (if not already)
sudo dnf install -y podman

# 2. Run bootstrap
./bootstrap-podman-env.sh

# 3. Configure subuid/subgid (if warned)
sudo usermod --add-subuids 100000-165535 $USER
sudo usermod --add-subgids 100000-165535 $USER
podman system migrate

# 4. Test
source .venv-podman/bin/activate
podman run --rm hello-world
```

### Daily Usage
```bash
# Activate environment
source .venv-podman/bin/activate

# Launch chapter (rootless - Chapters 0-2)
cd docs/tutorial-branches/chapter-01-main
./start-chapter-resources-podman.sh

# OR Background with logging
mkdir -p ../../../logs
nohup bash -c 'source ../../../.venv-podman/bin/activate && ./start-chapter-resources-podman.sh' \
  > ../../../logs/chapter-01-podman-$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Monitor logs
tail -f logs/chapter-01-podman-*.log

# Access UI
# Streamlit: http://localhost:8501
# MCP Server: http://localhost:8080
```

---

## Related Documentation

- **Comprehensive Guide:** [docs/podman-deployment-guide.md](podman-deployment-guide.md)
- **Test Procedures:** [docs/test-procedures-podman.md](test-procedures-podman.md)
- **Bootstrap Notes:** [docs/PODMAN_BOOTSTRAP_NOTES.md](PODMAN_BOOTSTRAP_NOTES.md)

---

**Last Updated:** 2026-02-09
**Bootstrap Script Version:** 1.1
**Tested On:** Rocky Linux 9.7, Podman 5.6.0
