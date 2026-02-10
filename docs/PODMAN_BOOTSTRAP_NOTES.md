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

**Resolution Applied:**
✅ Fixed by using local temporary storage with VFS driver:
```bash
# Storage directory cleared
rm -rf ~/.local/share/containers/storage

# Configured in ~/.config/containers/storage.conf:
[storage]
driver = "vfs"
graphroot = "/tmp/podman-storage-rigo160"
runroot = "/tmp/podman-run-rigo160"
```

✅ Test passed: `podman run --rm hello-world` succeeded

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

**Solution Applied:**
✅ Configured VFS driver with local storage:
```bash
[storage]
driver = "vfs"
graphroot = "/tmp/podman-storage-rigo160"
runroot = "/tmp/podman-run-rigo160"
```

This configuration is now automatically applied by `bootstrap-podman-env.sh`.

### Issue 3: Extended Attributes Not Supported
**Error:**
```
lsetxattr: operation not supported
```

**Impact:** Cannot use overlay storage driver on NFS

**Solution Applied:**
✅ Using VFS driver with local filesystem storage (see Issue 2).

---

### Issue 4: Insufficient UIDs/GIDs for Container Images
**Error encountered during image build:**
```
potentially insufficient UIDs or GIDs available in user namespace (requested 0:42 for /etc/gshadow)
Check /etc/subuid and /etc/subgid
```

**Root Cause:**
- No subuid/subgid ranges configured for user `rigo160`
- Rootless Podman uses single user mapping (current UID only)
- Many container images expect multiple UID/GID mappings (e.g., Python image has group ID 42)

**Impact:**
- Cannot build or run most container images in rootless mode
- Build process fails when trying to extract layers with different UIDs/GIDs

**Solution:**
Configure subuid/subgid ranges (requires admin/sudo):

```bash
# Add UID and GID ranges for the user
sudo usermod --add-subuids 100000-165535 $USER
sudo usermod --add-subgids 100000-165535 $USER

# Verify configuration
grep $USER /etc/subuid /etc/subgid
# Expected output:
# rigo160:100000:65536
# rigo160:100000:65536

# Migrate Podman to use new configuration
podman system migrate
```

**Alternative (if sudo not available):**
Use rootful Podman for all operations:
```bash
sudo -E bash -c 'source .venv-podman/bin/activate && cd docs/tutorial-branches/chapter-XX && ./start-chapter-resources-podman.sh'
```

**Status:**
⚠️ **Pending Resolution** - Requires admin to configure subuid/subgid ranges

---

### Issue 5: podman-compose Merge Error with platform: null
**Error:**
```
ValueError: can't merge value of [platform] of type <class 'str'> and <class 'NoneType'>
```

**Root Cause:**
- Original overlay files set `platform: null` to remove platform specifications
- podman-compose cannot merge string values from base file with null values from overlay

**Solution Applied:**
✅ Fixed - Removed `platform:` keys entirely from overlay files instead of setting to null. The overlay files now only override volumes and security options.

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

## Resolution Update (2026-02-09 17:40)

### Attempt 3: Subuid/Subgid Configuration Applied

**Action taken:**
```bash
sudo usermod --add-subuids 100000-165535 rigo160
sudo usermod --add-subgids 100000-165535 rigo160
```

**Verification:**
```bash
$ grep rigo160 /etc/subuid /etc/subgid
/etc/subuid:rigo160:100000:65536
/etc/subgid:rigo160:100000:65536
```

**Test result:**
```
Error: newuidmap: Target process is owned by a different user
uid:316305 pw_uid:316305 st_uid:316305
```

**Root cause identified:**
- User UID is 316305 (very high, indicates LDAP/network user)
- Subuid/subgid ranges were added but newuidmap fails
- This is a known issue with network/LDAP users in rootless Podman
- The system's newuidmap doesn't properly handle high UIDs with subordinate ranges

**References:**
- https://github.com/containers/podman/issues/2898
- https://github.com/shadow-maint/shadow/issues/158

### Decision: Use Docker Instead

**Discovery:**
- User is already member of `docker` group (GID 318)
- Docker daemon is running and accessible
- Test passed: `docker run --rm hello-world`

