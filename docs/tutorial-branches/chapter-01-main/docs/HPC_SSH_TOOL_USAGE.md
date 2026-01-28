# HPC SSH Tool - Usage Guide

## Overview

The HPC SSH Tool enables the AI agent to connect to remote HPC clusters, submit Slurm batch jobs, and monitor job status via SSH.

## Quick Start

### 1. Configure Environment Variables

Copy `.env.example` to `.env` and configure your HPC connection:

```bash
# Required
HPC_HOST=hpc.institution.edu
HPC_USER=your_username
HPC_SSH_PORT=22

# Option 1: SSH Key (RECOMMENDED)
# Path to SSH key on your HOST machine (Docker will mount it)
HPC_SSH_KEY_PATH_HOST=/Users/yourname/.ssh/hpc_key.pem

# Option 2: Encrypted SSH Key with Passphrase
HPC_SSH_KEY_PATH_HOST=/Users/yourname/.ssh/encrypted_key.pem
HPC_SSH_KEY_PASSPHRASE=   # Leave empty or add passphrase

# Option 3: Password (NOT RECOMMENDED)
# HPC_SSH_PASSWORD=   # Not recommended for production
```

**Important Notes:**
- `HPC_SSH_KEY_PATH_HOST` is the path on your **local machine** (host filesystem)
- Docker mounts this key to `/home/appuser/.ssh/hpc_key` inside the container
- The container automatically uses the mounted key (no need to set `HPC_SSH_KEY_PATH`)
- For security, only the specific key file is mounted (not your entire `~/.ssh/` directory)

### 2. Supported SSH Key Formats

The tool supports all standard SSH private key formats:
- **Unencrypted PEM** (`.pem`, `.key`)
- **Encrypted PEM with passphrase** (passphrase-protected)
- **OpenSSH format** (`id_rsa`, `id_ed25519`)
- **RSA, DSA, ECDSA, Ed25519** key types

### 3. How Encrypted Keys Work

Fabric (the SSH library) handles encrypted keys automatically:

1. **With ssh-agent:** If your key is loaded in ssh-agent, no passphrase needed
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_rsa  # Will prompt for passphrase once
   ```

2. **With HPC_SSH_KEY_PASSPHRASE:** Provide passphrase in `.env` (auto-decryption)
   ```bash
   HPC_SSH_KEY_PASSPHRASE=   # Add your passphrase here if key is encrypted
   ```

3. **Interactive prompt:** If key is encrypted and no passphrase in env, Fabric will prompt (not suitable for Docker containers)

### 4. Generate SSH Keys (if needed)

```bash
# Generate unencrypted key (simplest)
ssh-keygen -t ed25519 -f ~/.ssh/hpc_key -N ""

# Generate encrypted key with passphrase (more secure)
ssh-keygen -t ed25519 -f ~/.ssh/hpc_key

# Copy public key to HPC
ssh-copy-id -i ~/.ssh/hpc_key.pub user@hpc.institution.edu
```

Then set in `.env`:
```bash
HPC_SSH_KEY_PATH_HOST=/Users/yourname/.ssh/hpc_key
# Add passphrase only if key is encrypted:
# HPC_SSH_KEY_PASSPHRASE=
```

## Available Tools

### 1. test_hpc_connection

Test SSH connection to HPC cluster.

**Example Agent Query:**
```
Can you test the connection to our HPC cluster?
```

**Returns:**
```json
{
  "status": "success",
  "hostname": "hpc-login01.institution.edu",
  "kernel": "Linux",
  "uptime": "up 45 days"
}
```

### 2. submit_slurm_job

Submit a Slurm batch job from a script that already exists on the HPC.

**Example Agent Query:**
```
Submit the job script at /home/username/jobs/hello_world.sh
```

**Returns:**
```json
{
  "status": "success",
  "job_id": "123456",
  "message": "Job 123456 submitted successfully",
  "script_path": "/home/username/jobs/hello_world.sh"
}
```

**Parameters:**
- `script_path` (required): Path to batch script on remote HPC
- `job_name` (optional): Override job name

### 3. check_slurm_job_status

Check status of a submitted job.

**Example Agent Query:**
```
What's the status of job 123456?
```

**Returns:**
```json
{
  "status": "success",
  "job_id": "123456",
  "job_state": "RUNNING",
  "job_name": "hello_world",
  "partition": "compute",
  "user": "username",
  "runtime": "0:05:30"
}
```

**Job States:**
- `PENDING` - Waiting in queue
- `RUNNING` - Currently executing
- `COMPLETED` - Finished successfully
- `FAILED` - Job failed
- `CANCELLED` - User cancelled
- `NOT_FOUND` - Not in queue (may have completed)

## Example Workflow

### 1. Create Test Job on HPC

SSH to your HPC and create a test script:

```bash
ssh user@hpc.institution.edu
mkdir -p ~/jobs
cat > ~/jobs/hello_world.sh << 'EOF'
#!/bin/bash
#SBATCH --job-name=hello_test
#SBATCH --output=hello_%j.out
#SBATCH --error=hello_%j.err
#SBATCH --time=00:01:00
#SBATCH --ntasks=1
#SBATCH --mem=100M

echo "Hello from HPC MCP Tool!"
hostname
date
sleep 10
echo "Job completed successfully"
EOF

chmod +x ~/jobs/hello_world.sh
```

### 2. Use Agent to Submit Job

Talk to the agent:

```
User: Can you connect to our HPC cluster and check if it's working?
Agent: [Calls test_hpc_connection] 
       Yes, I successfully connected to hpc-login01.institution.edu running Linux.

