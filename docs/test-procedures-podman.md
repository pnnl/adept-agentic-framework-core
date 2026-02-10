# Podman Deployment Test Procedures

## Overview

This document provides manual testing procedures for validating Podman deployment of the ADEPT framework across Chapters 0-3. These tests should be performed after initial setup and when making changes to Podman-specific configurations.

---

## Test Environment Requirements

### Minimum Requirements

- **Podman:** Version 4.0 or higher
- **podman-compose:** Latest version from PyPI
- **Python:** 3.11+
- **Disk Space:** 10GB free
- **RAM:** 8GB minimum, 16GB recommended
- **Network:** Internet access for pulling images and API calls

### Supported Operating Systems

- Ubuntu 20.04+
- Fedora 35+
- RHEL/CentOS 8+
- macOS 12+ (with Podman machine)
- Windows 11 with WSL2

### API Keys Required

At minimum, one of:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `AZURE_API_KEY`
- Local Ollama installation (Chapter 0)

---

## Pre-Test Setup

### 1. Environment Configuration

```bash
# Navigate to repository root
cd /path/to/adept-agentic-framework-core

# Verify .env file exists with API keys
cat .env | grep -E "OPENAI_API_KEY|ANTHROPIC_API_KEY"

# If not, create from example
cp .env.example .env
nano .env  # Add your API keys
```

### 2. Clean Slate

```bash
# Remove any existing containers
podman ps -a | grep agentic | awk '{print $1}' | xargs -r podman rm -f

# Remove volumes (optional - will delete data)
podman volume ls | grep chapter | awk '{print $2}' | xargs -r podman volume rm

# Prune networks
podman network prune -f
```

### 3. Verify Prerequisites

```bash
# Podman version
podman --version
# Should output: podman version 4.x.x or higher

# podman-compose version
podman-compose --version
# Should output version information

# Python version
python3 --version
# Should output: Python 3.11.x or higher

# Test basic Podman functionality
podman run --rm hello-world
# Should download and run successfully
```

---

## Chapter 0: Introduction Tests

### Test Environment

- **Mode:** Rootless
- **Services:** ollama, mcp_server, streamlit_app, jupyterlab
- **Estimated Time:** 15-20 minutes

### Test 0.1: Prerequisites Check

```bash
cd docs/tutorial-branches/chapter-00-introduction

# Verify files exist
ls -l start-chapter-resources-podman.sh
ls -l docker-compose.podman.yaml

# Verify script is executable
test -x start-chapter-resources-podman.sh && echo "✓ Script is executable" || echo "✗ Script not executable"
```

**Expected Result:** Both files exist, script is executable.

---

### Test 0.2: Service Startup

```bash
# Start services (in background or new terminal)
./start-chapter-resources-podman.sh
```

**Expected Output:**
```
=======================================================
  ADEPT Chapter Resource Manager (Podman)
  Chapter: chapter-00-introduction
=======================================================
Checking prerequisites...
✓ Podman 4.x.x
✓ podman-compose x.x.x

Info: Podman overlay file 'docker-compose.podman.yaml' found and will be used.
Using command: podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml

Starting services with Podman. Press Ctrl+C to stop and clean up.
Building images if necessary and starting containers...
```

**Wait for all services to start** (may take 5-10 minutes on first run).

---

### Test 0.3: Container Status Check

```bash
# In a new terminal
podman ps

# Or use podman-compose
cd docs/tutorial-branches/chapter-00-introduction
podman-compose ps
```

**Expected Output:**
```
CONTAINER ID  IMAGE                           STATUS       PORTS
xxxx          localhost/ollama_ch00           Up 2 minutes 0.0.0.0:11434->11434/tcp
yyyy          localhost/agentic_mcp_server_ch00  Up 2 minutes 0.0.0.0:8080->8080/tcp
zzzz          localhost/agentic_streamlit_app_ch00 Up 2 minutes 0.0.0.0:8501->8501/tcp
aaaa          localhost/agentic_jupyterlab_ch00 Up 2 minutes 0.0.0.0:8888->8888/tcp
```

**Pass Criteria:** All 4 containers running with "Up" status.

---

### Test 0.4: Health Checks

```bash
# Test Ollama
curl -f http://localhost:11434/api/version
# Expected: {"version":"x.x.x"}

# Test MCP Server
curl -f http://localhost:8080/health || curl -f http://localhost:8080/
# Expected: 200 OK response

# Test Streamlit
curl -f http://localhost:8501/
# Expected: HTML response with "Streamlit" in content

# Test JupyterLab
curl -f http://localhost:8888/
# Expected: 200 OK or redirect to login page
```

