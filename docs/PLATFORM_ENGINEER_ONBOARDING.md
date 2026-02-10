# ADEPT Platform Engineer Onboarding Guide

**Document Version:** 1.0
**Last Updated:** 2026-02-09
**Framework Version:** ADEPT v0.1.0
**Target Audience:** Platform Engineers, DevOps, SREs, HPC Administrators

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Summary](#architecture-summary)
3. [Environment Prerequisites](#environment-prerequisites)
4. [Initial Setup](#initial-setup)
5. [Container Runtime Options](#container-runtime-options)
6. [Deployment Procedures](#deployment-procedures)
7. [Operational Tasks](#operational-tasks)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Troubleshooting Decision Tree](#troubleshooting-decision-tree)
10. [Security Considerations](#security-considerations)
11. [Performance Tuning](#performance-tuning)
12. [Appendix: Command Reference](#appendix-command-reference)

---

## Overview

### What is ADEPT?

**ADEPT** (Agentic Discovery and Exploration Platform for Tools) is a modular framework for building agentic scientific applications. It integrates LLMs with specialized scientific tools through the Model Context Protocol (MCP).

**Primary Purpose:** Educational and research tool for demonstrating LLM-tool integration patterns.

**Key Characteristics:**
- Microservices architecture with MCP protocol
- Multiple UI frontends (Streamlit, JupyterLab, OpenWebUI)
- LLM-agnostic design (OpenAI, Azure, Anthropic, Ollama, etc.)
- Progressive learning chapters (0-6)
- Pedagogical focus (not production-hardened)

### Your Role as Platform Engineer

You will be responsible for:
- ✅ Deploying and maintaining ADEPT environments
- ✅ Choosing appropriate container runtime (Docker vs Podman)
- ✅ Configuring infrastructure for development/research teams
- ✅ Troubleshooting deployment and operational issues
- ✅ Ensuring security in multi-tenant or shared environments
- ✅ Performance tuning and resource optimization

---

## Architecture Summary

### Service Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
├───────────────┬──────────────┬──────────────┬───────────────┤
│  Streamlit    │  JupyterLab  │  OpenWebUI   │     n8n       │
│  (Port 8501)  │ (Port 8888)  │ (Port 8902)  │  (Port 5678)  │
└───────┬───────┴──────┬───────┴──────┬───────┴───────┬───────┘
        │              │              │               │
        └──────────────┴──────────────┴───────────────┘
                            │
                    ┌───────▼────────┐
                    │ Langchain Agent │
                    │  Orchestrator   │
                    └───────┬────────┘
                            │
        ┌───────────────────┼────────────────────┐
        │                   │                    │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│   MCP Server   │  │ HPC MCP Server │  │Sandbox MCP Srv │
│  (Port 8080)   │  │  (Port 8081)   │  │  (Port 8082)   │
│                │  │                │  │                │
│ • RAG Tools    │  │ • BLAST        │  │ • Code Exec    │
│ • SQL Tools    │  │ • Whisper      │  │ • nsjail       │
│ • Web Search   │  │ • GitXRay      │  │ • Isolation    │
│ • Notes        │  │ • Nextflow     │  │                │
└───────┬────────┘  └───────┬────────┘  └────────────────┘
        │                   │
┌───────▼───────────────────▼────────┐
│         Data Layer                  │
├────────────┬──────────┬─────────────┤
│  ChromaDB  │  SQLite  │   Redis     │
│  (Vector)  │ (Struct) │  (Session)  │
└────────────┴──────────┴─────────────┘
```

### Chapter Progression

| Chapter | Services | Complexity | Recommended For |
|---------|----------|------------|-----------------|
| **0** | Ollama + MCP + Streamlit + Jupyter | Medium | Full feature demo |
| **1** | MCP + Streamlit | Low | **Initial deployment** |
| **2** | Ch1 + HPC MCP Server | Medium | Scientific tools |
| **3** | Ch2 + Sandbox Server | High | Code execution |
| **4** | Kubernetes deployment | High | Production-like |
| **5** | OpenWebUI integration | High | Alternative UI |
| **6** | Agent Gateway + Advanced | Very High | Full stack |

**Recommended starting point:** **Chapter 1** (simplest, core functionality)

---

## Environment Prerequisites

### Hardware Requirements

**Minimum (Development):**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 20 GB free space
- Network: Internet access for API calls and image pulls

**Recommended (Production-like):**
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 50+ GB SSD
- Network: High-bandwidth, low-latency

### Software Requirements

**Core:**
- Linux OS (Ubuntu 20.04+, RHEL/Rocky 8+, Fedora 35+)
- Python 3.11+ (3.9+ for Podman only)
- Git

**Container Runtime (choose one):**
- **Docker:** 24.0+ with Compose V2
- **Podman:** 4.0+ (5.0+ recommended)

**Optional:**
- Kubernetes 1.25+ (for Chapter 4)
- Helm 3.10+ (for Chapter 4)
- kubectl (for Chapter 4)

### Network Requirements

**Required Ports:**
- 8080 (MCP Server)
- 8081 (HPC MCP Server - Ch2+)
- 8082 (Sandbox Server - Ch3+)
- 8501 (Streamlit UI)
- 8888 (JupyterLab - Ch0)
- 11434 (Ollama - Ch0)

**Outbound Access:**
- registry-1.docker.io (Docker Hub)
- quay.io (Container images)
- api.openai.com (if using OpenAI)
- api.anthropic.com (if using Claude)

### API Keys Required

**At minimum one of:**
- `OPENAI_API_KEY` (OpenAI)
- `ANTHROPIC_API_KEY` (Claude)
- `AZURE_API_KEY` (Azure OpenAI)
- Local Ollama installation (Ch0)

---

## Initial Setup

### Step 1: Clone Repository

```bash
# Clone from GitHub
git clone https://github.com/pnnl/adept-agentic-framework-core.git
cd adept-agentic-framework-core

# Check current branch
git branch -a

# Verify structure
ls -la
```

**Expected structure:**
```
adept-agentic-framework-core/
├── docs/
│   ├── tutorial-branches/
│   │   ├── chapter-00-introduction/
│   │   ├── chapter-01-main/
│   │   ├── chapter-02-hpc-mcp-server-with-cot/
│   │   ├── chapter-03-llm-sandbox-and-multi-agent/
│   │   ├── chapter-04-kubernetes-deployment/
│   │   ├── chapter-05-openwebui-integration/
│   │   └── chapter-06-advanced-multi-agent-orchestration/
│   ├── podman-deployment-guide.md
│   └── PLATFORM_ENGINEER_ONBOARDING.md (this file)
├── src/agentic_framework_pkg/
├── .env.example
├── bootstrap-podman-env.sh
├── README.md
└── CLAUDE.md
```

### Step 2: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env  # or vim, emacs, etc.
```

**Required variables:**
```bash
# LLM Provider (choose one or more)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AZURE_API_KEY=...
AZURE_API_BASE=https://your-resource.openai.azure.com/
OLLAMA_API_BASE=http://localhost:11434  # If using local Ollama

# Model Configuration
LANGCHAIN_LLM_MODEL=gpt-4o-mini
EMBEDDING_DEFAULT_MODEL=text-embedding-3-small

# Data Persistence
CHROMA_DB_PATH=./data/persistent_chroma_db

# Server Ports (defaults)
MCP_SERVER_PORT=8080
HPC_MCP_SERVER_PORT=8081
SANDBOX_MCP_SERVER_PORT=8082
STREAMLIT_SERVER_PORT=8501
```

**Security note:** The `.env` file is gitignored. Never commit API keys.

### Step 3: Choose Container Runtime

You have two options: **Docker** (recommended for simplicity) or **Podman** (better for HPC/rootless).

**Decision matrix:**

| Factor | Docker | Podman |
|--------|--------|--------|
| Ease of setup | ✅ Simple | ⚠️ Moderate |
| Chapter support | ✅ All (0-6) | ⚠️ Only 0-3 |
| Root required | ⚠️ Daemon runs as root | ✅ Rootless capable |
| HPC integration | ❌ Limited | ✅ Better |
| Corporate adoption | ✅ High | ⚠️ Growing |
| Learning curve | ✅ Low | ⚠️ Medium |

**Recommendation:** Start with Docker, migrate to Podman later if needed.

---

## Container Runtime Options

### Option A: Docker Setup (Recommended)

#### Install Docker

**Ubuntu/Debian:**
```bash
# Install Docker from official repository
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

**RHEL/Rocky:**
```bash
# Install from distribution packages
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### Test Docker

```bash
docker run --rm hello-world
# Should pull and run successfully
```

#### Launch Chapter 1 (Recommended First Deployment)

```bash
cd docs/tutorial-branches/chapter-01-main

# Interactive mode (logs to console)
./start-chapter-resources.sh

# OR Background mode with logging
mkdir -p ../../../logs
docker compose up --build --remove-orphans > ../../../logs/chapter-01-docker-$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

---

### Option B: Podman Setup (HPC/Rootless Environments)

#### Install Podman

**Rocky/RHEL:**
```bash
sudo dnf install -y podman
```

**Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install -y podman
```

#### Run Bootstrap Script

```bash
# From project root
./bootstrap-podman-env.sh
```

**Expected output:**
```
✓ Found Python 3.9.x
✓ Found Podman 5.6.0
✓ Podman storage configured at /tmp/podman-storage-$USER
⚠️  Warning: No subuid ranges found for user $USER
   (Fix instructions provided)
✓ Virtual environment created
✓ Created activation helper
```

#### Configure Subuid/Subgid (Critical)

```bash
# Add UID/GID ranges (requires sudo - one-time)
sudo usermod --add-subuids 100000-165535 $USER
sudo usermod --add-subgids 100000-165535 $USER

# Verify configuration
grep $USER /etc/subuid /etc/subgid
# Expected: rigo160:100000:65536 (for both files)

# Migrate Podman to use new ranges
podman system migrate
```

#### Test Podman

```bash
# Activate environment
source .venv-podman/bin/activate

# Test basic functionality
podman run --rm hello-world
# Should show "Hello Podman World" ASCII art
```

#### Launch Chapter 1 with Podman

```bash
cd docs/tutorial-branches/chapter-01-main

# Interactive mode
./start-chapter-resources-podman.sh

# OR Background mode with logging
mkdir -p ../../../logs
nohup bash -c 'source ../../../.venv-podman/bin/activate && ./start-chapter-resources-podman.sh' \
  > ../../../logs/chapter-01-podman-$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Save PID for management
echo $! > ../../../logs/chapter-01-podman.pid
```

---

## Deployment Procedures

### Standard Deployment: Chapter 1 (Core)

**Services deployed:**
- `mcp_server` - Tool hosting server (port 8080)
- `streamlit_app` - Web UI (port 8501)

**Steps:**

#### Using Docker:
```bash
cd docs/tutorial-branches/chapter-01-main

# Verify configuration
cat .env | grep -E "OPENAI|ANTHROPIC" | head -3

# Start services
./start-chapter-resources.sh
```

#### Using Podman:
```bash
cd docs/tutorial-branches/chapter-01-main

# Activate environment
source ../../../.venv-podman/bin/activate

# Start services
./start-chapter-resources-podman.sh
```

#### Verification:
```bash
# Check containers are running
docker ps  # or: podman ps

# Expected output:
# agentic_mcp_server
# agentic_streamlit_app

# Test MCP server health
curl http://localhost:8080/health
# OR test tools endpoint
curl http://localhost:8080/mcp/tools

# Test Streamlit UI
curl http://localhost:8501
# OR open in browser
```

#### Access Points:
- **Streamlit UI:** http://localhost:8501
- **MCP Server:** http://localhost:8080
- **API Docs:** http://localhost:8080/docs

---

### Advanced Deployment: Chapter 0 (Full Stack)

**Additional services:**
- `ollama` - Local LLM inference (port 11434)
- `jupyterlab` - Notebook interface (port 8888)

**Deployment:**
```bash
cd docs/tutorial-branches/chapter-00-introduction
./start-chapter-resources.sh  # Docker
# OR
./start-chapter-resources-podman.sh  # Podman
```

**First-time setup considerations:**
- Ollama pulls models on first use (5-10 minutes)
- JupyterLab requires token (check logs for token)
- Larger resource footprint (RAM: 6+ GB)

---

### HPC Deployment: Chapter 2

**Additional services:**
- `hpc_mcp_server` - Scientific computing tools (port 8081)

**Special requirements:**
- BLAST database mount (optional): `./blast_databases`
- Increased disk space for datasets

**Deployment:**
```bash
cd docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot

# Optional: Download BLAST databases
mkdir -p blast_databases
# (BLAST DB setup instructions in chapter README)

# Launch
./start-chapter-resources.sh  # or *-podman.sh
```

---

### Sandbox Deployment: Chapter 3

**Additional services:**
- `sandbox_mcp_server` - Isolated code execution (port 8082)

**⚠️ Security Requirements:**
- Requires privileged container mode
- **Docker:** Mounts `/var/run/docker.sock`
- **Podman:** Requires rootful mode (`sudo`)

**Deployment with Docker:**
```bash
cd docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent
./start-chapter-resources.sh
```

**Deployment with Podman (rootful):**
```bash
cd docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent
sudo -E ./start-chapter-resources-podman.sh
```

**Security implications:**
- Container can access host Docker/Podman socket
- Used for isolated code execution via nsjail
- Only deploy in trusted environments
- Not recommended for multi-tenant systems

---

## Operational Tasks

### Starting Services

**Foreground (interactive, logs to console):**
```bash
cd docs/tutorial-branches/chapter-XX-name
./start-chapter-resources.sh  # Docker
./start-chapter-resources-podman.sh  # Podman
```

**Background (daemon mode):**
```bash
# Docker
cd docs/tutorial-branches/chapter-XX-name
docker compose up -d --build

# Podman (with proper logging)
mkdir -p ../../../logs
nohup bash -c 'source ../../../.venv-podman/bin/activate && ./start-chapter-resources-podman.sh' \
  > ../../../logs/chapter-XX-$(date +%Y%m%d_%H%M%S).log 2>&1 &
echo $! > ../../../logs/chapter-XX.pid
```

---

### Stopping Services

**Foreground deployment:**
- Press `Ctrl+C` in the terminal
- Cleanup handler runs automatically

**Background deployment (Docker):**
```bash
cd docs/tutorial-branches/chapter-XX-name
docker compose down
```

**Background deployment (Podman):**
```bash
# If you saved the PID
kill $(cat logs/chapter-XX-podman.pid)

# OR use podman-compose
cd docs/tutorial-branches/chapter-XX-name
source ../../../.venv-podman/bin/activate
podman-compose down
```

**Graceful shutdown:**
```bash
# Docker
docker compose down --timeout 30

# Podman
podman-compose down --timeout 30
```

---

### Checking Service Health

```bash
# Container status
docker ps  # or: podman ps

# Service health checks
curl http://localhost:8080/health  # MCP Server
curl http://localhost:8081/health  # HPC Server (Ch2+)
curl http://localhost:8082/health  # Sandbox (Ch3+)
curl http://localhost:8501/        # Streamlit

# Detailed container info
docker inspect agentic_mcp_server
# or
podman inspect agentic_mcp_server
```

---

### Viewing Logs

**Real-time logs:**
```bash
# Docker - all services
docker compose logs -f

# Docker - specific service
docker logs -f agentic_mcp_server

# Podman
podman logs -f agentic_mcp_server

# Podman with compose
podman-compose logs -f
```

**Historical logs:**
```bash
# Last 100 lines
docker logs --tail 100 agentic_mcp_server

# Since timestamp
docker logs --since 2024-01-01T10:00:00 agentic_mcp_server

# Save to file
docker logs agentic_mcp_server > mcp_server_$(date +%Y%m%d).log
```

---

### Updating Services

**Pull latest code:**
```bash
git pull origin main
```

**Rebuild images:**
```bash
# Docker
cd docs/tutorial-branches/chapter-XX-name
docker compose build --no-cache

# Podman
source ../../../.venv-podman/bin/activate
podman-compose build --no-cache
```

**Rolling update (Docker):**
```bash
docker compose up -d --build --force-recreate
```

---

### Data Management

**Volume locations:**

**Docker:**
```bash
# List volumes
docker volume ls | grep chapter

# Inspect volume
docker volume inspect chapter-01-main_shared_uploads

# Backup volume
docker run --rm -v chapter-01-main_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/data-backup-$(date +%Y%m%d).tar.gz -C /data .
```

**Podman:**
```bash
# List volumes
podman volume ls

# Inspect volume
podman volume inspect chapter-01-main_shared_uploads

# Volume location (rootless)
ls -la ~/.local/share/containers/storage/volumes/
# OR with graphroot override:
ls -la /tmp/podman-storage-$USER/volumes/
```

**Bind mounts:**
```bash
# Data directory (bind mount)
ls -la docs/tutorial-branches/chapter-XX-name/data/

# Contains:
# - notes.db (SQLite - notes tool)
# - structured_data.db (SQLite - SQL query tool)
# - persistent_chroma_db/ (ChromaDB - RAG vectors)
```

**Backup bind mounts:**
```bash
cd docs/tutorial-branches/chapter-XX-name
tar czf backup-$(date +%Y%m%d).tar.gz data/
```

---

## Monitoring and Logging

### Container Resource Usage

**Docker:**
```bash
# Real-time resource usage
docker stats

# Specific containers
docker stats agentic_mcp_server agentic_streamlit_app

# Export to file
docker stats --no-stream > stats-$(date +%Y%m%d_%H%M%S).txt
```

**Podman:**
```bash
# Real-time resource usage
podman stats

# System disk usage
podman system df
```

### Application Logs

**Log locations (background deployments):**
```
logs/
├── chapter-00-docker-20260209_120000.log
├── chapter-00-podman-20260209_150000.log
├── chapter-01-docker-20260209_120000.log
├── bootstrap-podman-20260209_150000.log
└── *.pid files
```

**Monitoring commands:**
```bash
# Follow latest log
tail -f logs/chapter-*-$(date +%Y%m%d)*.log

# Search for errors
grep -i error logs/chapter-01-*.log

# Filter by service
grep "agentic_mcp_server" logs/chapter-01-*.log
```

### Health Check Scripts

Create a monitoring script:

```bash
#!/bin/bash
# health-check.sh

echo "=== ADEPT Health Check ==="
echo "Timestamp: $(date)"
echo ""

# Check MCP Server
if curl -sf http://localhost:8080/health > /dev/null; then
    echo "✓ MCP Server (8080) - Healthy"
else
    echo "✗ MCP Server (8080) - Down"
fi

# Check Streamlit
if curl -sf http://localhost:8501 > /dev/null; then
    echo "✓ Streamlit (8501) - Healthy"
else
    echo "✗ Streamlit (8501) - Down"
fi

# Check containers
echo ""
echo "=== Container Status ==="
docker ps --filter "name=agentic" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## Troubleshooting Decision Tree

### Problem: Services won't start

**Step 1: Check prerequisites**
```bash
# Docker
docker --version && docker compose version

# Podman
podman --version && podman-compose --version
```

**Step 2: Check for port conflicts**
```bash
sudo lsof -i :8080,8501,8081,8082
# OR
sudo netstat -tulpn | grep -E "8080|8501"
```

**Step 3: Check environment file**
```bash
test -f .env && echo "✓ .env exists" || echo "✗ .env missing"
grep -E "OPENAI_API_KEY|ANTHROPIC_API_KEY" .env
```

**Step 4: Check logs**
```bash
# Docker
docker compose logs

# Podman
podman-compose logs
```

---

### Problem: Container build fails

**Podman-specific: "insufficient UIDs/GIDs"**
```bash
# Configure subuid/subgid
sudo usermod --add-subuids 100000-165535 $USER
sudo usermod --add-subgids 100000-165535 $USER
podman system migrate
```

**Network issues:**
```bash
# Test connectivity
curl -I https://registry-1.docker.io/v2/
curl -I https://quay.io/v2/

# Configure proxy if needed (in ~/.docker/config.json or ~/.config/containers/registries.conf)
```

**Disk space:**
```bash
df -h
docker system df  # or: podman system df
```

---

### Problem: Services running but UI inaccessible

**Check network bindings:**
```bash
# Verify ports are bound
netstat -tulpn | grep -E "8080|8501"
# Should show 0.0.0.0:8080 and 0.0.0.0:8501

# Check firewall
sudo firewall-cmd --list-ports
# If needed, open ports:
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload
```

**Check container networking:**
```bash
# Docker
docker network inspect chapter-XX-name_agentic_network

# Podman
podman network inspect agentic_network
```

---

### Problem: "Permission denied" errors

**SELinux context (Podman-specific):**
```bash
# Check SELinux status
getenforce
# If Enforcing, check contexts:
ls -Z ./data

# Verify Podman overlay includes :Z/:z suffixes
cat docker-compose.podman.yaml | grep -A 2 volumes
```

**File permissions:**
```bash
# Check data directory ownership
ls -la data/
# Should be owned by your user

# Fix if needed
chown -R $USER:$USER data/
```

---

### Problem: MCP Server not responding

**Check service is running:**
```bash
docker ps | grep mcp_server
# or
podman ps | grep mcp_server
```

**Check logs for errors:**
```bash
docker logs agentic_mcp_server | grep -i error
# or
podman logs agentic_mcp_server | grep -i error
```

**Common issues:**
- Missing API keys in `.env`
- ChromaDB initialization failure (check disk space)
- Port already in use (check with `lsof`)

---

## Security Considerations

### For Development Environments

**Docker:**
- ⚠️ Docker daemon runs as root
- ⚠️ Users in `docker` group have root-equivalent access
- ⚠️ Mounted socket in Ch3 sandbox poses risk
- ✅ Acceptable for single-user dev machines
- ✅ Use Docker Desktop on macOS/Windows for better isolation

**Podman Rootless (Ch0-2):**
- ✅ Containers run as non-root user
- ✅ No daemon running as root
- ✅ Better isolation from host system
- ✅ Recommended for shared dev servers
- ⚠️ Some images may not work without subuid/subgid

**Podman Rootful (Ch3):**
- ⚠️ Similar security profile to Docker
- ⚠️ Requires sudo to run scripts
- ⚠️ Privileged container for sandbox
- ⚠️ Only use in trusted environments

### For Shared/HPC Environments

**Recommended setup:**
1. Use Podman rootless mode (Chapters 0-2)
2. Disable Chapter 3 (sandbox) or run under strict supervision
3. Limit API key access (use dedicated service accounts)
4. Monitor resource usage (CPU/memory limits)
5. Implement network policies (if using Kubernetes)

**API key security:**
```bash
# Use restrictive permissions on .env
chmod 600 .env

# Never commit .env (already in .gitignore)
# Use secret management systems for production
```

### Sandbox Security (Chapter 3)

**Risk assessment:**
- **High:** Privileged container with host socket access
- **Medium:** Code execution within nsjail sandbox
- **Low:** Network isolation (containers on bridge network)

**Mitigations:**
- Only enable in trusted dev environments
- Use separate networks for sandbox services
- Monitor all code execution activities
- Consider disabling internet access for sandbox container
- Implement audit logging

---

## Performance Tuning

### Resource Limits

**Set container resource limits:**

```yaml
# In docker-compose.yaml or docker-compose.override.yaml
services:
  mcp_server:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```

**Apply to running containers:**
```bash
# Docker
docker update --memory=4g --cpus=2 agentic_mcp_server

# Podman
podman update --memory=4g --cpus=2 agentic_mcp_server
```

### Build Performance

**Docker layer caching:**
```bash
# Use BuildKit
export DOCKER_BUILDKIT=1

# Parallel builds
docker compose build --parallel
```

**Podman build optimization:**
```bash
# Use Buildah cache
export BUILDAH_CACHEDIR=$HOME/.cache/buildah

# Parallel builds
podman-compose build --parallel
```

### Storage Optimization

**Docker:**
```bash
# Check disk usage
docker system df

# Clean up old images/containers
docker system prune -a

# Clean build cache
docker builder prune
```

**Podman:**
```bash
# Check disk usage
podman system df

# Clean up
podman system prune -a

# For /tmp storage, consider mounting larger tmpfs:
# sudo mount -o remount,size=20G /tmp
```

### Network Performance

**Use host networking for testing (not recommended for production):**
```yaml
services:
  mcp_server:
    network_mode: "host"
```

**Optimize bridge network:**
```yaml
networks:
  agentic_network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: br-adept
      com.docker.network.driver.mtu: 1500
```

---

## Appendix: Command Reference

### Quick Launch Commands

```bash
# Docker - Chapter 1 (recommended start)
cd docs/tutorial-branches/chapter-01-main && ./start-chapter-resources.sh

# Podman - Chapter 1 (with environment)
source .venv-podman/bin/activate && \
cd docs/tutorial-branches/chapter-01-main && \
./start-chapter-resources-podman.sh

# Docker - All services background
docker compose up -d --build

# Podman - All services background
podman-compose up -d --build
```

### Container Management

```bash
# List containers
docker ps -a
podman ps -a

# Stop specific container
docker stop agentic_mcp_server
podman stop agentic_mcp_server

# Remove container
docker rm agentic_mcp_server
podman rm agentic_mcp_server

# Restart container
docker restart agentic_mcp_server
podman restart agentic_mcp_server

# Execute command in container
docker exec -it agentic_mcp_server bash
podman exec -it agentic_mcp_server bash
```

### Image Management

```bash
# List images
docker images | grep agentic
podman images | grep agentic

# Remove image
docker rmi image_name
podman rmi image_name

# Remove all project images
docker images | grep agentic | awk '{print $3}' | xargs docker rmi
podman images | grep agentic | awk '{print $3}' | xargs podman rmi

# Rebuild specific service
docker compose build mcp_server
podman-compose build mcp_server
```

### Volume Management

```bash
# List volumes
docker volume ls
podman volume ls

# Inspect volume
docker volume inspect shared_uploads
podman volume inspect shared_uploads

# Remove unused volumes
docker volume prune
podman volume prune

# Backup volume
docker run --rm -v volume_name:/data -v $(pwd):/backup \
  alpine tar czf /backup/volume_backup.tar.gz -C /data .
```

### Network Management

```bash
# List networks
docker network ls
podman network ls

# Inspect network
docker network inspect agentic_network
podman network inspect agentic_network

# Remove unused networks
docker network prune
podman network prune
```

### Cleanup Commands

```bash
# Docker - nuclear option (removes everything)
docker compose down -v  # removes volumes too
docker system prune -a --volumes

# Podman - full cleanup
podman-compose down -v
podman system prune -a --volumes

# Remove specific chapter resources
cd docs/tutorial-branches/chapter-XX-name
docker compose down --remove-orphans
# or
podman-compose down --remove-orphans
```

---

## Environment-Specific Notes

### HPC/Cluster Environments

**Common characteristics:**
- NFS home directories
- No subuid/subgid by default
- Firewall restrictions
- No root access for users
- Slurm or other schedulers

**Recommended approach:**
1. Use Podman rootless (Chapters 0-2)
2. Request admin to configure subuid/subgid
3. Use local scratch space for storage (`/tmp` or `/scratch`)
4. Coordinate port allocations
5. Consider using compute nodes instead of login nodes

**Configuration for HPC:**
```bash
# Use scratch space for storage
mkdir -p /scratch/$USER/podman-storage

# Configure in ~/.config/containers/storage.conf
[storage]
driver = "vfs"
graphroot = "/scratch/$USER/podman-storage"
runroot = "/tmp/podman-run-$USER"
```

### Cloud VMs (AWS, Azure, GCP)

**Instance recommendations:**
- **Type:** General purpose (e.g., AWS t3.xlarge, Azure D4s_v3)
- **OS:** Ubuntu 22.04 LTS or RHEL 9
- **Disk:** 50+ GB SSD
- **Network:** Allow ports 8080, 8081, 8082, 8501

**Security groups:**
```
Inbound:
- 22 (SSH) - Your IP only
- 8501 (Streamlit) - Your IP or VPC only
- 8080-8082 (MCP servers) - Internal only

Outbound:
- All (for API calls and image pulls)
```

### Development Workstations

**macOS:**
- Use Docker Desktop (easiest)
- OR Podman Desktop with VM
- ARM (M1/M2): Remove `platform: linux/amd64` from compose files

**Windows:**
- Use WSL2 + Docker Desktop
- OR WSL2 + Podman
- Follow Linux instructions within WSL

**Linux:**
- Native Docker or Podman
- Best performance
- Most flexible configuration

---

## Quick Start Recommendations

### For First-Time Platform Engineers

**Day 1: Deploy with Docker (Chapter 1)**
```bash
# 1. Clone repository
git clone https://github.com/pnnl/adept-agentic-framework-core.git
cd adept-agentic-framework-core

# 2. Configure
cp .env.example .env
nano .env  # Add OPENAI_API_KEY

# 3. Launch
cd docs/tutorial-branches/chapter-01-main
./start-chapter-resources.sh

# 4. Access
# Open http://localhost:8501
```

**Day 2: Explore Chapter 0 (Full Stack)**
```bash
cd docs/tutorial-branches/chapter-00-introduction
./start-chapter-resources.sh
# Includes Ollama + JupyterLab
```

**Week 2: Try Podman (HPC Prep)**
```bash
# Bootstrap Podman
./bootstrap-podman-env.sh

# Configure subuid/subgid (request admin)
sudo usermod --add-subuids 100000-165535 $USER
sudo usermod --add-subgids 100000-165535 $USER
podman system migrate

# Launch with Podman
source .venv-podman/bin/activate
cd docs/tutorial-branches/chapter-01-main
./start-chapter-resources-podman.sh
```

### For HPC/Cluster Deployment

**Week 1: Podman Setup**
```bash
# 1. Request admin to install Podman system-wide
# 2. Request subuid/subgid configuration
# 3. Bootstrap environment
./bootstrap-podman-env.sh

# 4. Test
source .venv-podman/bin/activate
podman run --rm hello-world
```

**Week 2: Deploy Chapter 1**
```bash
cd docs/tutorial-branches/chapter-01-main
./start-chapter-resources-podman.sh
```

**Week 3: Expand to Chapter 2 (HPC tools)**
```bash
cd docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot
./start-chapter-resources-podman.sh
```

---

## Reference Documentation

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[PODMAN_QUICKSTART.md](PODMAN_QUICKSTART.md)** | Streamlined Podman setup | First Podman deployment |
| **[podman-deployment-guide.md](podman-deployment-guide.md)** | Comprehensive Podman reference | Detailed Podman info |
| **[test-procedures-podman.md](test-procedures-podman.md)** | Testing procedures | QA and validation |
| **[PODMAN_BOOTSTRAP_NOTES.md](PODMAN_BOOTSTRAP_NOTES.md)** | Issue log and solutions | Troubleshooting |
| **[agentic-framework-tutorial.md](agentic-framework-tutorial.md)** | Complete framework tutorial | Learning the framework |
| **[CLAUDE.md](../CLAUDE.md)** | Development commands | Quick reference |
| **[README.md](../README.md)** | Project overview | First read |

---

## Support and Escalation

### Self-Service Resources

1. Check [Troubleshooting Decision Tree](#troubleshooting-decision-tree)
2. Review chapter-specific README
3. Check logs for errors
4. Search GitHub issues

### Reporting Issues

**Include in bug reports:**
- Chapter number
- Container runtime (Docker/Podman version)
- Operating system and version
- Error messages (full stack traces)
- Reproduction steps
- Environment details (HPC, cloud, local)
- Logs from affected containers

**GitHub Issues:**
https://github.com/pnnl/adept-agentic-framework-core/issues

---

## Onboarding Checklist

### Day 1: Environment Setup
- [ ] Clone repository
- [ ] Configure `.env` with API keys
- [ ] Install Docker OR run Podman bootstrap
- [ ] (Podman only) Configure subuid/subgid
- [ ] Test container runtime with hello-world
- [ ] Read architecture overview

### Day 2: First Deployment
- [ ] Deploy Chapter 1 (core functionality)
- [ ] Access Streamlit UI (http://localhost:8501)
- [ ] Test basic agent query
- [ ] Test MCP tools (notes, RAG, SQL)
- [ ] Review container logs
- [ ] Check resource usage

### Week 1: Full Stack Exploration
- [ ] Deploy Chapter 0 (Ollama + JupyterLab)
- [ ] Deploy Chapter 2 (HPC tools)
- [ ] Deploy Chapter 3 (sandbox - understand security implications)
- [ ] Test all major features
- [ ] Review monitoring and logging
- [ ] Practice start/stop procedures

### Week 2: Advanced Operations
- [ ] Try alternative container runtime
- [ ] Configure resource limits
- [ ] Implement health checks
- [ ] Set up automated backups
- [ ] Document environment-specific configurations
- [ ] Create runbooks for common operations

### Ongoing
- [ ] Monitor resource usage trends
- [ ] Review security best practices
- [ ] Keep documentation updated
- [ ] Share feedback with development team

---

**Congratulations! You're now ready to deploy and operate ADEPT.**

**Recommended first action:** Deploy Chapter 1 with Docker.

**Questions?** Check the [FAQ section](podman-deployment-guide.md#faq) or open a GitHub issue.

---

**Document Maintainers:** PNNL ADEPT Team
**Contributions:** Submit PRs for improvements to this guide
**License:** See [LICENSE](../LICENSE) file
