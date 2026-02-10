# Chapter 0 Troubleshooting Guide

## Common Issues and Solutions

### Issue: MCP Server Fails with "No module named 'asyncpg'"

**Symptom:**
```
ModuleNotFoundError: No module named 'asyncpg'
```

**Root Cause:**
The `.env` file is configured to use PostgreSQL (`postgresql+asyncpg://...`) but Chapter 0 does not include a PostgreSQL container. Chapter 0 is designed to use SQLite for simplicity.

**Solution:**
Edit `.env` file and change the `DATABASE_URL`:

```bash
# From (PostgreSQL - requires asyncpg):
DATABASE_URL=postgresql+asyncpg://admin:password@postgres:5432/agentic_orchestrator

# To (SQLite - no external dependencies):
DATABASE_URL=sqlite+aiosqlite:///./data/agentic_framework.db
```

Then restart containers:
```bash
sudo env "PATH=$PATH" podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml down
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

### Issue: Streamlit Can't Connect to MCP Server

**Symptom:**
```
RuntimeError: Client failed to connect: All connection attempts failed
```

**Root Cause:**
MCP server container is not running or crashed on startup. Usually caused by database configuration issues (see above).

**Solution:**
1. Check MCP server logs: `sudo podman logs agentic_mcp_server_ch00`
2. Look for errors like "asyncpg" or "permission denied"
3. Apply fixes for those specific errors
4. Restart containers

### Issue: ChromaDB Permission Denied

**Symptom:**
```
chromadb.errors.InternalError: Permission denied (os error 13)
```

**Root Cause:**
Container runs as non-root user but host directories are owned by root with restrictive permissions.

**Solution:**
The `start-chapter-resources-podman.sh` script automatically runs `chmod -R 777 data notebooks` before starting containers. If you see this error:

```bash
# Fix permissions manually:
cd /data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-00-introduction
sudo chmod -R 777 data notebooks

# Restart containers:
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

### Issue: Sudo Password Prompts Every Time

**Symptom:**
You have to enter your password every time you run `sudo` commands for Podman.

**Solution:**
Configure passwordless sudo for Podman commands:

```bash
sudo ./configure-sudo-nopasswd.sh
```

Or manually edit sudoers:
```bash
sudo visudo -f /etc/sudoers.d/podman-$(whoami)
```

Add:
```
your_username ALL=(ALL) NOPASSWD: /usr/bin/podman
your_username ALL=(ALL) NOPASSWD: /usr/bin/podman-compose
your_username ALL=(ALL) NOPASSWD: /usr/local/bin/podman-compose
your_username ALL=(ALL) NOPASSWD: /home/your_username/.local/bin/podman-compose
```

## Helper Scripts

### check-service-logs.sh
Cross-reference logs from all services and highlight errors.

**Usage:**
```bash
sudo ./check-service-logs.sh summary    # Errors only
sudo ./check-service-logs.sh full 50    # Last 50 lines each
sudo ./check-service-logs.sh follow     # Live tail all services
sudo ./check-service-logs.sh health     # Check HTTP endpoints
```

### verify-services.sh
Verify all services are healthy and accessible.

**Usage:**
```bash
sudo ./verify-services.sh
```

Checks:
- Container status
- HTTP endpoint health (Ollama, MCP, Streamlit, JupyterLab)
- Database file existence
- ChromaDB directory permissions

### configure-sudo-nopasswd.sh
Configure passwordless sudo for Podman operations (RECOMMENDED).

**Usage:**
```bash
sudo ./configure-sudo-nopasswd.sh
```

## Verification Checklist

After fixing issues, verify everything works:

1. **Check container status:**
   ```bash
   sudo podman ps --filter "name=ch00"
   ```
   Should show 4 containers running: ollama_ch00, agentic_mcp_server_ch00, agentic_streamlit_app_ch00, agentic_jupyterlab_ch00

2. **Check logs for errors:**
   ```bash
   sudo ./check-service-logs.sh summary
   ```
   Should show NO critical errors (deprecation warnings are OK)

3. **Check health endpoints:**
   ```bash
   sudo ./verify-services.sh
   ```
   All checks should show ✓ OK

4. **Access Streamlit:**
   ```bash
   # Via SSH port forwarding:
   https://localhost:18501  # (or your custom port)

   # Direct access:
   https://localhost:8501
   ```

## Getting Help

If issues persist:
1. Run: `sudo ./check-service-logs.sh full 100 > chapter0-logs.txt`
2. Review the logs for specific error messages
3. Check the main [Podman troubleshooting docs](../../PODMAN_BUGFIX_PROCESS.md)
4. Open a GitHub issue with logs attached