**Pass Criteria:** All endpoints respond successfully (HTTP 200).

---

### Test 0.5: UI Access

**Streamlit:**
1. Open browser to http://localhost:8501
2. Verify Streamlit interface loads
3. Check for no console errors in browser dev tools

**JupyterLab:**
1. Open browser to http://localhost:8888
2. Retrieve token from container logs:
   ```bash
   podman logs agentic_jupyterlab_ch00 2>&1 | grep "token="
   ```
3. Enter token and access JupyterLab interface
4. Navigate to `/work/notebooks` directory

**Pass Criteria:** Both UIs load without errors.

---

### Test 0.6: Functional Test - Ollama

1. In Streamlit UI, select "Ollama" as LLM provider
2. Send query: "What is 2+2?"
3. Verify response is generated

**Pass Criteria:** Ollama responds with coherent answer.

---

### Test 0.7: Functional Test - RAG

1. In Streamlit, upload a CSV file (create simple test file if needed)
2. Use "Add to Vector DB" tool
3. Ask question about the uploaded data
4. Verify RAG retrieves and uses the data

**Pass Criteria:** System successfully stores and retrieves from vector DB.

---

### Test 0.8: Container Logs

```bash
# Check for errors in logs
podman logs agentic_mcp_server_ch00 2>&1 | grep -i error
podman logs agentic_streamlit_app_ch00 2>&1 | grep -i error

# Should return minimal or no error messages
```

**Pass Criteria:** No critical errors in logs.

---

### Test 0.9: Volume Persistence

```bash
# Check that volumes exist
podman volume ls | grep -E "shared_uploads|ollama_data"

# Check bind mount
ls -la ./data
# Should contain SQLite databases and ChromaDB data
```

**Pass Criteria:** Volumes exist and data directory is populated.

---

### Test 0.10: Clean Shutdown

```bash
# Return to terminal running script
# Press Ctrl+C

# Verify cleanup prompts appear
# Answer 'n' to both prune prompts for now
```

**Expected Output:**
```
Caught exit signal. Shutting down and cleaning up...
Stopping and removing containers...
Containers stopped and removed successfully.
Do you want to prune unused Podman networks? (y/N) n
```

**Pass Criteria:** Clean shutdown without errors.

---

### Test 0.11: Verify Cleanup

```bash
# Check containers are stopped
podman ps -a | grep ch00
# Should show no running containers

# Check volumes still exist (for data persistence)
podman volume ls | grep shared_uploads
# Should still exist

# Restart and verify data persists
./start-chapter-resources-podman.sh
# After startup, check if previous RAG data still accessible
```

**Pass Criteria:** Containers stopped, volumes preserved, data persists after restart.

---

## Chapter 1: Main Architecture Tests

### Test Environment

- **Mode:** Rootless
- **Services:** mcp_server, streamlit_app
- **Estimated Time:** 10-15 minutes

### Test 1.1: Service Startup

```bash
cd docs/tutorial-branches/chapter-01-main
./start-chapter-resources-podman.sh
```

**Pass Criteria:** Both services start successfully.

---

### Test 1.2: Container Status

```bash
podman ps

# Expected: 2 containers
# - agentic_mcp_server
# - agentic_streamlit_app
```

**Pass Criteria:** Both containers running.

---

### Test 1.3: MCP Server Tool Registration

```bash
# Test MCP server tools endpoint
curl http://localhost:8080/mcp/tools

# Expected: JSON array of tool definitions
```

**Pass Criteria:** Returns list of available tools including:
- `add_note`
- `search_notes`
- `add_to_vector_db`
- `semantic_search`
- `add_csv_to_sql`
- `query_sql_db`

---

### Test 1.4: Langchain Agent Test

1. Open Streamlit at http://localhost:8501
2. Select OpenAI or another LLM provider
3. Send query: "Create a note titled 'Test' with content 'Hello World'"
4. Verify note is created
5. Send query: "Search for notes containing 'Test'"
6. Verify note is retrieved

**Pass Criteria:** Agent successfully uses MCP tools via Langchain.

---

### Test 1.5: SQL Database Tool

1. Create a test CSV:
   ```bash
   echo "name,age,city
   Alice,30,Seattle
   Bob,25,Portland" > test.csv
   ```
2. Upload via Streamlit
3. Use agent to add to SQL: "Add test.csv to SQL database"
4. Query: "What is the average age in the database?"
5. Verify correct result (27.5)

