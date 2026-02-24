# HPC SSH Tool Integration - Chapter 03

## Overview

The HPC SSH tool from Chapter 01 has been successfully integrated into Chapter 03's HPC MCP server. This enables the multi-agent system to connect to remote HPC clusters via SSH, submit Slurm batch jobs, and monitor job status.

## Changes Made

### 1. **Tool File Added**
- **Location**: `src/agentic_framework_pkg/hpc_mcp_server/tools/hpc_ssh_tool.py`
- **Source**: Copied from Chapter 01's `mcp_server/tools/hpc_ssh_tool.py`
- **Tools Provided**:
  - `test_hpc_connection()` - Test SSH connectivity to HPC cluster
  - `submit_slurm_job()` - Submit Slurm batch jobs
  - `check_slurm_job_status()` - Monitor job status

### 2. **Tool Registration**
- **File**: `src/agentic_framework_pkg/hpc_mcp_server/main.py`
- **Changes**:
  ```python
  # Added import
  from .tools import nextflow_blast_tool, video_processing_tool, gitxray_tool, hpc_ssh_tool
  
  # Added registration in setup_hpc_mcp_server()
  hpc_ssh_tool.register_tools(mcp_instance)  # SSH-based Slurm job submission
  ```

### 3. **Dependency Added**
- **File**: `pyproject.toml`
- **Added**: `fabric>=3.0.0` - SSH remote execution library
- **Install**: Run `uv sync` to install the new dependency

### 4. **Docker Configuration**
- **File**: `docker-compose.yaml`
- **Service**: `hpc_mcp_server`
- **Added Environment Variables**:
  ```yaml
  - HPC_HOST=${HPC_HOST}
  - HPC_USER=${HPC_USER}
  - HPC_SSH_PORT=${HPC_SSH_PORT:-22}
  - HPC_SSH_KEY_PATH=/home/appuser/.ssh/hpc_key
  - HPC_SSH_KEY_PASSPHRASE=${HPC_SSH_KEY_PASSPHRASE}
  - HPC_SSH_PASSWORD=${HPC_SSH_PASSWORD}
  ```
- **Added Volume Mount**:
  ```yaml
  - ${HPC_SSH_KEY_PATH_HOST:-/dev/null}:/home/appuser/.ssh/hpc_key:ro
  ```

### 5. **Environment Variables**

Add these variables to your `.env` file:

```bash
# Required for SSH connection
HPC_HOST="hpc.institution.edu"     # Your HPC cluster hostname or IP
HPC_USER="your_username"            # Your SSH username
HPC_SSH_PORT=22                     # SSH port (default: 22)

# SSH Key Authentication (RECOMMENDED)
# HPC_SSH_KEY_PATH_HOST: Path to key on YOUR LOCAL MACHINE (host)
#   Docker will mount this file into the container at /home/appuser/.ssh/hpc_key
#   The Python tool automatically reads HPC_SSH_KEY_PATH=/home/appuser/.ssh/hpc_key
HPC_SSH_KEY_PATH_HOST="/Users/yourusername/.ssh/your_hpc_key.pem"

# Optional: Passphrase if key is encrypted
# HPC_SSH_KEY_PASSPHRASE="your_passphrase"

# Alternative: Password Authentication (NOT RECOMMENDED)
# HPC_SSH_PASSWORD="your_password"
```

**Important SSH Key Path Configuration**:
- **`HPC_SSH_KEY_PATH_HOST`**: Path on your local machine (e.g., `/Users/you/.ssh/hpc_key.pem`)
  - Used by Docker to mount the file into the container
  - Set this in your `.env` file
