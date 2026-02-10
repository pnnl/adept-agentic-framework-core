# Podman Deployment Testing Guide

## Overview

This document describes the comprehensive test suite for validating Podman deployments of the ADEPT framework across all chapters (0-3).

## Test Suite Components

### 1. Comprehensive Test Suite (`test-podman-deployment.sh`)

**Location:** `tests/podman/`
**Purpose:** Full validation of Podman deployment with detailed reporting
**Runtime:** 2-5 minutes depending on chapter

**Features:**
- ✅ Prerequisites validation (Podman, podman-compose, Python)
- ✅ Environment setup verification
- ✅ Chapter-specific configuration tests
- ✅ Container health checks
- ✅ Endpoint accessibility tests
- ✅ Log analysis for critical errors
- ✅ Network configuration validation
- ✅ Image availability checks
- ✅ Structured test reporting with pass/fail/skip counts
- ✅ Detailed log file generation

**Usage:**
```bash
# Test all chapters
sudo ./tests/podman/test-podman-deployment.sh

# Test specific chapter
sudo ./tests/podman/test-podman-deployment.sh 0  # Chapter 0
sudo ./tests/podman/test-podman-deployment.sh 1  # Chapter 1
sudo ./tests/podman/test-podman-deployment.sh 2  # Chapter 2
sudo ./tests/podman/test-podman-deployment.sh 3  # Chapter 3

# Show help
sudo ./tests/podman/test-podman-deployment.sh --help
```

**Output:**
- Color-coded results (green=pass, red=fail, yellow=skip)
- Section-based organization
- Summary statistics
- Failed test details
- Test log file: `test-results-YYYYMMDD-HHMMSS.log`

---

### 2. Quick Smoke Test (`quick-test.sh`)

**Location:** Project root
**Purpose:** Fast validation for rapid feedback
**Runtime:** < 10 seconds

**Tests:**
- Container status (running vs stopped)
- Critical errors in recent logs
- Basic endpoint accessibility

**Usage:**
```bash
# Quick test Chapter 0
./tests/podman/quick-test.sh 0

# Quick test Chapter 1
./tests/podman/quick-test.sh 1
```

**When to use:**
- After making configuration changes
- Before committing code
- During iterative development
- When you need fast feedback

---

### 3. Chapter-Specific Helper Scripts

Located in each chapter directory (e.g., `chapter-00-introduction/`):

#### `check-service-logs.sh`
**Purpose:** Cross-reference logs with error highlighting

**Modes:**
- `summary` - Show only errors and warnings
- `full [N]` - Show last N lines from each service
- `follow` - Live tail all services
- `health` - Check HTTP endpoints

**Usage:**
```bash
cd docs/tutorial-branches/chapter-00-introduction
sudo ./check-service-logs.sh summary
sudo ./check-service-logs.sh health
```

#### `verify-services.sh`
**Purpose:** Comprehensive health verification for one chapter

**Checks:**
- Container status
- HTTP/HTTPS endpoints
- Database files
- Directory permissions

**Usage:**
```bash
cd docs/tutorial-branches/chapter-00-introduction
sudo ./verify-services.sh
```

---

## Test Categories

### Category 1: Prerequisites
Tests system requirements before deployment:
- Podman installation and version
- podman-compose availability
- Python version (3.9+)
- Podman service accessibility
- Registry configuration

### Category 2: Environment Setup
Validates project configuration:
- Project directory structure
- Podman virtual environment
- Bootstrap scripts
- Configuration scripts

### Category 3: Chapter Configuration
Tests chapter-specific setup:
- Required files present (docker-compose.yaml, overlays, scripts)
- YAML syntax validation
- SELinux label removal verification
- Permission fix functions present
- DATABASE_URL configuration (Chapter 0)

### Category 4: Runtime Validation
Tests running deployments:
- Container status (running vs stopped)
- Log analysis for critical errors
- Endpoint accessibility (HTTP/HTTPS)
- Service-to-service connectivity