**Pass Criteria:** SQL operations work through agent.

---

### Test 1.6: Volume Mounts

```bash
# Check data directory
ls -la ./data

# Should contain:
# - notes.db (SQLite for notes)
# - structured_data.db (SQLite for SQL tool)
# - persistent_chroma_db/ (ChromaDB directory)
```

**Pass Criteria:** All expected files/directories exist with proper permissions.

---

### Test 1.7: SELinux Labels (Linux Only)

```bash
# Check SELinux labels on mounted volumes
ls -Z ./data

# Should show container_file_t or similar context
```

**Pass Criteria:** No permission denied errors in logs related to volume access.

---

## Chapter 2: HPC MCP Server Tests

### Test Environment

- **Mode:** Rootless
- **Services:** mcp_server, streamlit_app, hpc_mcp_server
- **Estimated Time:** 15-20 minutes

### Test 2.1: Service Startup

```bash
cd docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot
./start-chapter-resources-podman.sh
```

**Pass Criteria:** All 3 services start successfully.

---

### Test 2.2: HPC Server Health

```bash
# Test HPC MCP server
curl http://localhost:8081/health || curl http://localhost:8081/

# Check tools endpoint
curl http://localhost:8081/mcp/tools
```

**Expected Tools:**
- `run_blast_search`
- `transcribe_audio_whisper`
- `analyze_git_repo_gitxray`

**Pass Criteria:** HPC server responds and lists tools.

---

### Test 2.3: BLAST Database Mount

```bash
# Check BLAST database volume
podman exec agentic_hpc_mcp_server ls -la /blast_databases

# If no databases exist (first run), that's OK
# But directory should be accessible
```

**Pass Criteria:** Directory exists and is accessible from container.

---

### Test 2.4: Whisper Tool Test

1. Find a sample audio file or create test WAV
2. Upload via Streamlit
3. Ask agent: "Transcribe the audio file using Whisper"
4. Verify transcription is returned

**Pass Criteria:** Whisper processes audio and returns transcription.

---

### Test 2.5: GitXRay Tool Test

1. In Streamlit, ask: "Analyze the Git repository at https://github.com/octocat/Hello-World using GitXRay"
2. Verify analysis is returned

**Pass Criteria:** GitXRay analyzes repository and returns summary.

---

### Test 2.6: Multi-Server Communication

```bash
# Verify both MCP servers are accessible from Streamlit
podman exec agentic_streamlit_app curl http://mcp_server:8080/health
podman exec agentic_streamlit_app curl http://hpc_mcp_server:8081/health
```

**Pass Criteria:** Streamlit can reach both MCP servers via internal network.

---

## Chapter 3: LLM Sandbox Tests (Rootful Mode)

### Test Environment

- **Mode:** Rootful (sudo required)
- **Services:** mcp_server, streamlit_app, hpc_mcp_server, sandbox_mcp_server
- **Estimated Time:** 20-25 minutes

### Test 3.1: Rootful Mode Check

```bash
cd docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent

# Attempt to run without sudo (should fail)
./start-chapter-resources-podman.sh
```

**Expected Output:**
```
WARNING: Chapter 3 requires ROOTFUL Podman for sandbox functionality
...
Error: This chapter requires rootful Podman mode.
Please run with: sudo -E ./start-chapter-resources-podman.sh
```

**Pass Criteria:** Script detects non-root execution and exits with instructions.

---

### Test 3.2: Rootful Startup

```bash
# Run with sudo and -E flag
sudo -E ./start-chapter-resources-podman.sh
```

**Expected Prompts:**
1. Rootful warning banner
2. Confirmation prompt: "Continue with rootful Podman? (y/N)"

Type `y` and press Enter.

**Pass Criteria:** Script accepts confirmation and proceeds with startup.

---

### Test 3.3: Privileged Container Check

```bash
# Verify sandbox server is running in privileged mode
sudo podman inspect sandbox_mcp_server | grep -i privileged
# Should show "Privileged": true
```

**Pass Criteria:** Container has privileged mode enabled.

---

### Test 3.4: Podman Socket Mount

```bash
# Verify Podman socket is mounted
sudo podman inspect sandbox_mcp_server | grep podman.sock

# Check if socket is accessible from inside container
sudo podman exec sandbox_mcp_server ls -l /var/run/docker.sock
```

**Pass Criteria:** Socket exists and is accessible from sandbox container.

---

### Test 3.5: Sandbox Server Health