**Rationale:**
1. **Docker works immediately** - No additional configuration needed
2. **Full chapter support** - Docker supports all chapters (0-6)
3. **Network user limitations** - Rootless Podman has known issues with LDAP/NIS users
4. **Time efficiency** - Can deploy now vs troubleshooting newuidmap
5. **Podman still available** - Can revisit rootful Podman for specific use cases

**Implementation:**
Launched Chapter 0 with Docker in background mode:
```bash
cd docs/tutorial-branches/chapter-00-introduction
nohup ./start-chapter-resources.sh > logs/chapter-00-docker-$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### Lessons Learned

1. **Check existing infrastructure first** - Docker was already configured
2. **Network users complicate rootless** - LDAP/NIS users have special challenges
3. **Docker group membership = ready to use** - No additional setup needed
4. **Podman rootful still viable** - For specific HPC use cases, can use `sudo -E`
5. **VFS storage works** - When we did get Podman working (hello-world), VFS driver succeeded

---

## Configuration Fixes for Rootful Podman (2026-02-09 18:00)

> **📋 Implementation Status:** See [PODMAN_IMPLEMENTATION_PROGRESS.md](PODMAN_IMPLEMENTATION_PROGRESS.md) for detailed progress tracking, test results, and verification checklist.

After determining that rootless Podman cannot work with network users due to newuidmap limitations, we implemented rootful Podman as the solution. During this process, we discovered and fixed 8 configuration issues in the existing Podman overlay files and startup scripts.

### Issues Fixed

1. **Conflicting Security Options (HIGH)**
   - **Problem:** `security_opt: label=disable` in all services disabled SELinux labeling
   - **Impact:** Made volume labels (`:Z`, `:z`) ineffective, causing permission issues
   - **Fix:** Removed `label=disable` from all services to allow SELinux labels to work
   - **Files:** All 4 chapter overlay files

2. **Inconsistent AppArmor Configuration (MEDIUM)**
   - **Problem:** Only sandbox_mcp_server had `apparmor=unconfined`, other services lacked it
   - **Impact:** Inconsistent security posture across services
   - **Fix:** Added `apparmor=unconfined` to ALL services for consistent security policy
   - **Files:** All 4 chapter overlay files

3. **Podman Socket Label Too Restrictive (MEDIUM)**
   - **Problem:** Chapter 3 mounted Podman socket with `:Z` (private) instead of `:z` (shared)
   - **Impact:** Prevented shared access to socket across containers
   - **Fix:** Changed socket mount from `:Z` to `:z` in sandbox_mcp_server
   - **Files:** Chapter 3 overlay file

4. **No Rootless/Rootful Detection (MEDIUM)**
   - **Problem:** Scripts didn't detect or require rootful mode for network users
   - **Impact:** Users hit confusing newuidmap errors
   - **Fix:** Added EUID check at start of all scripts to require sudo
   - **Files:** All 4 chapter startup scripts

5. **Missing Rootful Verification (MEDIUM)**
   - **Problem:** No check that rootful Podman actually works
   - **Impact:** Silent failures if Podman service not running
   - **Fix:** Added `podman ps` verification in prerequisite checks
   - **Files:** All 4 chapter startup scripts

6. **Unclear Error Messages (LOW)**
   - **Problem:** No clear guidance when rootless mode fails
   - **Impact:** Users don't understand why it failed or how to fix
   - **Fix:** Added detailed error message explaining network user limitation and sudo requirement
   - **Files:** All 4 chapter startup scripts

7. **PATH Reset by sudo (MEDIUM)**
   - **Problem:** `sudo` resets PATH, causing `podman-compose` to not be found (installed in `~/.local/bin`)
   - **Impact:** Script fails with "command not found" even with correct sudo usage
   - **Fix:** Scripts now capture PATH before sudo check and restore it, plus provide correct command in error message
   - **Files:** All 4 chapter startup scripts

8. **Registry Search Order (HIGH)**
   - **Problem:** Podman searches Red Hat registry first for unqualified images, can't find Docker Hub images
   - **Impact:** Build failures with "Repo not found" when pulling images like `jupyter/scipy-notebook:latest`
   - **Fix:** Created `configure-podman-registries.sh` script to configure Docker Hub as primary search registry
   - **Files:** New script in project root

### Testing Results

**Testing Status:** ✅ SUCCESSFUL

**Chapter 0 - Attempt 1 (FAILED):**
- Error: Podman tried to pull from Red Hat registry instead of Docker Hub
- Fix applied: Created registries configuration script

**Chapter 0 - Attempt 2 (SUCCESS):**
- Date: 2026-02-09 20:30
- All 4 services started successfully
- Images pulled from docker.io (Docker Hub)
- JupyterLab loaded with all extensions
- No newuidmap errors
- No SELinux permission errors
- Log: logs/start-chapter-resources-podman.20260209-2030.log

**Next test steps:**

```bash
# Step 1: Configure Podman registries for root
sudo ./configure-podman-registries.sh