- **`HPC_SSH_KEY_PATH`**: Path inside the container (fixed: `/home/appuser/.ssh/hpc_key`)
  - Set automatically by docker-compose.yaml
  - The Python tool reads this env var to find the mounted key
  - Do NOT set this in your `.env` file (it's hardcoded in docker-compose.yaml)

**Flow**: Your key at `${HPC_SSH_KEY_PATH_HOST}` → mounted to container at `/home/appuser/.ssh/hpc_key` → tool reads `HPC_SSH_KEY_PATH=/home/appuser/.ssh/hpc_key`


- **File**: `.env.example` (already contained HPC SSH configuration)
- **Configuration Required**:
  ```bash
  # HPC Cluster Connection
  HPC_HOST="hpc.institution.edu"
  HPC_USER="your_username"
  HPC_SSH_PORT=22
  
  # SSH Authentication (Option 1: Key - RECOMMENDED)
  HPC_SSH_KEY_PATH_HOST="/Users/yourusername/.ssh/your_hpc_key.pem"
  # HPC_SSH_KEY_PASSPHRASE=""  # Optional: if key is encrypted
  
  # SSH Authentication (Option 2: Password - NOT RECOMMENDED)
  # HPC_SSH_PASSWORD="your_password"
  ```

## How to Use

### 1. Configure Environment
Copy `.env.example` to `.env` and configure your HPC connection:
```bash
HPC_HOST=hpc.institution.edu
HPC_USER=your_username
HPC_SSH_KEY_PATH_HOST=/Users/yourname/.ssh/hpc_key.pem
```

### 2. Rebuild Containers
```bash
docker compose build hpc_mcp_server
docker compose up -d
```

### 3. Test via Streamlit UI
Ask the multi-agent system:
- "Can you test the connection to our HPC cluster?"
- "Submit the job script at /home/username/jobs/hello.sh"
- "What's the status of job 123456?"

## Available Tools

### test_hpc_connection
Test SSH connection to HPC cluster and verify authentication.

**Returns**:
- hostname
- kernel version
- uptime

### submit_slurm_job
Submit a Slurm batch job that exists on the remote HPC.

**Parameters**:
- `script_path` (required): Path to .sh script on remote HPC
- `job_name` (optional): Override job name

**Returns**:
- job_id
- submission output

### check_slurm_job_status
Query Slurm scheduler for job status.

**Parameters**:
- `job_id` (required): Slurm job ID

**Returns**:
- job_state (PENDING, RUNNING, COMPLETED, FAILED, etc.)
- job_name
- partition
- runtime

## Security Features

### Input Validation
All user inputs are validated to prevent command injection:
- **Path validation**: Blocks shell metacharacters (`;`, `&`, `|`, `` ` ``, `$()`)
- **Job name validation**: Only alphanumeric, dash, underscore, dot allowed
- **Job ID validation**: Must be numeric only

### Limited Command Set
Tool only executes these specific commands:
- `uname -s`, `hostname`, `uptime` (read-only system info)
- `test -f <path>` (file existence check)
- `sbatch <validated_path>` (job submission with validated inputs)
- `squeue -j <validated_job_id>` (job status query)

### Authentication
- Supports SSH keys (encrypted or unencrypted)
- SSH key mounted read-only into container
- No credentials in source code

## Testing

### Unit Tests
The tool includes comprehensive validation and parsing functions:
- `_validate_path_safe()` - Prevents path-based injection
- `_validate_job_name_safe()` - Validates job names
- `_validate_job_id_safe()` - Validates numeric job IDs
- `_parse_sbatch_output()` - Extracts job ID from submission
- `_parse_squeue_output()` - Parses job status output

### Integration Testing
1. Create test job on HPC:
   ```bash
   ssh user@hpc.edu
   mkdir -p ~/jobs
   cat > ~/jobs/hello.sh << 'EOF'
   #!/bin/bash
   #SBATCH --job-name=hello_test
   #SBATCH --time=00:01:00
   #SBATCH --ntasks=1
   echo "Hello from HPC!"
   hostname
   EOF
   chmod +x ~/jobs/hello.sh
   ```

2. Test via Streamlit:
   - "Test connection to HPC"
   - "Submit /home/username/jobs/hello.sh"
   - "Check status of job 123456"

## Troubleshooting

### Connection Refused
- Verify `HPC_HOST` is correct
- Check SSH port (default: 22)
- Ensure HPC firewall allows connections

### Authentication Failed
- Verify `HPC_USER` is correct
- Check SSH key path in `.env`
- Ensure public key is in `~/.ssh/authorized_keys` on HPC
- Test manually: `ssh -i ~/.ssh/hpc_key user@hpc`

### Key Not Found
- Verify `HPC_SSH_KEY_PATH_HOST` points to existing file
- Check file permissions: `chmod 600 ~/.ssh/hpc_key`
- Restart containers: `docker compose down && docker compose up -d`

### Script Not Found
- SSH to HPC and verify file exists
- Use absolute paths
- Check file permissions: `chmod +x script.sh`

## Differences from Chapter 01

1. **Tool Location**: In HPC MCP server instead of main MCP server
2. **Registration Pattern**: Follows Chapter 03's multi-server pattern
3. **Logging**: Uses Chapter 03's centralized logger
4. **Dependencies**: Already installed via `pyproject.toml`

## Next Steps

1. Copy `.env.example` to `.env` and configure HPC settings
2. Run `uv sync` to install fabric dependency
3. Rebuild HPC MCP server: `docker compose build hpc_mcp_server`
4. Start services: `docker compose up -d`
5. Test via Streamlit UI with HPC queries

## References

- [Chapter 01 HPC SSH Tool Planning](../../chapter-01-main/docs/HPC_SSH_TOOL_MVP_PLAN.md)
- [Chapter 01 HPC SSH Tool Usage Guide](../../chapter-01-main/docs/HPC_SSH_TOOL_USAGE.md)
- [Fabric Documentation](https://www.fabfile.org/)
- [Slurm Documentation](https://slurm.schedmd.com/)
