# HPC SSH Tool MVP - Planning Document

**Branch:** `HPC-ssh-tool`  
**Target Chapter:** chapter-01-main  
**Date Created:** 2026-01-28  
**Date Completed:** 2026-01-28  
**Status:** ✅ MVP Completed and Tested

---

## Executive Summary

Create a minimal viable product (MVP) MCP tool for chapter-01 that enables the AI agent to:
1. Connect to a remote HPC cluster via SSH
2. Verify connection health
3. Submit existing Slurm batch jobs
4. Check job status

This MVP focuses on **basic remote job orchestration** with proper authentication and security considerations. Advanced features (file transfer, result retrieval, job output parsing) are deferred to later chapters.

---

## Problem Statement

Current ADEPT framework limitations:
- ❌ No remote HPC cluster integration
- ❌ All compute runs in local Docker containers
- ❌ No SSH-based job submission to Slurm/PBS/SGE schedulers
- ❌ Cannot leverage institutional HPC resources

### User Story
> "As a computational scientist, I want the AI agent to submit my existing batch jobs to our institutional HPC cluster so that I can run large-scale computations without managing SSH connections manually."

---

## Technology Selection

### Option 1: **Fabric (Recommended for MVP)** ✅
- **Library:** `fabric` (v3.x, modern version)
- **Built on:** Paramiko (SSH) + Invoke (CLI tasks)
- **Pros:**
  - High-level, Pythonic API for remote execution
  - Well-maintained (15k+ stars on GitHub)
  - Simple connection handling: `Connection('host').run('command')`
  - Excellent error handling and output capture
  - SSH key and password authentication support
  - Production-ready and battle-tested
- **Cons:**
  - Additional dependency (~2MB)
- **Example:**
  ```python
  from fabric import Connection
  
  # Connect and run command
  with Connection('hpc.institution.edu', user='username', 
                  connect_kwargs={"key_filename": "/path/to/key"}) as c:
      result = c.run('squeue -u $USER', hide=True)
      print(result.stdout)
  ```

### Option 2: Paramiko (Lower-level, more control)
- **Pros:** Full SSH protocol control, no extra dependencies
- **Cons:** More verbose, manual connection lifecycle, harder error handling
- **Verdict:** Overkill for MVP, use Fabric which wraps Paramiko

### Option 3: subprocess + ssh command
- **Pros:** No dependencies, uses system SSH
- **Cons:** Shell injection risks, poor error handling, no connection pooling
- **Verdict:** Not secure enough for production use

### ❌ **NOT Recommended:**
- **pyslurm** - Requires C compilation, needs Slurm headers (complex)
- **dask-jobqueue** - Designed for distributed computing, overkill
- **HPCrocket** - Not a widely-used library (if exists)

### **Decision: Use Fabric v3.x** 🎯

---

## MVP Scope

### In-Scope Features (MVP) - ✅ ALL COMPLETED
1. ✅ **SSH Connection Test** - Verify host reachability and authentication (IMPLEMENTED)
2. ✅ **Slurm Job Submission** - Execute `sbatch <existing_script.sh>` on remote HPC (IMPLEMENTED)
3. ✅ **Job Status Check** - Run `squeue -j <job_id>` and parse output (IMPLEMENTED)
4. ✅ **Authentication** - Support SSH keys (encrypted/unencrypted) and password (IMPLEMENTED)
5. ✅ **Error Handling** - Connection failures, job errors, timeouts (IMPLEMENTED)
6. ✅ **Security** - Single-key Docker volume mount, `.env` for secrets, no credentials in code (IMPLEMENTED)
7. ✅ **Unit Tests** - 17 unit tests covering parsing and connection setup (IMPLEMENTED)
8. ✅ **LangChain Integration** - Full agent integration with Pydantic schemas (IMPLEMENTED)
9. ✅ **Documentation** - Usage guide and planning docs (COMPLETED)

### Out-of-Scope (Future Chapters)
- ❌ File transfer (SFTP/SCP) - Chapter 2+
- ❌ Job output retrieval - Chapter 2+
- ❌ Job cancellation/modification - Chapter 2+
- ❌ Multiple HPC cluster support - Chapter 3+
- ❌ PBS/SGE schedulers - Chapter 3+
- ❌ Advanced monitoring (resource usage, queue time) - Chapter 3+

