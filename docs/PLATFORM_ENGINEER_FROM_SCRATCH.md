# Platform Engineer From-Scratch Deployment Guide

**Target Audience:** System Administrators and Platform Engineers
**Use Case:** Deploying ADEPT Framework with Podman on a fresh system
**Environment:** HPC/Enterprise Linux with network authentication (LDAP/NIS)
**Time Estimate:** 30-45 minutes for complete setup

---

## Table of Contents

1. [Prerequisites Check](#prerequisites-check)
2. [System Preparation](#system-preparation)
3. [Podman Installation](#podman-installation)
4. [Project Setup](#project-setup)
5. [Podman Configuration](#podman-configuration)
6. [Chapter Deployment](#chapter-deployment)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

---

## Prerequisites Check

### System Requirements

**Minimum Requirements:**
- **OS:** Rocky Linux 9.x, RHEL 9.x, Ubuntu 22.04+, or Fedora 38+
- **RAM:** 8 GB (16 GB recommended for all services)
- **Disk:** 50 GB free space
- **CPU:** 4 cores (8 cores recommended)
- **Network:** Internet access for image pulls

**Software Requirements:**
- Python 3.9 or higher
- Git 2.x
- curl or wget
- Podman 4.0+ (5.0+ recommended)

**Access Requirements:**
- sudo/root access for Podman configuration
- Network access to Docker Hub (docker.io)
- Optional: API keys for LLM providers (OpenAI, Azure, Anthropic)

### Check Your User Type

Run this command to determine if you're a network/LDAP user:

```bash
id -u
# If output > 100000, you're a network user and MUST use rootful Podman
# If output < 100000, you're a local user and CAN use rootless Podman
```

**Network/LDAP Users:**
- High UID (typically > 100000)
- Common in HPC and enterprise environments
- **MUST use rootful Podman** (rootless won't work)
- Requires sudo for all Podman operations

**Local Users:**
- Low UID (typically 1000-60000)
- Can choose rootless or rootful Podman
- Rootless recommended for security

---

## System Preparation

### Step 1: Update System Packages

**Rocky Linux / RHEL:**
```bash
sudo dnf update -y
sudo dnf install -y git curl wget python3 python3-pip
```

**Ubuntu / Debian:**
```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y git curl wget python3 python3-pip python3-venv
```

**Fedora:**
```bash
sudo dnf update -y
sudo dnf install -y git curl wget python3 python3-pip
```

### Step 2: Install pip (if not present)

```bash
# Check if pip is available
python3 -m pip --version

# If not found, install pip
curl -sSL https://bootstrap.pypa.io/get-pip.py | python3 -
```

### Step 3: Verify Python Version

```bash
python3 --version
# Should show: Python 3.9.x or higher
```

---

## Podman Installation

### Step 1: Install Podman

**Rocky Linux / RHEL / Fedora:**
```bash
sudo dnf install -y podman podman-compose
```

**Ubuntu / Debian:**
```bash
# Add Podman repository (Ubuntu 20.04/22.04)
sudo apt-get update
sudo apt-get -y install podman

# Install podman-compose separately
sudo pip3 install podman-compose
```

### Step 2: Verify Podman Installation

```bash
podman --version
# Should show: podman version 4.x.x or 5.x.x

# Test Podman (will use rootless if possible)
podman run --rm hello-world
```

**If you get newuidmap errors:**
```
newuidmap: Target process is owned by a different user
```
This confirms you're a network user and MUST use rootful Podman (covered in configuration section).

### Step 3: Enable Podman Service (Optional)

Only needed for rootful Podman socket access:

```bash
sudo systemctl enable --now podman.socket
sudo systemctl status podman.socket
```

---

## Project Setup

### Step 1: Clone Repository

```bash
# Choose installation directory
cd ~  # or /opt, or wherever you prefer

# Clone the repository
git clone https://github.com/pnnl/adept-agentic-framework-core.git
cd adept-agentic-framework-core

# Checkout feature branch (if needed)
# git checkout feature-add-podman-support
```

### Step 2: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your API keys
nano .env  # or vim, emacs, etc.
```

**Required Variables:**
```bash
# At minimum, configure one LLM provider:
OPENAI_API_KEY=your_openai_key_here

# Optional: Other providers
ANTHROPIC_API_KEY=your_anthropic_key_here
AZURE_API_KEY=your_azure_key_here

# Optional: Model configuration
LANGCHAIN_LLM_MODEL=gpt-4o-mini
EMBEDDING_DEFAULT_MODEL=text-embedding-3-small
```

**Save and exit** (Ctrl+X, Y, Enter in nano).

### Step 3: Bootstrap Podman Environment

This creates a Python virtual environment with all Podman dependencies:

```bash
# Make bootstrap script executable
chmod +x bootstrap-podman-env.sh

# Run bootstrap (creates .venv-podman)
./bootstrap-podman-env.sh
```

**Expected output:**
```
==========================================
Podman Python Environment Bootstrap
==========================================

✓ Found Python 3.9.x
✓ Found Podman 5.6.0

Configuring Podman storage...
✓ Podman storage configured at /tmp/podman-storage-<user>

Creating virtual environment...
✓ Virtual environment created at .venv-podman

Installing Podman Python libraries...
✓ Installed: podman, podman-compose, python-dotenv, pyyaml, requests, rich

✓ Bootstrap complete!
```

### Step 4: Activate Podman Environment

```bash
# Method 1: Direct activation
source .venv-podman/bin/activate

# Method 2: Helper script
source ./activate-podman-env.sh

# Verify activation
which podman-compose
# Should show: /path/to/.venv-podman/bin/podman-compose
```

---

## Podman Configuration

### Step 1: Configure Container Registries

**CRITICAL:** This step configures Podman to search Docker Hub for images.

```bash
# Make configuration script executable
chmod +x configure-podman-registries.sh

# Run with sudo to configure rootful Podman
sudo ./configure-podman-registries.sh
```

**This script:**
- Creates `/root/.config/containers/registries.conf`
- Sets Docker Hub as primary registry
- Prevents "Repo not found" errors when pulling images

**Expected output:**
```
================================================================
Configuring Podman Registries for Docker Hub
================================================================

Creating /root/.config/containers directory...
Writing registries configuration to /root/.config/containers/registries.conf...

✓ Configuration complete!

Podman will now search docker.io (Docker Hub) for unqualified images.
```

### Step 2: Verify Podman Configuration

```bash
# Test rootful Podman access
sudo podman ps
# Should show: No errors, empty container list

# Test image pull from Docker Hub
sudo podman pull hello-world
# Should pull from docker.io, not Red Hat registry

# Clean up test image
sudo podman rmi hello-world
```

---

## Chapter Deployment

### Overview of Chapters

The ADEPT Framework has 4 chapters with progressive complexity:

| Chapter | Description | Services | Rootful Required? |
|---------|-------------|----------|-------------------|
| 0 | Introduction + Basic RAG | ollama, mcp_server, streamlit, jupyterlab | Network users only |
| 1 | Main Architecture | mcp_server, streamlit | Network users only |
| 2 | HPC Integration | mcp_server, streamlit, hpc_mcp_server | Network users only |
| 3 | Sandbox + Multi-Agent | mcp_server, streamlit, hpc_mcp_server, sandbox | **ALL users** |

**Note:** Chapter 3 requires rootful Podman for ALL users due to sandbox security requirements (nsjail).

### Deploy Chapter 0 (Recommended for First Test)

Chapter 0 is the most comprehensive and best for testing your setup.

```bash
# Ensure Podman environment is activated
source .venv-podman/bin/activate

# Navigate to Chapter 0
cd docs/tutorial-branches/chapter-00-introduction

# For network/LDAP users (UID > 100000) - REQUIRED
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh

# For local users (UID < 100000) - OPTIONAL (can use rootless)
./start-chapter-resources-podman.sh
```

**What happens during launch:**
1. Script checks for rootful mode (if required)
2. Verifies podman and podman-compose are available
3. Pulls/builds container images (first time only)
4. Starts all services
5. Displays service URLs

**Expected services started:**
- Ollama (LLM runtime): http://localhost:11434
- MCP Server: http://localhost:8080
- Streamlit UI: http://localhost:8501
- JupyterLab: http://localhost:8888

**Build time:** 5-15 minutes on first run (pulls images and builds)
**Startup time:** 1-2 minutes on subsequent runs

### Background Mode (Optional)

For production or long-running deployments:

```bash
# Create logs directory
mkdir -p logs

# Launch in background
nohup sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh \
  > logs/chapter-00-$(date +%Y%m%d-%H%M%S).log 2>&1 &

# Save PID for later
echo $! > logs/chapter-00.pid

# Monitor logs
tail -f logs/chapter-00-*.log

# To stop later
kill $(cat logs/chapter-00.pid)
```

### Deploy Other Chapters

Once Chapter 0 works, deploy other chapters similarly:

**Chapter 1 (Main Architecture):**
```bash
cd docs/tutorial-branches/chapter-01-main
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

**Chapter 2 (HPC Integration):**
```bash
cd docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

**Chapter 3 (Sandbox - ALL users need sudo):**
```bash
cd docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

---

## Verification

### Step 1: Check Running Containers

```bash
# List all running containers
sudo podman ps

# Expected output (Chapter 0):
# CONTAINER ID  IMAGE                           COMMAND     CREATED        STATUS        PORTS                   NAMES
# <id>          localhost/chapter-00-mcp:latest ...         2 minutes ago  Up 2 minutes  0.0.0.0:8080->8080/tcp  agentic_mcp_server_ch00
# <id>          localhost/chapter-00-streamlit:latest ...   2 minutes ago  Up 2 minutes  0.0.0.0:8501->8501/tcp  agentic_streamlit_app_ch00
# <id>          ollama/ollama:latest ...                    2 minutes ago  Up 2 minutes  0.0.0.0:11434->11434/tcp ollama_ch00
# <id>          localhost/chapter-00-jupyter:latest ...     2 minutes ago  Up 2 minutes  0.0.0.0:8888->8888/tcp  agentic_jupyterlab_ch00
```

### Step 2: Test Service Endpoints

```bash
# Test Ollama
curl -f http://localhost:11434/api/tags
# Should return: JSON with available models

# Test MCP Server
curl -f http://localhost:8080/health
# Should return: {"status": "healthy"} or similar

# Test Streamlit (returns HTML)
curl -f http://localhost:8501
# Should return: HTTP 200 OK with HTML

# Test JupyterLab (returns HTML)
curl -f http://localhost:8888
# Should return: HTTP 200 OK with HTML
```

### Step 3: Check Container Logs

```bash
# Check for errors in container logs
sudo podman logs agentic_mcp_server_ch00 | tail -20
sudo podman logs agentic_streamlit_app_ch00 | tail -20
sudo podman logs ollama_ch00 | tail -20
sudo podman logs agentic_jupyterlab_ch00 | tail -20

# Look for:
# ✓ No error messages
# ✓ Services started successfully
# ✓ No newuidmap errors
# ✓ No SELinux permission errors
```

### Step 4: Access Web Interfaces

Open in your browser:

1. **Streamlit UI:** http://localhost:8501
   - Should show ADEPT Framework interface
   - Test by asking a simple question

2. **JupyterLab:** http://localhost:8888
   - Should show JupyterLab interface
   - Check that notebooks directory is accessible

3. **Ollama (API only):** http://localhost:11434
   - Can test with: `curl http://localhost:11434/api/generate -d '{"model":"llama2","prompt":"Hello"}'`

### Step 5: Verify No Errors

```bash
# Check for newuidmap errors (should be none)
sudo podman logs agentic_mcp_server_ch00 2>&1 | grep -i newuidmap
# Expected: No output

# Check for SELinux errors (should be none)
sudo podman logs agentic_mcp_server_ch00 2>&1 | grep -i "permission denied"
# Expected: No output

# Check for image pull errors (should be none)
sudo podman logs agentic_mcp_server_ch00 2>&1 | grep -i "pull"
# Expected: Successful pulls from docker.io
```

---

## Testing and Validation

### Automated Test Suite

Validate your deployment with the comprehensive test suite:

```bash
# From project root

# Test Chapter 0 (after deployment)
sudo -E ./tests/podman/test-podman-deployment.sh 0

# Quick smoke test
./tests/podman/quick-test.sh 0
```

**Test Categories:**
- ✅ Prerequisites (Podman, podman-compose, Python, registry config)
- ✅ Environment setup (project structure, virtual env)
- ✅ Chapter configuration (YAML syntax, SELinux labels, permissions)
- ✅ Runtime validation (containers, logs, endpoints)
- ✅ Chapter-specific configs (DATABASE_URL, permissions, etc.)

**Example output:**
```
Total Tests:   20
Passed:        17
Failed:        0
Skipped:       3

TEST SUITE PASSED
```

See [PODMAN_TESTING.md](PODMAN_TESTING.md) for complete test suite documentation.

### Helper Scripts

**Chapter 0 troubleshooting tools** (in chapter directory):

```bash
cd docs/tutorial-branches/chapter-00-introduction

# Cross-reference logs with error highlighting
sudo ./check-service-logs.sh summary  # Errors only
sudo ./check-service-logs.sh health   # Check endpoints
sudo ./check-service-logs.sh follow   # Live tail

# Comprehensive health verification
sudo ./verify-services.sh

# Configure passwordless sudo (optional)
sudo ./configure-sudo-nopasswd.sh
```

**Cleanup stale processes** (from project root):

```bash
# Clean up orphaned containers and processes
sudo ./scripts/cleanup-stale-processes.sh
```

Use this:
- After interrupted deployments (Ctrl+C, nohup disconnect)
- Before starting a new chapter
- When switching between chapters

**Available helper scripts:**
- `tests/podman/test-podman-deployment.sh` - Comprehensive test suite
- `tests/podman/quick-test.sh` - Fast smoke tests
- `scripts/cleanup-stale-processes.sh` - Clean up stale processes
- `docs/tutorial-branches/chapter-00-introduction/check-service-logs.sh` - Log monitoring
- `docs/tutorial-branches/chapter-00-introduction/verify-services.sh` - Health checks
- `docs/tutorial-branches/chapter-00-introduction/configure-sudo-nopasswd.sh` - Sudo config

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "podman-compose: command not found"

**Symptom:** Script fails with command not found error

**Cause:** sudo reset PATH, podman-compose not in root's PATH

**Solution:**
```bash
# Always use env "PATH=$PATH" with sudo
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh

# Verify podman-compose location
which podman-compose
# Add this directory to command if needed
```

#### Issue 2: "Repo not found" when pulling images

**Symptom:** Error pulling jupyter/scipy-notebook or other images from registry.access.redhat.com

**Cause:** Registries not configured, Podman searching wrong registry

**Solution:**
```bash
# Run registry configuration
sudo ./configure-podman-registries.sh

# Verify configuration
sudo cat /root/.config/containers/registries.conf
# Should show: unqualified-search-registries = ["docker.io"]

# Retry deployment
```

#### Issue 3: newuidmap errors

**Symptom:** "Target process is owned by a different user" errors

**Cause:** Network/LDAP user trying to use rootless Podman

**Solution:**
```bash
# Check your UID
id -u
# If > 100000, you MUST use rootful Podman

# Always use sudo for all chapters
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

#### Issue 4: Permission denied on volumes

**Symptom:** Container can't access mounted volumes

**Cause:** SELinux context mismatch

**Solution:**
```bash
# Check if SELinux is enforcing
getenforce

# Temporarily set permissive (testing only)
sudo setenforce 0

# Proper fix: Ensure SELinux labels in overlay files
# Should have :Z or :z suffixes on volume mounts
grep "volumes:" -A 5 docker-compose.podman.yaml
```

#### Issue 5: Port already in use

**Symptom:** "address already in use" errors

**Cause:** Another service using same ports

**Solution:**
```bash
# Find what's using the port
sudo lsof -i :8080  # or :8501, :8888, :11434

# Stop conflicting service or change ports
# Edit docker-compose.yaml to use different host ports
```

#### Issue 6: Out of disk space

**Symptom:** "no space left on device" errors

**Cause:** Container images and volumes fill disk

**Solution:**
```bash
# Check disk usage
df -h

# Clean up Podman resources
sudo podman system prune -a -f

# Check Podman storage location
sudo podman info | grep -A 5 graphRoot
```

#### Issue 7: Cannot connect to Podman socket

**Symptom:** "cannot connect to Podman. Is the Podman daemon running?"

**Cause:** Podman service not running (rootful mode)

**Solution:**
```bash
# Enable and start Podman socket
sudo systemctl enable --now podman.socket
sudo systemctl status podman.socket

# Verify socket exists
ls -l /run/podman/podman.sock

# Test connection
sudo podman ps
```

---

## Maintenance

### Daily Operations

**Start Services:**
```bash
cd docs/tutorial-branches/chapter-XX-name
source ../../.venv-podman/bin/activate  # Adjust path as needed
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

**Stop Services:**
```bash
# Graceful shutdown (if running in foreground)
Ctrl+C

# Force stop (if running in background)
cd docs/tutorial-branches/chapter-XX-name
sudo podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml down
```

**View Logs:**
```bash
# Real-time logs
sudo podman logs -f agentic_mcp_server_ch00

# Last N lines
sudo podman logs --tail 50 agentic_mcp_server_ch00

# All container logs
sudo podman-compose logs
```

### Weekly Maintenance

**Update Container Images:**
```bash
# Pull latest images
sudo podman pull ollama/ollama:latest
sudo podman pull jupyter/scipy-notebook:latest

# Rebuild services with new images
cd docs/tutorial-branches/chapter-00-introduction
sudo podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml up --build -d
```

**Clean Up Resources:**
```bash
# Remove stopped containers
sudo podman container prune -f

# Remove unused images
sudo podman image prune -f

# Remove unused volumes
sudo podman volume prune -f

# Full cleanup (aggressive)
sudo podman system prune -a -f
```

**Check System Health:**
```bash
# Container status
sudo podman ps -a

# Resource usage
sudo podman stats --no-stream

# Disk usage
sudo podman system df

# System info
sudo podman info
```

### Monthly Maintenance

**Update System Packages:**
```bash
sudo dnf update -y  # or apt-get update && apt-get upgrade -y
sudo reboot  # if kernel updated
```

**Update Podman:**
```bash
sudo dnf update podman podman-compose  # Rocky/RHEL/Fedora
sudo apt-get update && sudo apt-get upgrade podman  # Ubuntu/Debian
```

**Update ADEPT Framework:**
```bash
cd ~/adept-agentic-framework-core
git pull origin main
./bootstrap-podman-env.sh  # Refresh dependencies if needed
```

**Backup Configuration:**
```bash
# Backup .env file
cp .env .env.backup-$(date +%Y%m%d)

# Backup data directories
tar -czf data-backup-$(date +%Y%m%d).tar.gz docs/tutorial-branches/chapter-*/data/
```

### Security Maintenance

**Review Podman Security:**
```bash
# Check for security updates
sudo dnf check-update podman

# Review container security
sudo podman inspect <container_id> | grep -i security

# Check SELinux denials
sudo ausearch -m avc -ts recent
```

**Update API Keys:**
```bash
# Rotate API keys in .env
nano .env

# Restart services to pick up new keys
cd docs/tutorial-branches/chapter-XX-name
sudo podman-compose restart
```

---

## Quick Reference

### Essential Commands

```bash
# Activate environment
source .venv-podman/bin/activate

# Launch chapter (network users)
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh

# Check containers
sudo podman ps

# Check logs
sudo podman logs <container_name>

# Stop services
Ctrl+C  # or sudo podman-compose down

# Clean up
sudo podman system prune -f
```

### Service URLs

- Streamlit UI: http://localhost:8501
- MCP Server: http://localhost:8080
- JupyterLab: http://localhost:8888
- Ollama API: http://localhost:11434

### Important Files

- Environment: `.env`
- Podman venv: `.venv-podman/`
- Registry config: `/root/.config/containers/registries.conf`
- Chapter scripts: `docs/tutorial-branches/chapter-*/start-chapter-resources-podman.sh`

### Documentation

- Bootstrap notes: `docs/PODMAN_BOOTSTRAP_NOTES.md`
- Deployment guide: `docs/podman-deployment-guide.md`
- Quick start: `docs/PODMAN_QUICKSTART.md`
- Progress tracking: `docs/PODMAN_IMPLEMENTATION_PROGRESS.md`
- Bugfix process: `docs/PODMAN_BUGFIX_PROCESS.md`
- This guide: `docs/PLATFORM_ENGINEER_FROM_SCRATCH.md`

---

## Success Checklist

### Initial Deployment
- [ ] System packages updated
- [ ] Podman installed and verified
- [ ] Project cloned
- [ ] .env configured with API keys
- [ ] Podman environment bootstrapped
- [ ] Registries configured
- [ ] Chapter 0 launched successfully
- [ ] All services responding
- [ ] No errors in logs
- [ ] Web interfaces accessible

### Production Ready
- [ ] All chapters tested
- [ ] Backup procedures in place
- [ ] Monitoring configured
- [ ] Documentation reviewed
- [ ] Team trained on operations
- [ ] Security audit completed
- [ ] Disaster recovery plan
- [ ] Maintenance schedule created

---

## Support and Resources

### Getting Help

1. **Check documentation:**
   - Read troubleshooting section above
   - Review PODMAN_*.md files in docs/
   - Check README files in chapter directories

2. **Check logs:**
   - Container logs: `sudo podman logs <container>`
   - System logs: `sudo journalctl -u podman`
   - Script logs: Check logs/ directory

3. **Community support:**
   - GitHub Issues: [Repository link]
   - Podman documentation: https://docs.podman.io/
   - ADEPT Framework docs: In-repo documentation

### Additional Resources

- **Podman Official Docs:** https://docs.podman.io/
- **Rootless Containers:** https://rootlesscontaine.rs/
- **Docker to Podman Migration:** https://docs.podman.io/en/latest/markdown/podman-docker.1.html
- **SELinux with Containers:** https://www.redhat.com/en/blog/selinux-containers

---

**Document Version:** 1.0
**Last Updated:** 2026-02-09
**Maintainer:** ADEPT Framework Team
**Status:** Production Ready