```bash
# Test sandbox server
curl http://localhost:8082/health || curl http://localhost:8082/

# Check tools
curl http://localhost:8082/mcp/tools
```

**Expected Tools:**
- `execute_code_in_sandbox`
- (possibly others depending on implementation)

**Pass Criteria:** Sandbox server responds and lists execution tools.

---

### Test 3.6: Code Execution Test

1. Open Streamlit at http://localhost:8501
2. Ask agent: "Execute this Python code in the sandbox: print('Hello from sandbox')"
3. Verify execution result is returned

**Expected Result:**
```
Output: Hello from sandbox
```

**Pass Criteria:** Code executes successfully in isolated sandbox.

---

### Test 3.7: Sandbox Isolation Test

1. Execute code that attempts file system access:
   ```python
   import os
   print(os.listdir('/'))
   ```
2. Verify limited filesystem is visible (sandbox isolation working)

**Pass Criteria:** Sandbox limits visible filesystem, demonstrating isolation.

---

### Test 3.8: Multi-Agent Functionality

1. Test router-mode multi-agent:
   - Ask: "Use multiple agents to analyze this data and create a report"
   - Verify planner creates plan, supervisor delegates tasks

**Pass Criteria:** Multi-agent orchestration works with all services.

---

### Test 3.9: Rootful Cleanup

```bash
# Press Ctrl+C in terminal running script

# Verify cleanup runs as root
# Check containers stopped
sudo podman ps -a | grep agentic
```

**Pass Criteria:** Clean shutdown with root privileges.

---

### Test 3.10: Security Verification

```bash
# After shutdown, verify rootful Podman isn't accidentally left running services
sudo podman ps

# Should show no running containers
```

**Pass Criteria:** All services stopped, no orphaned rootful containers.

---

## Cross-Chapter Tests

### Test X.1: Chapter Switching

1. Run Chapter 1
2. Stop (Ctrl+C)
3. Run Chapter 2
4. Verify no port conflicts
5. Stop
6. Run Chapter 1 again
7. Verify services restart cleanly

**Pass Criteria:** Can switch between chapters without conflicts.

---

### Test X.2: Parallel Chapter Isolation

```bash
# Start Chapter 1 in one terminal
cd docs/tutorial-branches/chapter-01-main
./start-chapter-resources-podman.sh &

# Start Chapter 0 in another terminal (will fail due to port conflicts)
cd docs/tutorial-branches/chapter-00-introduction
./start-chapter-resources-podman.sh

# Expected: Port conflict error
```

**Pass Criteria:** Script detects port conflicts and reports them clearly.

---

### Test X.3: Data Persistence Across Chapters

1. In Chapter 1, create a note: "Persistence Test"
2. Stop Chapter 1
3. Start Chapter 2
4. Verify the note still exists in `./data/notes.db`
5. Stop Chapter 2
6. Start Chapter 1
7. Search for "Persistence Test" note
8. Verify note is still accessible

**Pass Criteria:** Data persists across chapter restarts.

---

## Performance Benchmarks

### Benchmark 1: Image Build Time

```bash
cd docs/tutorial-branches/chapter-01-main

# Clean build
podman rmi $(podman images | grep agentic | awk '{print $3}')

# Time the build
time podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml build
```

**Expected:**
- First build: 5-10 minutes (depending on network)
- Subsequent builds: 1-2 minutes (cached layers)

**Record:** Build time: _______ minutes

---

### Benchmark 2: Startup Time

```bash
# Time from script start to all containers running
time ./start-chapter-resources-podman.sh &

# In another terminal, monitor until all healthy
watch -n 2 'podman ps | grep agentic'
```

**Expected:**
- Cold start (no images): 10-15 minutes
- Warm start (images cached): 30-60 seconds

**Record:** Startup time: _______ seconds

---

### Benchmark 3: Query Response Time

1. Start Chapter 1
2. In Streamlit, time a simple agent query: "What is 2+2?"
3. Measure from send to response

**Expected:** 1-5 seconds (depending on LLM provider)

**Record:** Response time: _______ seconds

---

## Test Results Matrix

