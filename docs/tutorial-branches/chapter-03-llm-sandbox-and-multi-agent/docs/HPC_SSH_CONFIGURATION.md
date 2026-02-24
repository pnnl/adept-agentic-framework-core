# HPC SSH Configuration Guide

## Quick Setup

### 1. Configure Your `.env` File

Copy `.env.example` to `.env` and configure:

```bash
# Required: HPC cluster connection details
HPC_HOST="hpc.institution.edu"          # Your HPC cluster hostname
HPC_USER="your_username"                 # Your SSH username
HPC_SSH_PORT=22                          # SSH port (usually 22)

# SSH Key Authentication (RECOMMENDED)
HPC_SSH_KEY_PATH_HOST="/Users/yourusername/.ssh/hpc_key.pem"  # Path on YOUR machine

# Optional: If key is password-protected
# HPC_SSH_KEY_PASSPHRASE="your_passphrase"

# Alternative: Password auth (NOT RECOMMENDED)
# HPC_SSH_PASSWORD="your_password"
```

### 2. Ensure Your SSH Key Exists

```bash
# Verify key exists on your machine
ls -la /Users/yourusername/.ssh/hpc_key.pem

# Ensure proper permissions (SSH requires this)
chmod 600 /Users/yourusername/.ssh/hpc_key.pem
```

### 3. Build and Start Services

```bash
# Build with new SSH configuration
docker compose build hpc_mcp_server

# Start all services
./start-chapter-resources.sh
# OR
docker compose up -d
```

### 4. Test the Connection

Via Streamlit UI:
- Navigate to http://localhost:8501
- Ask: "Test the SSH connection to the HPC cluster"

Via pytest:
```bash
uv run pytest tests/test_mcp_tools_smoke.py::TestHPCSSHToolsSmoke -v
```

## How SSH Key Mounting Works

### The Flow

1. **Your Machine (Host)**
   - You have an SSH private key at: `/Users/you/.ssh/hpc_key.pem`
   - You set in `.env`: `HPC_SSH_KEY_PATH_HOST="/Users/you/.ssh/hpc_key.pem"`

2. **Docker Volume Mount** (in `docker-compose.yaml`)
   ```yaml
   volumes:
     - ${HPC_SSH_KEY_PATH_HOST:-/dev/null}:/home/appuser/.ssh/hpc_key:ro
   ```
   - Mounts your host key → `/home/appuser/.ssh/hpc_key` inside container
   - `:ro` = read-only for security

3. **Container Environment** (in `docker-compose.yaml`)
   ```yaml
   environment:
     - HPC_SSH_KEY_PATH=/home/appuser/.ssh/hpc_key
   ```
   - Tells the Python tool where to find the mounted key

4. **Python Tool** (`hpc_ssh_tool.py`)
   ```python
   key_path = os.getenv("HPC_SSH_KEY_PATH")  # Gets /home/appuser/.ssh/hpc_key
   if key_path and os.path.exists(key_path):
       connect_kwargs["key_filename"] = key_path
   ```
   - Reads the mounted key and uses it for SSH authentication

### Environment Variables Summary

| Variable                | Set In                            | Purpose                    | Example                       |
| ----------------------- | --------------------------------- | -------------------------- | ----------------------------- |
| `HPC_SSH_KEY_PATH_HOST` | `.env` (you configure)            | Path on your local machine | `/Users/you/.ssh/hpc_key.pem` |
| `HPC_SSH_KEY_PATH`      | `docker-compose.yaml` (hardcoded) | Path inside container      | `/home/appuser/.ssh/hpc_key`  |

**Important**: Only set `HPC_SSH_KEY_PATH_HOST` in your `.env` file. The `HPC_SSH_KEY_PATH` is automatically set by docker-compose.yaml.

## Dockerfile Changes

The `Dockerfile.hpc` includes:

```dockerfile
# Create .ssh directory with proper permissions
RUN mkdir -p /home/appuser/.ssh && \
    chown -R appuser:appgroup /home/appuser/.ssh && \
    chmod 700 /home/appuser/.ssh
```

This ensures:
- SSH directory exists before key is mounted
- Proper ownership for the non-root `appuser`
- Correct permissions (700) required by SSH clients

## Security Features

1. **Read-Only Mount**: Key is mounted read-only (`:ro`) to prevent modification
2. **Non-Root User**: Container runs as `appuser`, not root
3. **Input Validation**: Tool validates all paths and commands to prevent injection
4. **No Plaintext Passwords**: Supports encrypted keys via `HPC_SSH_KEY_PASSPHRASE`
5. **Restricted Access**: SSH directory has 700 permissions

## Troubleshooting

### "SSH key not found" Error

```bash
# Check if key is mounted in container
docker compose exec hpc_mcp_server ls -la /home/appuser/.ssh/

# Should see:
# -rw------- 1 appuser appgroup ... hpc_key
```

**Fix**: Ensure `HPC_SSH_KEY_PATH_HOST` in `.env` points to your actual key file.

### "Permission denied (publickey)" Error

```bash
# Check key permissions on host
ls -la /Users/yourusername/.ssh/hpc_key.pem

# Should be: -rw------- (600)
# Fix with:
chmod 600 /Users/yourusername/.ssh/hpc_key.pem
```

### "Connection timed out" Error

- Verify `HPC_HOST` is correct and accessible from your network
- Check if `HPC_SSH_PORT` is correct (usually 22)
- Ensure firewall allows outbound SSH connections

### Key is Encrypted, But No Passphrase Prompt

Set the passphrase in `.env`:
```bash
HPC_SSH_KEY_PASSPHRASE="your_passphrase"
```

## Available Tools

Once configured, the multi-agent system can use these HPC tools:

### 1. `test_hpc_connection`
Tests SSH connectivity to the remote HPC cluster.

**Example Query**: "Test the SSH connection to the HPC cluster"

**Returns**:
```json
{
  "status": "success",
  "hostname": "hpc-login01.institution.edu",
  "kernel": "Linux",
  "uptime": "up 45 days"
}
```

### 2. `submit_slurm_job`
Submits a Slurm batch job to the remote cluster.

**Requirements**: Script must already exist on the HPC cluster filesystem.

**Example Query**: "Submit the Slurm job at /home/username/jobs/hello.sh"

**Returns**:
```json
{
  "status": "success",
  "job_id": "123456",
  "message": "Job submitted successfully"
}
```

### 3. `check_slurm_job_status`
Monitors the status of a submitted job.

**Example Query**: "Check the status of Slurm job 123456"

**Returns**:
```json
{
  "status": "success",
  "job_id": "123456",
  "job_state": "RUNNING",
  "job_name": "my_job",
  "partition": "compute",
  "runtime": "00:05:32"
}
```

## Next Steps

1. ✅ Configure `.env` with your HPC credentials
2. ✅ Verify SSH key exists and has proper permissions
3. ✅ Rebuild and start containers
4. ✅ Test connection via Streamlit or pytest
5. 🎯 Submit real jobs to your HPC cluster!

## Tool Disambiguation

The HPC MCP server hosts **two different types** of tools:

### Local Execution (Nextflow/BLAST)
- **Tool**: `run_nextflow_blast_pipeline`
- **Runs**: In the HPC MCP server container
- **Use Case**: Quick BLAST searches without cluster access

### Remote Execution (HPC SSH)
- **Tools**: `test_hpc_connection`, `submit_slurm_job`, `check_slurm_job_status`
- **Runs**: On your external HPC cluster via SSH
- **Use Case**: Large-scale jobs on institutional HPC resources

The LLM agent automatically chooses the correct tool based on your query.