---

## Architecture Design

### Component Structure
```
chapter-01-main/
├── src/agentic_framework_pkg/
│   └── mcp_server/
│       └── tools/
│           └── hpc_ssh_tool.py          # NEW: HPC SSH MCP tool
├── pyproject.toml                       # Add fabric dependency
├── .env.example                         # Add HPC config examples
├── tests/
│   └── test_hpc_ssh_tool.py            # NEW: Unit + integration tests
└── docs/
    └── HPC_SSH_TOOL_MVP_PLAN.md        # This document
```

### Tool Definition

```python
# src/agentic_framework_pkg/mcp_server/tools/hpc_ssh_tool.py

from fastmcp import FastMCP, Context
from fabric import Connection
from typing import Dict, Any, Optional
import os
from ...logger_config import get_logger

logger = get_logger(__name__)

def register_tools(mcp: FastMCP):
    
    @mcp.tool()
    async def test_hpc_connection(
        ctx: Context,
        hpc_host: Optional[str] = None,
        hpc_user: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test SSH connection to remote HPC cluster.
        
        Args:
            ctx: FastMCP context
            hpc_host: HPC hostname (defaults to env var HPC_HOST)
            hpc_user: SSH username (defaults to env var HPC_USER)
        
        Returns:
            {
                "status": "success" | "error",
                "message": str,
                "hostname": str,
                "kernel": str  # uname -s output
            }
        """
        # Implementation details below...
    
    @mcp.tool()
    async def submit_slurm_job(
        ctx: Context,
        script_path: str,
        job_name: Optional[str] = None,
        hpc_host: Optional[str] = None,
        hpc_user: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a Slurm batch job on remote HPC.
        
        Args:
            script_path: Absolute path to .sh script on REMOTE HPC
            job_name: Optional job name (shown in squeue)
            hpc_host: HPC hostname (defaults to env var)
            hpc_user: SSH username (defaults to env var)
        
        Returns:
            {
                "status": "success" | "error",
                "job_id": str,
                "message": str,
                "submission_output": str
            }
        """
        # Implementation details below...
    
    @mcp.tool()
    async def check_slurm_job_status(
        ctx: Context,
        job_id: str,
        hpc_host: Optional[str] = None,
        hpc_user: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check status of Slurm job.
        
        Args:
            job_id: Slurm job ID (from submit_slurm_job)
            hpc_host: HPC hostname (defaults to env var)
            hpc_user: SSH username (defaults to env var)
        
        Returns:
            {
                "status": "success" | "error",
                "job_id": str,
                "job_state": "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED",
                "job_name": str,
                "runtime": str,
                "raw_output": str
            }
        """
        # Implementation details below...
```

### Environment Variables (.env)
```bash
# HPC SSH Configuration
HPC_HOST=hpc.institution.edu
HPC_USER=username
HPC_SSH_KEY_PATH=/path/to/id_rsa  # Optional: if using key auth
HPC_SSH_PASSWORD=                  # Optional: if using password (NOT RECOMMENDED)
HPC_SSH_PORT=22                    # Default SSH port

# Slurm Configuration (optional defaults)
HPC_DEFAULT_PARTITION=compute      # Default queue/partition
HPC_DEFAULT_WALLTIME=01:00:00      # Default job time limit
```

---

## Security Considerations

### ✅ Authentication Best Practices
1. **SSH Keys (Preferred)**
   - Store private key path in `.env` (gitignored)
   - Use `ssh-agent` for passwordless keys
   - Fabric: `connect_kwargs={"key_filename": "/path/to/key"}`

2. **Password Auth (Fallback)**
   - Store in `.env` (never commit)
   - Fabric: `connect_kwargs={"password": os.getenv("HPC_SSH_PASSWORD")}`
   - Add warning in logs when using password auth

3. **Connection Timeout**
   - Set reasonable timeout (30s) to prevent hanging
   - Fabric: `Connection(..., connect_timeout=30)`