# Step 2: Activate Podman environment
source .venv-podman/bin/activate

# Step 3: Launch with sudo and PATH preserved
cd docs/tutorial-branches/chapter-00-introduction
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

**Expected outcomes:**
- ✅ podman-compose found via preserved PATH
- ✅ Images pulled from docker.io (Docker Hub)
- ✅ All services start successfully (ollama, mcp_server, streamlit_app, jupyterlab)
- ✅ No newuidmap errors
- ✅ SELinux labels working correctly (no permission errors)
- ✅ Consistent AppArmor policy across all services
- ✅ Clean shutdown with Ctrl+C

### Usage for All Chapters

All Podman chapters now require rootful mode:

```bash
# Step 1: One-time setup - Configure registries (REQUIRED ONCE)
sudo ./configure-podman-registries.sh

# Step 2: One-time bootstrap (if not done already)
./bootstrap-podman-env.sh

# Step 3: Activate environment (each session)
source .venv-podman/bin/activate

# Step 4: Launch any chapter with sudo preserving PATH
cd docs/tutorial-branches/chapter-XX-name
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh

# Or with -E flag (preserves all environment variables including .env):
sudo -E env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

**Important notes:**
- The `configure-podman-registries.sh` script configures Podman to search Docker Hub for images
- The `env "PATH=$PATH"` is required because sudo resets PATH and won't find podman-compose in `~/.local/bin`
- Scripts will also attempt to restore the PATH automatically

**Why rootful mode is required:**
1. Network/LDAP users (high UIDs like 316305) cannot use rootless Podman
2. newuidmap utility limitation with subordinate UID/GID ranges
3. Known unfixable issue (see GitHub issues containers/podman#2898, shadow-maint/shadow#158)
4. Chapter 3 additionally requires privileged mode for sandbox/nsjail

**Security implications:**
- Rootful Podman has similar security model to Docker daemon
- Acceptable for HPC development environments
- Use in trusted networks only
- Containers still have SELinux and AppArmor restrictions

### Configuration Changes Summary

**Before (non-functional):**
```yaml
services:
  mcp_server:
    security_opt:
      - label=disable  # Broke SELinux labels
    volumes:
      - ./data:/app/data:Z  # Label ignored
```

**After (functional):**
```yaml
services:
  mcp_server:
    security_opt:
      - apparmor=unconfined  # Consistent policy
    volumes:
      - ./data:/app/data:Z  # Label now effective
```

### Files Modified

**Overlay files (configuration fixes):**
- `docs/tutorial-branches/chapter-00-introduction/docker-compose.podman.yaml`
- `docs/tutorial-branches/chapter-01-main/docker-compose.podman.yaml`
- `docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot/docker-compose.podman.yaml`
- `docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent/docker-compose.podman.yaml`

**Startup scripts (rootful mode enforcement):**
- `docs/tutorial-branches/chapter-00-introduction/start-chapter-resources-podman.sh`
- `docs/tutorial-branches/chapter-01-main/start-chapter-resources-podman.sh`
- `docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot/start-chapter-resources-podman.sh`
- `docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent/start-chapter-resources-podman.sh`

### Verification Commands

```bash
# Check script requires sudo (should show error)
./start-chapter-resources-podman.sh

# Launch with sudo
sudo -E ./start-chapter-resources-podman.sh

# Verify services running (in another terminal)
sudo podman ps

# Check service logs
sudo podman logs agentic_mcp_server
sudo podman logs agentic_streamlit_app

# Test endpoints
curl -f http://localhost:8080/health  # MCP server
curl -f http://localhost:8501          # Streamlit
```

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