### Category 5: Networking
Validates container networking:
- Bridge networks exist
- Network inspection passes
- Service name DNS resolution

### Category 6: Images
Checks container images:
- Required images pulled
- Image availability

---

## Test Results Interpretation

### Pass ✓
Test completed successfully. No action needed.

### Fail ✗
Test failed. Review the error output and refer to troubleshooting guides.

Common failures:
- **DATABASE_URL wrong**: Chapter 0 requires SQLite, not PostgreSQL
- **Permission errors**: Run `chmod 777 data/` in chapter directory
- **Endpoint not responding**: Check if service crashed with `podman logs`
- **Registry errors**: Run `sudo ./configure-podman-registries.sh`

### Skip ⊘
Test skipped because precondition not met (e.g., containers not running).
Not an error - just informational.

---

## Testing Workflow

### 1. Fresh Deployment Testing

```bash
# Step 1: Run prerequisites
sudo ./tests/podman/test-podman-deployment.sh 0  # Test Chapter 0 only

# Step 2: If fails, review errors
cat test-results-*.log | grep "FAIL:"

# Step 3: Fix issues and retest
sudo ./tests/podman/test-podman-deployment.sh 0
```

### 2. Rapid Development Testing

```bash
# Make changes to configuration
vim docs/tutorial-branches/chapter-00-introduction/docker-compose.podman.yaml

# Quick validation
./tests/podman/quick-test.sh 0

# If pass, run full suite
sudo ./tests/podman/test-podman-deployment.sh 0
```

### 3. Multi-Chapter Testing

```bash
# Test all chapters at once
sudo ./tests/podman/test-podman-deployment.sh all

# Review summary
# Deploy next chapter if previous passed
```

---

## Chapter-Specific Tests

### Chapter 0: Introduction
**Services:** ollama, mcp_server, streamlit_app, jupyterlab
**Endpoints:** 11434 (Ollama), 8080 (MCP), 8501 (Streamlit SSL), 8888 (JupyterLab)

**Special Tests:**
- DATABASE_URL must be SQLite (not PostgreSQL)
- `.env` file configuration validation
- Data directory permissions (chmod 777)
- ChromaDB directory accessibility

**Common Issues:**
- ModuleNotFoundError: asyncpg → DATABASE_URL set to PostgreSQL
- Permission denied: ChromaDB → Run chmod 777 data/
- Streamlit connection error → MCP server crashed, check logs

### Chapter 1: Main Architecture
**Services:** mcp_server, streamlit_app
**Endpoints:** 8080 (MCP), 8501 (Streamlit)

**Special Tests:**
- No DATABASE_URL checks (uses env vars)
- Simpler deployment (fewer services)

### Chapter 2: HPC MCP Server
**Services:** mcp_server, streamlit_app, hpc_mcp_server
**Endpoints:** 8080 (MCP), 8081 (HPC MCP), 8501 (Streamlit)

**Special Tests:**
- HPC server endpoint accessibility
- BLAST database directory permissions

### Chapter 3: Sandbox and Multi-Agent
**Services:** mcp_server, streamlit_app, hpc_mcp_server, sandbox_mcp_server
**Endpoints:** 8080 (MCP), 8081 (HPC MCP), 8082 (Sandbox), 8501 (Streamlit)

**Special Tests:**
- Sandbox requires rootful Podman (ALL users)
- Podman socket accessibility
- Privileged container validation

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Podman Deployment

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Podman
        run: |
          sudo apt-get update
          sudo apt-get install -y podman podman-compose

      - name: Configure registries
        run: sudo ./configure-podman-registries.sh

      - name: Bootstrap environment
        run: ./bootstrap-podman-env.sh

      - name: Test Chapter 0
        run: sudo ./tests/podman/test-podman-deployment.sh 0

      - name: Upload test logs
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results-*.log
```

---

## Troubleshooting Test Failures

### Test: "Registry configured"
**Failure:** registries.conf not found or doesn't contain docker.io

**Fix:**
```bash
sudo ./configure-podman-registries.sh
```

### Test: "Container X running"
**Failure:** Container not found or stopped

**Fix:**
```bash
# Check container status
sudo podman ps -a