| Test ID | Chapter | Description | Status | Notes |
|---------|---------|-------------|--------|-------|
| 0.1 | 0 | Prerequisites Check | ⬜ |  |
| 0.2 | 0 | Service Startup | ⬜ |  |
| 0.3 | 0 | Container Status | ⬜ |  |
| 0.4 | 0 | Health Checks | ⬜ |  |
| 0.5 | 0 | UI Access | ⬜ |  |
| 0.6 | 0 | Ollama Functional | ⬜ |  |
| 0.7 | 0 | RAG Functional | ⬜ |  |
| 0.8 | 0 | Container Logs | ⬜ |  |
| 0.9 | 0 | Volume Persistence | ⬜ |  |
| 0.10 | 0 | Clean Shutdown | ⬜ |  |
| 0.11 | 0 | Verify Cleanup | ⬜ |  |
| 1.1 | 1 | Service Startup | ⬜ |  |
| 1.2 | 1 | Container Status | ⬜ |  |
| 1.3 | 1 | MCP Tool Registration | ⬜ |  |
| 1.4 | 1 | Langchain Agent | ⬜ |  |
| 1.5 | 1 | SQL Database Tool | ⬜ |  |
| 1.6 | 1 | Volume Mounts | ⬜ |  |
| 1.7 | 1 | SELinux Labels | ⬜ |  |
| 2.1 | 2 | Service Startup | ⬜ |  |
| 2.2 | 2 | HPC Server Health | ⬜ |  |
| 2.3 | 2 | BLAST Database Mount | ⬜ |  |
| 2.4 | 2 | Whisper Tool | ⬜ |  |
| 2.5 | 2 | GitXRay Tool | ⬜ |  |
| 2.6 | 2 | Multi-Server Comm | ⬜ |  |
| 3.1 | 3 | Rootful Mode Check | ⬜ |  |
| 3.2 | 3 | Rootful Startup | ⬜ |  |
| 3.3 | 3 | Privileged Container | ⬜ |  |
| 3.4 | 3 | Podman Socket Mount | ⬜ |  |
| 3.5 | 3 | Sandbox Server Health | ⬜ |  |
| 3.6 | 3 | Code Execution | ⬜ |  |
| 3.7 | 3 | Sandbox Isolation | ⬜ |  |
| 3.8 | 3 | Multi-Agent | ⬜ |  |
| 3.9 | 3 | Rootful Cleanup | ⬜ |  |
| 3.10 | 3 | Security Verification | ⬜ |  |
| X.1 | All | Chapter Switching | ⬜ |  |
| X.2 | All | Parallel Isolation | ⬜ |  |
| X.3 | All | Data Persistence | ⬜ |  |

**Legend:**
- ⬜ Not Tested
- ✅ Pass
- ⚠️ Pass with Issues (note in "Notes" column)
- ❌ Fail (note issue in "Notes" column)

---

## Test Environment Information

Record your test environment details:

```
Date: _______________________
Tester: _____________________

Operating System: ___________
OS Version: _________________
Kernel Version: _____________

Podman Version: _____________
podman-compose Version: _____
Python Version: _____________

CPU: ________________________
RAM: ________________________
Disk: _______________________

SELinux Status: _____________
```

---

## Reporting Issues

When reporting test failures:

1. **Test ID:** Which test failed
2. **Chapter:** Which chapter
3. **Error Message:** Exact error from logs
4. **Container Logs:**
   ```bash
   podman logs <container_name> > container.log
   ```
   Attach relevant portions
5. **Environment:** Fill in test environment section above
6. **Reproduction Steps:** Exact commands that led to failure
7. **Expected vs Actual:** What should have happened vs what did happen

---

## Success Criteria Summary

### Chapter 0
- ✅ All 4 services start and respond to health checks
- ✅ Streamlit and JupyterLab UIs accessible
- ✅ Ollama generates responses
- ✅ RAG operations work (upload, store, retrieve)
- ✅ Data persists across restarts

### Chapter 1
- ✅ Both services start and respond
- ✅ MCP tools registered and accessible
- ✅ Langchain agent executes tool calls
- ✅ Notes and SQL tools functional
- ✅ Volume mounts work with proper permissions

### Chapter 2
- ✅ All 3 services start and respond
- ✅ HPC tools (BLAST, Whisper, GitXRay) accessible
- ✅ Cross-server communication works
- ✅ BLAST database mount accessible
- ✅ Specialized tools execute successfully

### Chapter 3
- ✅ Rootful mode detection and warning works
- ✅ All 4 services start with sudo
- ✅ Privileged mode enabled for sandbox
- ✅ Podman socket mounted correctly
- ✅ Code execution in sandbox works
- ✅ Sandbox isolation verified
- ✅ Multi-agent orchestration functional

---

**Last Updated:** 2025-02-09
**Test Suite Version:** 1.0
**Supported Chapters:** 0-3
