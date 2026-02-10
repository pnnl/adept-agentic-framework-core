# Podman Bootstrap Notes

This document records the Podman installation and configuration process on this node (WorkshopieMcWorkshop.emsl.pnl.gov).

## System Information

**OS:** Rocky Linux 9.7 (Blue Onyx)
**Kernel:** Linux 5.14.0-611.16.1.el9_7.x86_64
**Architecture:** x86_64 (amd64)
**Date:** 2026-02-09

## Installation Steps

### 1. Podman Installation

Podman was manually installed (version 5.6.0):
```bash
# Manual installation by user
# Podman 5.6.0 installed system-wide
```

Verified with:
```bash
$ podman --version
podman version 5.6.0
```

### 2. Python pip Installation

pip was not available on the system. Installed using the official bootstrap script:
```bash
curl -sSL https://bootstrap.pypa.io/get-pip.py | python3 -
```

Result:
- pip 26.0.1 installed to user directory
- wheel 0.46.3 installed
- packaging 26.0 installed

### 3. podman-compose Installation

Installed podman-compose via pip:
```bash
pip install podman-compose
```

Result:
- podman-compose 1.5.0 installed
- python-dotenv 1.2.1 installed as dependency
- PyYAML 5.4.1 already satisfied

### 4. Storage Configuration Issues

**Problem Encountered:**
When testing Podman with `podman run --rm hello-world`, encountered error:
```
lsetxattr /home/rigo160/.local/share/containers/storage/overlay/.../diff: operation not supported
```

**Root Cause:**
- Home directory is on a network filesystem (NFS)
- NFS detected by Podman: "Network file system detected as backing store"
- Overlay storage driver requires extended attributes (xattrs) which are not supported on NFS

**Initial Attempted Solution:**
Created `~/.config/containers/storage.conf` to use VFS driver:
```toml
[storage]
driver = "vfs"
```

However, this failed because Podman already had existing storage with overlay driver.

**Resolution Required:**
To fix this issue, need to either:
1. Reset Podman storage:
   ```bash
   podman system reset  # WARNING: Deletes all images and containers
   ```
2. Use a local (non-NFS) directory for storage by setting `graphroot` in storage.conf
3. Continue with overlay driver but expect compatibility issues

## Python Virtual Environment Solution

Instead of resolving the storage issue immediately, created a proper Python virtual environment approach for the project.

### Created Bootstrap Script

**File:** `/data/workspace/adept-agentic-framework-core/bootstrap-podman-env.sh`

The script:
1. Checks for Python 3 and Podman availability
2. Creates a dedicated virtual environment (`.venv-podman`)
3. Installs Podman Python libraries:
   - `podman` - Python SDK for Podman
   - `podman-compose` - Docker Compose compatibility
   - `python-dotenv` - Environment variable management
   - `pyyaml` - YAML parsing
   - `requests` - HTTP library
   - `rich` - Enhanced terminal output
4. Creates an activation helper script (`activate-podman-env.sh`)

### Usage

**One-time setup:**
```bash
./bootstrap-podman-env.sh
```

**Activate environment:**
```bash
source .venv-podman/bin/activate
# OR
source ./activate-podman-env.sh
```

**Deactivate:**
```bash
deactivate
```

## Configuration Issues Summary

### Issue 1: No subuid/subgid ranges
**Warning:**
```
cannot find UID/GID for user rigo160: no subuid ranges found for user "rigo160" in /etc/subuid
```

**Impact:** Rootless mode uses single mapping, may break some images

**Solution (if needed):**
```bash
# Add subuid/subgid ranges (requires root)
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 rigo160
```

### Issue 2: Network Filesystem
**Warning:**
```
Network file system detected as backing store. Enforcing overlay option force_mask="700"
```

**Impact:** Storage driver may have compatibility issues

**Solutions:**
1. Use VFS driver (slower but compatible):
   ```bash
   podman system reset
   # Then ensure storage.conf has: driver = "vfs"
   ```

2. Use local storage location:
   ```toml
   [storage]
   driver = "overlay"
   graphroot = "/tmp/podman-storage-$USER"
   ```

### Issue 3: Extended Attributes Not Supported
**Error:**
```
lsetxattr: operation not supported
```

**Impact:** Cannot use overlay storage driver on NFS

**Best Solution:**
Use VFS driver or local filesystem for storage.

## Environment-Specific Notes

### HPC/Cluster Environment Considerations

This node appears to be part of an HPC or cluster environment based on:
- Home directories on NFS
- No subuid/subgid configured by default
- Systemd cgroup v2 configuration

**Recommendations for HPC Usage:**

1. **Use VFS Storage Driver** - More compatible with NFS
2. **Consider Local Scratch Space** - Use `/tmp` or cluster scratch for storage
3. **Rootless Mode Limitations** - Some containers may not work without subuid/subgid
4. **Network Performance** - NFS backing may impact container I/O performance

## Documentation Updates

Updated the following files to include bootstrap instructions:

1. **Root Documentation:**
   - `README.md` - Added bootstrap quick start
   - `CLAUDE.md` - Added bootstrap to Podman workflow

2. **Chapter READMEs:**
   - `docs/tutorial-branches/chapter-00-introduction/README.md`
   - `docs/tutorial-branches/chapter-01-main/README.md`
   - `docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot/README.md`
   - `docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent/README.md`

All documentation now includes:
- Bootstrap script usage
- Virtual environment activation
- Prerequisites clarification

## Next Steps

To fully enable Podman on this node:

1. **Resolve Storage Issue:**
   ```bash
   # Option A: Reset and use VFS
   podman system reset
   echo '[storage]' > ~/.config/containers/storage.conf
   echo 'driver = "vfs"' >> ~/.config/containers/storage.conf

   # Option B: Use local storage
   mkdir -p /tmp/podman-storage-$USER
   echo '[storage]' > ~/.config/containers/storage.conf
   echo 'driver = "overlay"' >> ~/.config/containers/storage.conf
   echo "graphroot = \"/tmp/podman-storage-$USER\"" >> ~/.config/containers/storage.conf
   ```

2. **Configure subuid/subgid (optional, requires admin):**
   ```bash
   # Request admin to add:
   echo "$USER:100000:65536" | sudo tee -a /etc/subuid
   echo "$USER:100000:65536" | sudo tee -a /etc/subgid
   podman system migrate
   ```

3. **Test Basic Functionality:**
   ```bash
   source .venv-podman/bin/activate
   podman run --rm hello-world
   ```

4. **Launch Chapter 0 (Introduction):**
   ```bash
   cd docs/tutorial-branches/chapter-00-introduction
   ./start-chapter-resources-podman.sh
   ```

## References

- Podman Documentation: https://podman.io/docs
- Podman Python SDK: https://podman-py.readthedocs.io/
- Rootless Containers: https://rootlesscontaine.rs/
- NFS Storage Issues: https://github.com/containers/podman/issues/8272

## Troubleshooting Commands

```bash
# Check Podman info
podman info

# Check storage configuration
cat ~/.config/containers/storage.conf

# Check current storage
podman system df

# Reset everything (WARNING: deletes all containers/images)
podman system reset

# Check subuid/subgid
grep $USER /etc/subuid /etc/subgid

# Test hello-world
podman run --rm hello-world
```

---

**Last Updated:** 2026-02-09
**System:** WorkshopieMcWorkshop.emsl.pnl.gov
**Podman Version:** 5.6.0
**Python Version:** 3.9
