# Podman Deployment Guide for ADEPT Framework

> **⚠️ IMPORTANT: Network/LDAP User Limitation**
>
> If you're on a system with network authentication (LDAP/NIS) and have a high UID (>100000), **rootful Podman (sudo) is REQUIRED** for all chapters. Rootless mode will not work due to newuidmap limitations. See [Known Issues](#known-issues-and-limitations) for details.
>
> **Quick solution:** Use `sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh` for all chapters.

## Table of Contents

1. [Introduction](#introduction)
2. [Why Podman for ADEPT?](#why-podman-for-adept)
3. [Installation](#installation)
4. [Chapter Compatibility Matrix](#chapter-compatibility-matrix)
5. [Rootless vs Rootful Mode](#rootless-vs-rootful-mode)
6. [Step-by-Step Setup](#step-by-step-setup)
7. [Known Issues and Limitations](#known-issues-and-limitations)
8. [Performance Considerations](#performance-considerations)
9. [Migration from Docker](#migration-from-docker)
10. [Troubleshooting](#troubleshooting)
11. [FAQ](#faq)

---

## Introduction

This guide provides comprehensive instructions for deploying the ADEPT (Agentic Discovery and Exploration Platform for Tools) framework using **Podman** as an alternative to Docker. Podman offers a daemonless, rootless-capable container runtime that integrates well with HPC environments and air-gapped systems.

**Supported Chapters:** 0-3 (Introduction through LLM Sandbox and Multi-Agent)

**Not Yet Supported:** Chapters 4-6 (Kubernetes, OpenWebUI, Agent Gateway)

**Quick Start:** For a streamlined setup process, see [PODMAN_QUICKSTART.md](PODMAN_QUICKSTART.md) which provides step-by-step instructions with solutions for common HPC environment issues.

---

## Why Podman for ADEPT?

### Advantages of Using Podman

1. **Daemonless Architecture**
   - No background daemon process required
   - Simpler security model
   - Better process isolation

2. **Rootless Container Support**
   - Run containers as non-root user (Chapters 0-2)
   - Enhanced security for development environments
   - No daemon running as root

3. **HPC Environment Integration**
   - Widely adopted in scientific computing centers
   - Works well with schedulers like Slurm
   - No systemd dependency for rootless mode

4. **Docker Compatibility**
   - Drop-in replacement for most Docker commands
   - Compatible with Dockerfile syntax
   - Works with Docker Compose files via podman-compose

5. **Air-Gapped Deployment**
   - Simpler dependency chain
   - Easier to set up in restricted networks
   - No need for Docker daemon registration

### When to Use Podman vs Docker

**Use Podman when:**
- Deploying on HPC/scientific computing systems
- Root access is restricted or unavailable
- Security policies prohibit Docker daemon
- Working in air-gapped environments
- You prefer rootless container execution

**Use Docker when:**
- You need Chapter 4-6 features (not yet supported in Podman)
- Your organization standardizes on Docker
- You're already familiar with Docker tooling
- You need guaranteed compatibility with all features

---

## Installation

### Prerequisites

- **Operating System:** Linux (Ubuntu, Fedora, RHEL, etc.), macOS, or Windows with WSL2
- **Podman:** Version 4.0 or higher
- **Python:** 3.11+ (for podman-compose)
- **pip or pipx:** For installing podman-compose

### Linux Installation

#### Ubuntu/Debian

```bash
# Update package index
sudo apt-get update

# Install Podman
sudo apt-get install -y podman

# Install podman-compose via pip
pip install podman-compose

# Or use pipx for isolated installation
pipx install podman-compose
```

#### Fedora/RHEL/CentOS

```bash
# Podman is typically pre-installed on Fedora
# If not, install it:
sudo dnf install -y podman

# Install podman-compose
pip install podman-compose
```

#### Arch Linux

```bash
# Install Podman
sudo pacman -S podman

# Install podman-compose
pip install podman-compose
```

### macOS Installation

```bash
# Install Podman using Homebrew
brew install podman

# Initialize Podman machine (required on macOS)
podman machine init
podman machine start

# Install podman-compose
pip install podman-compose
```

### Windows (WSL2)

```bash
# Inside WSL2 Ubuntu distribution
# Follow Ubuntu installation steps above

# Ensure WSL2 is using version 2
wsl --set-version Ubuntu 2
```

### Verify Installation

```bash
# Check Podman version
podman --version
# Expected: podman version 4.0.0 or higher

# Test basic Podman (may fail without further configuration)
podman run --rm hello-world
```

**Note:** If the test fails with permission or storage errors, proceed to the Bootstrap Process section below which handles these issues automatically.

### Automated Setup (Recommended)

Instead of manual installation of podman-compose and configuration, use our bootstrap script:

```bash
# From project root
./bootstrap-podman-env.sh
```

This script automatically:
- Configures Podman storage for NFS environments
- Creates a Python virtual environment
- Installs podman-compose and dependencies
- Checks for subuid/subgid configuration
- Provides fix instructions if needed

See [PODMAN_QUICKSTART.md](PODMAN_QUICKSTART.md) for detailed bootstrap usage.

---

## Chapter Compatibility Matrix

| Chapter | Description | Rootless | Rootful | Status | Notes |
|---------|-------------|----------|---------|--------|-------|
| **0** | Introduction (Basic Tools) | ✅ Yes | ✅ Yes | Fully Supported | Ollama, MCP server, Streamlit, JupyterLab |
| **1** | Main Architecture (Langchain) | ✅ Yes | ✅ Yes | Fully Supported | Recommended starting point |
| **2** | HPC MCP Server + CoT | ✅ Yes | ✅ Yes | Fully Supported | BLAST, Whisper, GitXRay tools |
| **3** | LLM Sandbox + Multi-Agent | ❌ No | ✅ Yes | Requires Rootful | nsjail requires privileged mode |
| **4** | Kubernetes Deployment | ⚠️ Partial | ⚠️ Partial | Not Documented | Possible but untested |
| **5** | OpenWebUI Integration | ❌ No | ❌ No | Not Supported | Future work |
| **6** | Agent Gateway | ❌ No | ❌ No | Not Supported | Future work |

### Legend

- ✅ **Yes**: Full support, tested and documented
- ⚠️ **Partial**: May work but not officially supported
- ❌ **No**: Not supported or incompatible

---

## Rootless vs Rootful Mode

> **IMPORTANT:** On systems with network/LDAP users (high UIDs), rootful Podman (sudo) is REQUIRED for all chapters due to newuidmap limitations. See [Known Issues](#known-issues-and-limitations) for details.

### Rootless Mode (Ideal for Standard Users)

**What is it?**
Rootless mode allows Podman to run containers as a non-root user without requiring sudo or elevated privileges.

**Advantages:**
- Enhanced security (containers can't escalate to root)
- No daemon running as root
- Safe for multi-tenant systems
- Default recommended mode for development

**Limitations:**
- ⚠️ **Does not work with network/LDAP users** - Users with high UIDs (>100000) from LDAP/NIS cannot use rootless mode due to newuidmap utility limitations
- ⚠️ This is a known unfixable issue (see [containers/podman#2898](https://github.com/containers/podman/issues/2898))
- Requires properly configured subuid/subgid ranges in `/etc/subuid` and `/etc/subgid`

**How to use (if your user supports it):**
```bash
# Check if you're a network user (high UID indicates LDAP/NIS)
id -u  # If > 100000, you likely need rootful mode

# If rootless is supported, run without sudo
cd docs/tutorial-branches/chapter-01-main
./start-chapter-resources-podman.sh
```

**Supported Chapters:** 0, 1, 2 (if rootless works for your user)

---

### Rootful Mode (Required for Network Users and Chapter 3)

**What is it?**
Rootful mode runs Podman with root privileges using sudo, similar to Docker's default behavior.

**When required:**
1. **Network/LDAP users (ALL CHAPTERS)** - Users with high UIDs cannot use rootless mode
2. **Chapter 3 sandbox features** - nsjail requires privileged mode for code sandboxing

**Why required for Chapter 3?**
The `sandbox_mcp_server` uses **nsjail** for code sandboxing, which requires:
- Privileged container mode
- Access to host kernel features
- Ability to create namespaces with elevated privileges

**Security Implications:**
- ⚠️ Containers run with elevated host privileges
- ⚠️ Potential for container escape if misconfigured
- ⚠️ Should only be used in trusted development environments
- ⚠️ Similar security model to Docker daemon
- ⚠️ Acceptable for HPC/scientific computing environments

**How to use:**
```bash
# Run with sudo, preserving PATH for podman-compose
cd docs/tutorial-branches/chapter-XX-name
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh

# Or with -E flag to preserve all environment variables (.env file, etc.)
sudo -E env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

**Important:** The `env "PATH=$PATH"` is required because sudo resets PATH and won't find podman-compose installed in `~/.local/bin`.

**Note:** Chapter 3 script will display an additional warning about privileged mode and require confirmation before proceeding.

---

## Step-by-Step Setup

### First-Time Setup

#### 1. Clone Repository

```bash
git clone https://github.com/pnnl/adept-agentic-framework-core.git
cd adept-agentic-framework-core
```

#### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your API keys
nano .env  # or use your preferred editor
```

Required variables:
```bash
OPENAI_API_KEY=your_key_here
# Or use other LLM providers:
ANTHROPIC_API_KEY=your_key_here
AZURE_API_KEY=your_key_here
OLLAMA_API_BASE=http://localhost:11434
```

#### 3. Choose Your Chapter

For first-time users, **Chapter 1** is recommended as it's the simplest and demonstrates core functionality.

```bash
cd docs/tutorial-branches/chapter-01-main
```

#### 4. Start Services with Podman

```bash
# Run the Podman-specific startup script
./start-chapter-resources-podman.sh
```

The script will:
1. Check for Podman and podman-compose installation
2. Auto-detect all necessary compose files
3. Include Podman-specific overlays automatically
4. Build images and start containers
5. Display logs in real-time

#### 5. Verify Services

Open a new terminal and check running containers:

```bash
podman ps
```

Expected output (Chapter 1):
```
CONTAINER ID  IMAGE                           COMMAND     PORTS
abcd1234      localhost/agentic_mcp_server    ...         0.0.0.0:8080->8080/tcp
efgh5678      localhost/agentic_streamlit_app ...         0.0.0.0:8501->8501/tcp
```

#### 6. Access the UI

Open your browser and navigate to:
```
http://localhost:8501
```

You should see the Streamlit interface for the ADEPT framework.

#### 7. Test MCP Server

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{"status": "healthy"}
```

### Running Different Chapters

#### Chapter 0 (Introduction with Ollama)

```bash
cd docs/tutorial-branches/chapter-00-introduction
./start-chapter-resources-podman.sh
```

**Services:** ollama, mcp_server, streamlit_app, jupyterlab

**Access Points:**
- Streamlit: http://localhost:8501
- JupyterLab: http://localhost:8888
- MCP Server: http://localhost:8080
- Ollama: http://localhost:11434

#### Chapter 2 (HPC MCP Server)

```bash
cd docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot
./start-chapter-resources-podman.sh
```

**Services:** mcp_server, streamlit_app, hpc_mcp_server

**Additional Features:**
- BLAST bioinformatics tools
- Whisper audio transcription
- GitXRay repository analysis

#### Chapter 3 (LLM Sandbox) - Rootful Required

```bash
cd docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent

# Must use sudo with -E flag
sudo -E ./start-chapter-resources-podman.sh
```

**Warning Prompt:**
```
WARNING: Chapter 3 requires ROOTFUL Podman for sandbox functionality
Continue with rootful Podman? (y/N)
```

Type `y` and press Enter to proceed.

**Services:** mcp_server, streamlit_app, hpc_mcp_server, sandbox_mcp_server

### Stopping Services

Press `Ctrl+C` in the terminal running the script. The cleanup handler will:

1. Stop all containers gracefully
2. Remove containers
3. Prompt for network cleanup
4. Prompt for image cleanup (optional)

### Manual Cleanup

If the script doesn't clean up properly:

```bash
# Stop and remove containers
cd docs/tutorial-branches/chapter-XX-name
podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml down

# For Chapter 3 (rootful)
sudo podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml down

# Prune networks
podman network prune -f

# Prune images (caution: removes all unused images)
podman image prune -a -f
```

---

## Known Issues and Limitations

### 1. Network/LDAP User Limitation (CRITICAL)

**Issue:** Users with network/LDAP authentication (high UIDs > 100000) **cannot use rootless Podman** at all.

**Symptoms:**
```
newuidmap: Target process is owned by a different user
uid:316305 pw_uid:316305 st_uid:316305
```

**Root Cause:**
- The `newuidmap` utility doesn't properly handle high UIDs with subordinate UID/GID ranges
- This is a known unfixable limitation in the shadow-utils package
- Affects NIS, LDAP, and other network authentication systems common in HPC environments

**Solution:** **Use rootful Podman (sudo) for ALL chapters:**

```bash
# Check if you're affected (high UID indicates network user)
id -u  # If > 100000, you MUST use rootful mode

# Launch any chapter with rootful Podman
cd docs/tutorial-branches/chapter-XX-name
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

**Security note:** Rootful Podman has a similar security model to Docker daemon. It's acceptable for HPC development environments but should only be used in trusted networks.

**References:**
- [containers/podman#2898](https://github.com/containers/podman/issues/2898)
- [shadow-maint/shadow#158](https://github.com/shadow-maint/shadow/issues/158)

**Workaround:** If you have Docker available and are uncomfortable with rootful Podman, use Docker instead. All chapters support both.

---

### 2. Platform Warnings

**Issue:** Podman may display warnings about `platform: linux/amd64` specifications.

**Example:**
```
WARNING: platform linux/amd64 is ignored
```

**Solution:** This is expected behavior. The Podman overlay files set `platform: null` to suppress this warning, but you may still see it from the base compose file. It's safe to ignore.

### 3. SELinux Contexts

**Issue:** On SELinux-enforcing systems (Fedora, RHEL), volume mounts may fail with permission denied errors.

**Solution:** The Podman overlay files add `:Z` or `:z` suffixes to volume mounts:
- `:Z` = Private label (exclusive to one container)
- `:z` = Shared label (can be shared across containers)

If you still encounter issues:
```bash
# Check SELinux status
getenforce

# Temporarily set to permissive (not recommended for production)
sudo setenforce 0

# Or fix volume labels manually
podman unshare chown -R $(id -u):$(id -g) ./data
```

### 4. Socket Path Differences

**Issue:** Chapter 3 sandbox server expects Docker socket at `/var/run/docker.sock`.

**Solution:** The Podman overlay mounts Podman's socket at the Docker location with shared SELinux label:
```yaml
volumes:
  # :z = shared label (socket can be accessed by multiple containers)
  - /run/podman/podman.sock:/var/run/docker.sock:z
```

**Note:** This only works with rootful Podman. Rootless Podman sockets are located at:
```
$XDG_RUNTIME_DIR/podman/podman.sock
# Typically: /run/user/1000/podman/podman.sock
```

However, **rootless mode is not functional** on systems with network users (see issue #1).

### 5. Privileged Mode Requirement (Chapter 3)

**Issue:** The `llm-sandbox` package uses `nsjail` which requires privileged mode.

**Why it matters:**
- Rootless Podman cannot run truly privileged containers
- This is a security feature, not a bug
- Sandbox features fundamentally require elevated privileges

**Solutions:**
1. **Use rootful Podman** (as documented) - Supported
2. **Use Docker instead** for Chapter 3 - Recommended if uncomfortable with rootful
3. **Disable sandbox features** - Not documented, requires code changes

### 6. Performance on macOS

**Issue:** Podman on macOS runs inside a virtual machine, adding overhead.

**Impact:**
- Slower image builds
- Higher memory usage
- Filesystem operations slower than Linux

**Mitigation:**
```bash
# Allocate more resources to Podman machine
podman machine stop
podman machine rm
podman machine init --cpus=4 --memory=8192 --disk-size=100
podman machine start
```

### 7. Port Conflicts

**Issue:** Default ports may already be in use on your system.

**Affected Ports:**
- 8080 (MCP Server)
- 8081 (HPC MCP Server)
- 8082 (Sandbox MCP Server)
- 8501 (Streamlit)
- 8888 (JupyterLab)
- 11434 (Ollama)

**Solution:** Modify the `docker-compose.yaml` to use different ports:
```yaml
ports:
  - "9080:8080"  # Change host port to 9080
```

### 8. Image Building with Buildah

**Issue:** Podman uses Buildah for image building, which may behave slightly differently than Docker.

**Known Differences:**
- Different default isolation modes
- May require `--format docker` flag for compatibility
- Different handling of `.dockerignore`

**Solution:** If builds fail, try:
```bash
# Build with docker format
podman build --format docker -f Dockerfile -t image_name .
```

---

## Performance Considerations

### Build Performance

**Docker vs Podman:**
- **First build:** Podman typically 10-20% slower (no daemon caching)
- **Subsequent builds:** Comparable performance
- **Layer caching:** Works similarly to Docker

**Optimization Tips:**
```bash
# Use Podman's buildah cache
export BUILDAH_CACHEDIR=$HOME/.cache/buildah

# Parallel builds (if multiple services)
podman-compose build --parallel
```

### Runtime Performance

**Container Execution:**
- **Rootless mode:** 5-10% overhead compared to rootful (due to user namespaces)
- **Rootful mode:** Nearly identical to Docker performance
- **Networking:** Comparable performance for bridge networks

**Memory Usage:**
- **No daemon:** Podman uses ~50-100MB less RAM than Docker daemon
- **Containers:** Same memory usage as Docker

### Storage Performance

**Default Storage Driver:**
- Linux: `overlay2` (same as Docker)
- macOS: `vfs` (inside Podman machine)

**Check your storage driver:**
```bash
podman info | grep -A 5 "graphDriverName"
```

**Optimize for overlay2:**
```bash
# Edit /etc/containers/storage.conf
# Add or modify:
[storage]
driver = "overlay2"
```

---

## Migration from Docker

### For Existing Docker Users

If you've already used the Docker scripts, migrating to Podman is straightforward.

### Step 1: Stop Docker Services

```bash
# In your chapter directory
./start-chapter-resources.sh
# Press Ctrl+C to stop

# Verify containers are stopped
docker ps -a | grep agentic
```

### Step 2: Optional - Export Data

```bash
# If you want to preserve data volumes
docker volume inspect chapter-01-main_shared_uploads
docker volume inspect chapter-01-main_data

# Export if needed (not usually necessary)
```

### Step 3: Install Podman

Follow [Installation](#installation) instructions above.

### Step 4: Start with Podman

```bash
# Same directory
./start-chapter-resources-podman.sh
```

**Note:** Volume data stored in `./data` directory is automatically preserved since it's a bind mount.

### Step 5: Verify Functionality

Test all features to ensure they work identically:
- Streamlit UI access
- MCP tool calls
- File uploads
- RAG queries

### Switching Back to Docker

Simply run the original script:
```bash
./start-chapter-resources.sh
```

Both Docker and Podman can coexist on the same system without conflicts.

---

## Troubleshooting

### Problem: "podman-compose: command not found"

**Cause:** podman-compose is not installed or not in PATH.

**Solution:**
```bash
# Install via pip
pip install podman-compose

# Or via pipx for isolated installation
pipx install podman-compose

# Verify installation
which podman-compose
podman-compose --version
```

---

### Problem: Permission Denied on Volume Mounts

**Cause:** SELinux is blocking container access to host directories.

**Solution 1: Check SELinux labels**
```bash
ls -Z ./data
# Should show context labels like system_u:object_r:container_file_t:s0

# If not, relabel
podman unshare chown -R $(id -u):$(id -g) ./data
```

**Solution 2: Verify overlay file is loaded**
```bash
# Check that docker-compose.podman.yaml exists
ls -l docker-compose.podman.yaml

# Manually run with overlay
podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml up
```

**Solution 3: Temporarily disable SELinux (not recommended for production)**
```bash
# Check status
getenforce

# Set to permissive
sudo setenforce 0

# Test if issue is resolved
./start-chapter-resources-podman.sh
```

---

### Problem: Containers Won't Start - "Exec format error"

**Cause:** Architecture mismatch (e.g., trying to run amd64 images on ARM).

**Solution:**
```bash
# Check your architecture
uname -m

# If on ARM (Apple Silicon, Raspberry Pi), you may need to:
# 1. Remove platform specification entirely
# 2. Build native ARM images

# Edit docker-compose.podman.yaml to ensure platform: null
```

---

### Problem: Port Already in Use

**Cause:** Another service is using the required port.

**Solution:**
```bash
# Find what's using the port
sudo lsof -i :8080
# or
sudo netstat -tulpn | grep 8080

# Option 1: Stop the conflicting service
# Option 2: Change the port in docker-compose.yaml
ports:
  - "9080:8080"  # Use port 9080 on host instead
```

---

### Problem: Chapter 3 Fails with "Operation not permitted"

**Cause:** Running Chapter 3 in rootless mode (not supported).

**Solution:**
```bash
# Chapter 3 MUST run with sudo
sudo -E ./start-chapter-resources-podman.sh

# Verify you're running as root when script starts
# The script will check and warn if not
```

---

### Problem: Images Build Very Slowly

**Cause:** No layer caching or slow mirror.

**Solution:**
```bash
# Configure faster registry mirror (if applicable)
# Edit /etc/containers/registries.conf

# Use Buildah cache
export BUILDAH_CACHEDIR=$HOME/.cache/buildah

# Pull base images beforehand
podman pull python:3.11-slim
podman pull ollama/ollama:latest
```

---

### Problem: "network agentic_network not found"

**Cause:** Network cleanup was incomplete from previous run.

**Solution:**
```bash
# Manually create the network
podman network create agentic_network

# Or clean up and restart
podman network prune -f
./start-chapter-resources-podman.sh
```

---

### Problem: On macOS - "podman machine not running"

**Cause:** Podman machine VM is not started.

**Solution:**
```bash
# Check machine status
podman machine list

# Start the machine
podman machine start

# If doesn't exist, initialize
podman machine init
podman machine start
```

---

## FAQ

### Q: Can I use Podman and Docker at the same time?

**A:** Yes. Podman and Docker can coexist without conflicts. They use different socket paths and container storage locations.

---

### Q: Which is better for ADEPT - Podman or Docker?

**A:**
- **For most users:** Docker is recommended (more mature tooling, full chapter support)
- **For HPC environments:** Podman is preferred (rootless mode, no daemon)
- **For learning:** Start with Docker, migrate to Podman later if needed

---

### Q: Can I use Podman for Chapters 4-6?

**A:** Not officially supported yet. Chapters 4-6 involve Kubernetes deployments and advanced integrations that haven't been tested with Podman. It may work, but documentation and testing are incomplete.

---

### Q: Why does Chapter 3 require root?

**A:** The sandbox server uses `nsjail` for code isolation, which requires:
- Creating user/network namespaces with elevated privileges
- Mounting proc/sys filesystems
- Setting resource limits at kernel level

These operations are not possible in rootless mode by design (security feature).

---

### Q: Is rootful Podman as secure as rootless?

**A:** No. Rootful Podman has a similar security profile to Docker - containers run with elevated privileges and could potentially escape to the host if misconfigured. Only use rootful mode in trusted development environments.

---

### Q: Can I run ADEPT with Podman in production?

**A:** The framework is designed for research and development. For production:
- Use Kubernetes (Chapter 4) with proper RBAC
- Enable authentication and TLS
- Review security implications of each component
- Consider using managed container services

---

### Q: How do I update Podman?

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get upgrade podman
```

**Fedora/RHEL:**
```bash
sudo dnf update podman
```

**macOS:**
```bash
brew upgrade podman
```

---

### Q: Can I use podman-compose v2?

**A:** Podman Compose v2 is not yet stable. The instructions in this guide use the Python-based `podman-compose` which is compatible with Docker Compose file format.

---

### Q: Where are Podman volumes stored?

**Rootless:**
```bash
~/.local/share/containers/storage/volumes/
```

**Rootful:**
```bash
/var/lib/containers/storage/volumes/
```

To inspect:
```bash
podman volume ls
podman volume inspect volume_name
```

---

### Q: How do I access container logs?

```bash
# View logs
podman logs agentic_mcp_server

# Follow logs in real-time
podman logs -f agentic_streamlit_app

# Last 100 lines
podman logs --tail 100 agentic_mcp_server
```

---

### Q: Can I use Docker Compose instead of podman-compose?

**A:** No, Docker Compose is designed to work with Docker daemon. You must use `podman-compose` for Podman, which is compatible with Docker Compose file syntax.

---

### Q: What's the difference between :Z and :z volume flags?

**A:**
- `:Z` - Private unshared label. Only this container can access the volume.
- `:z` - Shared label. Multiple containers can share this volume.

Use `:Z` for exclusive access (like `./data`) and `:z` for shared volumes (like `shared_uploads`).

---

## Additional Resources

- **Podman Official Documentation:** https://docs.podman.io/
- **podman-compose GitHub:** https://github.com/containers/podman-compose
- **Podman Desktop (GUI):** https://podman-desktop.io/
- **ADEPT Main Documentation:** `/docs/agentic-framework-tutorial.md`
- **Test Procedures:** `/docs/test-procedures-podman.md`

---

## Support

For issues specific to Podman deployment:
1. Check [Known Issues](#known-issues-and-limitations)
2. Review [Troubleshooting](#troubleshooting)
3. Check [Test Procedures](/docs/test-procedures-podman.md)
4. Open an issue on GitHub with:
   - Chapter number
   - Podman version (`podman --version`)
   - Operating system
   - Error messages and logs
   - Whether using rootless or rootful mode

---

**Last Updated:** 2025-02-09
**Supported Podman Versions:** 4.0+
**Supported Chapters:** 0-3