# Check logs for errors
sudo podman logs <container_name>

# Restart chapter
cd docs/tutorial-branches/chapter-XX-name
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

### Test: "Container X has no critical errors"
**Failure:** Critical errors found in logs

**Fix:**
```bash
# View full logs
sudo podman logs <container_name> | less

# Check for specific issues:
# - ModuleNotFoundError: asyncpg → DATABASE_URL issue
# - Permission denied → chmod 777 data/
# - Connection refused → Check network/depends_on
```

### Test: "DATABASE_URL uses SQLite"
**Failure:** .env configured for PostgreSQL

**Fix:**
```bash
# Edit .env file
vim docs/tutorial-branches/chapter-00-introduction/.env

# Change line 266 to:
DATABASE_URL=sqlite+aiosqlite:///./data/agentic_framework.db

# Restart services
cd docs/tutorial-branches/chapter-00-introduction
sudo env "PATH=$PATH" podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml down
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

---

## Test Coverage Matrix

| Test Category | Ch 0 | Ch 1 | Ch 2 | Ch 3 | Notes |
|---------------|------|------|------|------|-------|
| Prerequisites | ✓ | ✓ | ✓ | ✓ | System-wide |
| Environment | ✓ | ✓ | ✓ | ✓ | Project-wide |
| Config Files | ✓ | ✓ | ✓ | ✓ | Chapter-specific |
| Container Status | ✓ | ✓ | ✓ | ✓ | If running |
| Log Analysis | ✓ | ✓ | ✓ | ✓ | If running |
| Endpoint Tests | ✓ | ✓ | ✓ | ✓ | If running |
| DATABASE_URL | ✓ | - | - | - | Ch 0 only |
| Permissions | ✓ | ✓ | ✓ | ✓ | data/ directories |
| Networking | ✓ | ✓ | ✓ | ✓ | Bridge networks |
| Images | ✓ | ✓ | ✓ | ✓ | If pulled |

---

## Best Practices

1. **Run tests after configuration changes**
   ```bash
   sudo ./tests/podman/test-podman-deployment.sh <chapter>
   ```

2. **Use quick test for rapid iteration**
   ```bash
   ./tests/podman/quick-test.sh <chapter>
   ```

3. **Review logs when tests fail**
   ```bash
   cat test-results-*.log | grep -A 5 "FAIL:"
   ```

4. **Test one chapter at a time initially**
   - Fix Chapter 0 completely before moving to Chapter 1
   - Verify all tests pass before proceeding

5. **Keep test logs for debugging**
   ```bash
   # Archive successful test runs
   mkdir -p test-logs/
   mv test-results-*.log test-logs/
   ```

6. **Run full suite before commits**
   ```bash
   sudo ./tests/podman/test-podman-deployment.sh all
   ```

---

## Future Enhancements

- [ ] Integration tests (test actual tool calls, not just endpoints)
- [ ] Performance benchmarking
- [ ] Resource usage monitoring
- [ ] Automated recovery from failures
- [ ] Parallel test execution
- [ ] Test result dashboard
- [ ] Comparison with Docker deployment

---

## References

- [PODMAN_IMPLEMENTATION_PROGRESS.md](PODMAN_IMPLEMENTATION_PROGRESS.md) - Implementation tracking
- [PODMAN_BUGFIX_PROCESS.md](PODMAN_BUGFIX_PROCESS.md) - Bugfix methodology
- [TROUBLESHOOTING.md](../docs/tutorial-branches/chapter-00-introduction/TROUBLESHOOTING.md) - Chapter 0 troubleshooting
- [test-podman-deployment.sh](../tests/podman/test-podman-deployment.sh) - Main test script
- [tests/README.md](../tests/README.md) - Test suite overview