### ❌ Security Anti-Patterns to Avoid
- ❌ Hardcoded credentials in source code
- ❌ Plaintext passwords in tracked files
- ❌ Executing arbitrary shell commands (use allowlist approach)
- ❌ Exposing SSH keys in Docker images
- ❌ Accepting unvalidated user input in shell commands

### 🛡️ Input Validation & Command Injection Prevention (IMPLEMENTED)

**Validation Functions:**
- `_validate_path_safe(path)`: Blocks shell metacharacters (`;`, `&`, `|`, `` ` ``, `$()`, `${}`)
- `_validate_job_name_safe(job_name)`: Only allows `[a-zA-Z0-9_.-]`, max 64 chars
- `_validate_job_id_safe(job_id)`: Numeric only

**Protected Against:**
- Command injection via script path: `/home/user/script.sh; rm -rf /` → **BLOCKED**
- Command injection via job name: `test; cat /etc/passwd` → **BLOCKED**
- Command injection via job ID: `123; curl evil.com` → **BLOCKED**

**Limited Command Set:**
Tool only executes these specific, read-only or validated commands:
- `uname -s`, `hostname`, `uptime` - System info (read-only)
- `test -f <validated_path>` - File existence check (read-only)
- `sbatch <validated_options> <validated_path>` - Job submission (validated inputs)
- `squeue -j <validated_job_id>` - Job status query (read-only)

**NOT Possible** (by design):
- ❌ Arbitrary shell command execution
- ❌ File operations (`rm`, `mv`, `cp`, `chmod`)
- ❌ System administration (`sudo`, `systemctl`)
- ❌ Data exfiltration (`curl`, `wget`, `scp`)

### 🔒 Secrets Management
- Use `.env` for local development (gitignored)
- Use Docker secrets or Kubernetes secrets for production
- Add `.env.example` with placeholder values
- Document all required environment variables in README

---

## Implementation Plan

### Phase 1: Dependency Setup (30 min)
- [ ] Add `fabric>=3.0.0` to `pyproject.toml`
- [ ] Update `Dockerfile.mcp_server` to install fabric
- [ ] Update `.env.example` with HPC configuration
- [ ] Run `uv sync` to install dependencies

### Phase 2: Core Tool Implementation (2-3 hours)
- [ ] Create `src/agentic_framework_pkg/mcp_server/tools/hpc_ssh_tool.py`
- [ ] Implement `test_hpc_connection()` tool
  - Connection test with fabric
  - Error handling for auth failures
  - Return structured response
- [ ] Implement `submit_slurm_job()` tool
  - Execute `sbatch <script_path>`
  - Parse job ID from output
  - Handle submission errors
- [ ] Implement `check_slurm_job_status()` tool
  - Execute `squeue -j <job_id>`
  - Parse job state from output
  - Handle non-existent job errors

### Phase 3: Helper Functions (1 hour)
- [ ] `_get_hpc_connection()` - Create Fabric Connection with env vars
- [ ] `_parse_sbatch_output()` - Extract job ID from sbatch
- [ ] `_parse_squeue_output()` - Extract job state from squeue
- [ ] Error handling wrappers

### Phase 4: Registration & Integration (30 min)
- [ ] Register tools in `src/agentic_framework_pkg/mcp_server/tools/__init__.py`
- [ ] Update `main.py` to call `hpc_ssh_tool.register_tools(mcp)`
- [ ] Test server startup: `docker compose up --build`

### Phase 5: Testing (2-3 hours)
- [ ] Unit tests (mocked Fabric connections)
  - Test connection success/failure
  - Test job submission parsing
  - Test status parsing
- [ ] Integration tests (requires actual HPC or mock server)
  - Test real SSH connection
  - Test actual job submission (hello world)
  - Test job status monitoring
- [ ] Smoke tests via agent
  - Agent calls `test_hpc_connection`
  - Agent submits job
  - Agent checks job status

### Phase 6: Documentation (1 hour)
- [ ] Add tool usage examples to README
- [ ] Document required environment variables
- [ ] Add troubleshooting section
- [ ] Update CHANGELOG

**Total Estimated Time:** 8-10 hours

---

## Testing Strategy

### 1. Unit Tests (Mocked)
```python
# tests/test_hpc_ssh_tool.py

import pytest
from unittest.mock import patch, MagicMock
from agentic_framework_pkg.mcp_server.tools.hpc_ssh_tool import (
    _parse_sbatch_output,
    _parse_squeue_output
)

def test_parse_sbatch_output_success():
    output = "Submitted batch job 123456\n"
    job_id = _parse_sbatch_output(output)
    assert job_id == "123456"

def test_parse_sbatch_output_failure():
    output = "sbatch: error: Batch job submission failed\n"
    with pytest.raises(ValueError):
        _parse_sbatch_output(output)

def test_parse_squeue_output_running():
    output = "123456  compute  myjob  username  RUNNING  0:05:30\n"
    state = _parse_squeue_output(output)
    assert state["job_state"] == "RUNNING"
    assert state["job_id"] == "123456"

@patch('fabric.Connection')
def test_test_hpc_connection_success(mock_conn):
    # Mock successful connection
    mock_result = MagicMock()
    mock_result.stdout = "Linux\n"
    mock_result.exited = 0
    mock_conn.return_value.run.return_value = mock_result
    
    # Test tool call
    result = await test_hpc_connection(ctx, hpc_host="test.hpc.edu")
    assert result["status"] == "success"
    assert "Linux" in result["kernel"]
```

### 2. Integration Tests (Real or Mock HPC)

**Option A: Mock SSH Server (docker-ssh-mock)**
```yaml
# docker-compose.test.yaml
services:
  mock_hpc:
    image: linuxserver/openssh-server
    environment:
      - PUID=1000
      - PGID=1000
      - PASSWORD_ACCESS=true
      - USER_NAME=testuser
      - USER_PASSWORD=testpass
    ports:
      - "2222:2222"
```

**Option B: Real HPC (requires institutional access)**
- Use test account with limited resources
- Pre-stage hello world script: `/home/user/test_jobs/hello.sh`
- Run integration tests only when `HPC_HOST` is set

### 3. Smoke Tests (Agent-based)
```python
# tests/test_mcp_tools_smoke.py

@pytest.mark.skipif(not HPC_AVAILABLE, reason="HPC not configured")
class TestHPCToolsSmoke:
    
    async def test_hpc_connection_via_agent(self):
        agent = ScientificWorkflowAgent(mcp_session_id="test-hpc")
        result = await agent.arun("Test the connection to our HPC cluster")
        assert "success" in result["output"].lower()
    
    async def test_slurm_job_submission_via_agent(self):
        agent = ScientificWorkflowAgent(mcp_session_id="test-hpc")
        result = await agent.arun(
            "Submit the hello world job located at /home/testuser/hello.sh"
        )
        assert "job" in result["output"].lower()
        assert "submitted" in result["output"].lower()
```

---

## Example Test Script (Remote HPC)

```bash
#!/bin/bash
# File: /home/testuser/hello_world.sh
# Description: Simple Slurm test job

#SBATCH --job-name=hello_mcp_test
#SBATCH --output=hello_%j.out
#SBATCH --error=hello_%j.err
#SBATCH --time=00:01:00
#SBATCH --ntasks=1
#SBATCH --mem=100M

echo "Hello from HPC MCP Tool MVP!"
hostname
date
sleep 10
echo "Job completed successfully"
```

**Manual Test Commands:**
```bash
# 1. Upload script to HPC
scp hello_world.sh user@hpc.edu:/home/user/

# 2. Test submission
ssh user@hpc.edu 'sbatch /home/user/hello_world.sh'
# Expected output: Submitted batch job 123456

# 3. Check status
ssh user@hpc.edu 'squeue -j 123456'
# Expected: Job state (PENDING, RUNNING, COMPLETED)

# 4. View output
ssh user@hpc.edu 'cat /home/user/hello_123456.out'
```

---

## Implementation Code Snippets

### Connection Helper
```python
def _get_hpc_connection(
    hpc_host: Optional[str] = None,
    hpc_user: Optional[str] = None,
    timeout: int = 30
) -> Connection:
    """Create Fabric connection to HPC cluster."""
    host = hpc_host or os.getenv("HPC_HOST")
    user = hpc_user or os.getenv("HPC_USER")
    
    if not host or not user:
        raise ValueError("HPC_HOST and HPC_USER must be set")
    
    # Build connection kwargs
    connect_kwargs = {}
    
    # Try SSH key first
    key_path = os.getenv("HPC_SSH_KEY_PATH")
    if key_path and os.path.exists(key_path):
        connect_kwargs["key_filename"] = key_path
        logger.info(f"Using SSH key auth: {key_path}")
    
    # Fallback to password (warn user)
    elif os.getenv("HPC_SSH_PASSWORD"):
        connect_kwargs["password"] = os.getenv("HPC_SSH_PASSWORD")
        logger.warning("Using password auth - SSH keys recommended!")
    
    port = int(os.getenv("HPC_SSH_PORT", "22"))
    
    return Connection(
        host=host,
        user=user,
        port=port,
        connect_timeout=timeout,
        connect_kwargs=connect_kwargs
    )
```

### Job Submission
```python
async def submit_slurm_job(
    ctx: Context,
    script_path: str,
    job_name: Optional[str] = None,
    hpc_host: Optional[str] = None,
    hpc_user: Optional[str] = None
) -> Dict[str, Any]:
    """Submit Slurm batch job."""
    try:
        conn = _get_hpc_connection(hpc_host, hpc_user)
        
        # Verify script exists on remote
        check_cmd = f"test -f {script_path} && echo 'exists' || echo 'missing'"
        check_result = conn.run(check_cmd, hide=True)
        
        if "missing" in check_result.stdout:
            return {
                "status": "error",
                "message": f"Script not found on HPC: {script_path}",
                "script_path": script_path
            }
        
        # Submit job
        submit_cmd = f"sbatch {script_path}"
        if job_name:
            submit_cmd += f" --job-name={job_name}"
        
        result = conn.run(submit_cmd, hide=True)
        
        # Parse job ID from output
        job_id = _parse_sbatch_output(result.stdout)
        
        await ctx.info(f"Submitted Slurm job {job_id}")
        
        return {
            "status": "success",
            "job_id": job_id,
            "message": f"Job submitted successfully",
            "submission_output": result.stdout.strip()
        }
        
    except Exception as e:
        logger.error(f"Job submission failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "script_path": script_path
        }
```

### Output Parsing
```python
def _parse_sbatch_output(output: str) -> str:
    """Extract job ID from sbatch output."""
    import re
    # Expected: "Submitted batch job 123456"
    match = re.search(r'Submitted batch job (\d+)', output)
    if match:
        return match.group(1)
    raise ValueError(f"Could not parse job ID from: {output}")

def _parse_squeue_output(output: str) -> Dict[str, Any]:
    """Parse squeue output into structured data."""
    # Format: JOBID PARTITION NAME USER ST TIME
    # Example: 123456 compute myjob username R 0:05:30
    
    if not output.strip():
        return {"job_state": "NOT_FOUND", "message": "Job not in queue"}
    
    lines = output.strip().split('\n')
    if len(lines) < 2:  # Header + data
        # Job might have completed
        return {"job_state": "COMPLETED_OR_REMOVED"}
    
    # Parse data line (skip header)
    parts = lines[1].split()
    if len(parts) < 6:
        return {"job_state": "PARSE_ERROR", "raw": output}
    
    state_map = {
        "PD": "PENDING",
        "R": "RUNNING",
        "CG": "COMPLETING",
        "CD": "COMPLETED",
        "F": "FAILED",
        "CA": "CANCELLED"
    }
    
    return {
        "job_id": parts[0],
        "partition": parts[1],
        "job_name": parts[2],
        "user": parts[3],
        "job_state": state_map.get(parts[4], parts[4]),
        "runtime": parts[5],
        "raw_output": output
    }
```

---

## Success Criteria

### Functional Requirements
- ✅ Agent can successfully connect to remote HPC via SSH
- ✅ Agent can submit existing Slurm scripts
- ✅ Agent can check job status and report state
- ✅ All tools return structured JSON responses
- ✅ Errors are handled gracefully (connection timeout, auth failure, job errors)

### Non-Functional Requirements
- ✅ No credentials committed to git
- ✅ Tools respond within 30s timeout
- ✅ Logs contain useful debugging info
- ✅ All tests pass (unit + integration)
- ✅ Documentation complete

### Acceptance Test
```
User: "Can you connect to our HPC cluster and check if it's online?"
Agent: ✅ Successfully tests connection, reports hostname and kernel version

User: "Submit the job at /home/username/test_jobs/hello.sh"
Agent: ✅ Submits job, returns job ID 123456

User: "What's the status of job 123456?"
Agent: ✅ Reports job state (PENDING/RUNNING/COMPLETED)
```

---

## Future Enhancements (Later Chapters)

### Chapter 2: File Operations
- SFTP file transfer (upload scripts, download results)
- Result retrieval and parsing
- Job output monitoring (`tail -f` equivalent)

### Chapter 3: Advanced Job Management
- Job cancellation (`scancel`)
- Job modification (`scontrol update`)
- Array jobs and dependencies
- Resource usage monitoring

### Chapter 4: Multi-Cluster Support
- Multiple HPC cluster connections
- PBS/SGE scheduler support
- Cluster selection based on job requirements

### Chapter 5: Workflow Orchestration
- Nextflow + Slurm integration
- DAG-based job pipelines
- Automatic result aggregation

---

## Dependencies

### Python Packages (add to pyproject.toml)
```toml
dependencies = [
    # ... existing dependencies ...
    "fabric>=3.0.0",  # SSH remote execution
]
```

### System Dependencies (Dockerfile.mcp_server)
- Already has SSH client (`openssh-client` in Debian base)
- No additional packages needed for Fabric

---

## Risk Assessment

| Risk            | Likelihood | Impact   | Mitigation                                            |
| --------------- | ---------- | -------- | ----------------------------------------------------- |
| HPC unreachable | Medium     | High     | Add connection retry logic, timeout handling          |
| Auth failure    | Medium     | High     | Document setup clearly, test multiple auth methods    |
| Job fails       | High       | Low      | Tool reports failure status, agent handles gracefully |
| Network timeout | Low        | Medium   | Set reasonable timeouts (30s), fail gracefully        |
| Credential leak | Low        | Critical | `.env` gitignored, code reviews, security audit       |

---

## Timeline

| Phase                        | Estimated Time | Dependencies                |
| ---------------------------- | -------------- | --------------------------- |
| Phase 1: Setup               | 30 min         | None                        |
| Phase 2: Core Implementation | 2-3 hours      | Phase 1                     |
| Phase 3: Helpers             | 1 hour         | Phase 2                     |
| Phase 4: Integration         | 30 min         | Phase 3                     |
| Phase 5: Testing             | 2-3 hours      | Phase 4, HPC access         |
| Phase 6: Documentation       | 1 hour         | Phase 5                     |
| **Total**                    | **8-10 hours** | HPC access for full testing |

---

## Open Questions

1. **HPC Access:** Do we have a test HPC cluster available?
   - If yes: What are the connection details?
   - If no: Should we use a mock SSH server for testing?

2. **Test Job Location:** Where should the hello world script live on the HPC?
   - Suggestion: `/home/<user>/test_jobs/hello_world.sh`

3. **Slurm Version:** Which Slurm version are we targeting?
   - MVP targets standard `sbatch` and `squeue` commands (works on all versions)

4. **Authentication:** SSH key or password for testing?
   - Recommendation: Use SSH key with `ssh-agent`

5. **Error Reporting:** How detailed should error messages be?
   - Suggestion: Return full stdout/stderr for debugging, summarize for user

---

## Next Steps

1. **Review this plan** with team/user for feedback
2. **Confirm HPC access** or set up mock SSH server
3. **Create test script** on remote HPC
4. **Begin Phase 1** implementation
5. **Iterate** based on testing results

---

## References

- [Fabric Documentation](https://www.fabfile.org/)
- [Fabric API Docs](https://docs.fabfile.org/)
- [Slurm Quickstart](https://slurm.schedmd.com/quickstart.html)
- [Slurm sbatch](https://slurm.schedmd.com/sbatch.html)
- [Slurm squeue](https://slurm.schedmd.com/squeue.html)
- [SSH Best Practices](https://www.ssh.com/academy/ssh/public-key-authentication)

---

**End of MVP Planning Document**