User: Great! Please submit the hello world job at /home/username/jobs/hello_world.sh
Agent: [Calls submit_slurm_job]
       Job submitted successfully! The job ID is 123456.

User: What's the status?
Agent: [Calls check_slurm_job_status]
       Job 123456 is currently RUNNING. It's been running for 0:00:15.

User: Check again in 30 seconds
Agent: [Calls check_slurm_job_status after wait]
       Job 123456 is no longer in the queue - it has either completed or been removed.
```

## Troubleshooting

### Connection Refused
```
Error: Connection failed: [Errno 61] Connection refused
```
**Fix:** Check that HPC_HOST is correct and SSH port is open (usually 22)

### Authentication Failed
```
Error: Connection failed: Authentication failed
```
**Fix:** 
- Verify HPC_USER is correct
- Check SSH key is correct: `ssh -i ~/.ssh/hpc_key user@hpc`
- Ensure public key is in `~/.ssh/authorized_keys` on HPC

### Key Not Found
```
Error: SSH key not found: /home/appuser/.ssh/hpc_key
```
**Fix:** 
- Verify `HPC_SSH_KEY_PATH_HOST` in `.env` points to an existing file on your host machine
- Ensure the key file has correct permissions: `chmod 600 ~/.ssh/hpc_key`
- Restart Docker containers after changing `.env`: `docker compose down && docker compose up -d`

### Encrypted Key Prompt (in Docker)
```
Error: Timeout waiting for passphrase prompt
```
**Fix:** Add `HPC_SSH_KEY_PASSPHRASE` to `.env` or use unencrypted key

### Script Not Found
```
Error: Script not found on HPC: /home/user/script.sh
```
**Fix:** 
- SSH to HPC and verify file exists: `ls -l /home/user/script.sh`
- Use absolute paths, not relative
- Ensure correct permissions: `chmod +x script.sh`

### Job Not Found
```
job_state: NOT_FOUND
```
**Reason:** Job completed and is no longer in queue
**Fix:** Check job output files or use `sacct -j <job_id>` on HPC

## Security Best Practices

### ✅ DO:
- Use SSH keys instead of passwords
- Use encrypted PEM keys with passphrases
- Store private keys with restricted permissions: `chmod 600 ~/.ssh/hpc_key`
- Use `.env` for secrets (gitignored)
- Regularly rotate SSH keys
- Review job scripts before submission
- Use HPC user account with appropriate permissions (not root)

### ❌ DON'T:
- Commit `.env` to git
- Use password authentication in production
- Share SSH keys between users
- Store unencrypted keys in Docker images
- Use the same key for multiple services
- Give the agent SSH access to production systems without review

### 🛡️ Built-in Security Guardrails

The HPC SSH tool includes multiple layers of protection against malicious use:

#### 1. **Input Validation**
All user inputs are validated before execution:

- **Script Paths**: Blocked characters: `;`, `&`, `|`, `` ` ``, `$()`, `${}`, `<`, `>`
  - Prevents: Command injection via path manipulation
  - Example blocked: `/home/user/script.sh; rm -rf /`

- **Job Names**: Only allows `a-z`, `A-Z`, `0-9`, `-`, `_`, `.`
  - Max length: 64 characters
  - Prevents: Command injection via job name parameter
  - Example blocked: `test_job; cat /etc/passwd`

- **Job IDs**: Must be numeric only
  - Prevents: Command injection via job ID lookup
  - Example blocked: `12345; cat /etc/shadow`

#### 2. **Limited Command Set**
The tool only executes these specific commands:
- `uname -s` - Get kernel info (read-only)
- `hostname` - Get hostname (read-only)
- `uptime` - Get uptime (read-only)
- `test -f <path>` - Check file exists (read-only)
- `sbatch <options> <path>` - Submit job (validated inputs)
- `squeue -j <job_id>` - Check job status (read-only)

**Not Supported** (by design):
- ❌ Arbitrary shell command execution
- ❌ File deletion (`rm`, `rmdir`)
- ❌ File modification (`mv`, `cp`, `sed`, `awk`)
- ❌ Permission changes (`chmod`, `chown`)
- ❌ System administration (`sudo`, `su`)

#### 3. **HPC User Permissions**
Security is enforced at the HPC level:
- Agent runs with the configured user's SSH credentials
- Subject to all HPC access controls and quotas
- Cannot access files/directories without proper permissions
- Cannot affect other users' jobs or data
- Slurm scheduler enforces resource limits

### 🔐 Future Enhancements (Not in MVP)

Planned security features for later chapters:
- **Audit Logging**: Track all HPC commands with timestamps and user context
- **Allowlist Mode**: Only permit job submission to specific directories
- **Dry-Run Mode**: Preview commands before execution
- **Multi-Factor Auth**: Require approval for certain operations
- **Rate Limiting**: Prevent excessive job submission

## Testing

### Run Unit Tests
```bash
cd docs/tutorial-branches/chapter-01-main
uv run pytest src/agentic_framework_pkg/mcp_server/tools/test_hpc_ssh_tool.py -v

# Or run all tests
uv run pytest tests/ -v
```

### Test with Real HPC (Integration)
Set up `.env` with real credentials, then:
```bash
# Start services
docker compose up -d

# Test via agent
uv run streamlit run src/agentic_framework_pkg/streamlit_app/app.py
```

## Limitations (MVP)

Current version does NOT support:
- File transfer (SFTP/SCP) 
- Job output retrieval 
- Job cancellation 

## Next Steps

1. Test connection to your HPC
2. Create a hello world test job
3. Submit job via agent
4. Monitor job status
5. Check output files on HPC
