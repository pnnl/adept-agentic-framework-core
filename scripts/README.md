# ADEPT Framework Scripts

Utility scripts for managing the ADEPT framework deployment.

## Available Scripts

### cleanup-stale-processes.sh

**Purpose:** Clean up stale Podman processes and containers from interrupted deployments.

**Usage:**
```bash
sudo ./scripts/cleanup-stale-processes.sh
```

**What it does:**
1. Stops all running Podman containers
2. Removes all containers (running and stopped)
3. Kills stale sudo/podman-compose processes
4. Kills bash processes running startup scripts
5. Verifies complete cleanup

**When to use:**
- After interrupted chapter deployments (Ctrl+C, terminal disconnect)
- When containers from previous runs are still active
- Before starting a new chapter (for clean slate)
- When switching between chapters

**Example output:**
```
Step 1: Stopping all running containers... ✓
Step 2: Removing all containers... ✓
Step 3: Killing stale sudo/podman-compose processes... ✓
Step 4: Killing bash processes running start-chapter scripts... ✓
Step 5: Verifying cleanup... ✓
Cleanup complete!
```

---

## Related Scripts

### Project Root Scripts
- `bootstrap-podman-env.sh` - Bootstrap Podman Python environment (one-time setup)
- `configure-podman-registries.sh` - Configure Docker Hub as primary registry (one-time setup)
- `activate-podman-env.sh` - Activate Podman virtual environment

### Chapter Helper Scripts
Located in `docs/tutorial-branches/chapter-XX-name/`:
- `start-chapter-resources-podman.sh` - Start chapter services
- `check-service-logs.sh` - Monitor logs with error highlighting (Chapter 0)
- `verify-services.sh` - Health checks for all endpoints (Chapter 0)
- `configure-sudo-nopasswd.sh` - Configure passwordless sudo (Chapter 0)

### Test Scripts
Located in `tests/podman/`:
- `test-podman-deployment.sh` - Comprehensive validation suite
- `quick-test.sh` - Fast smoke tests

See [tests/README.md](/tests/README.md) for test suite documentation.

---

## Script Organization

```
adept-agentic-framework-core/
├── scripts/                           # Utility scripts (this directory)
│   ├── cleanup-stale-processes.sh     # Cleanup stale processes
│   └── README.md                      # This file
├── tests/                             # Test suites
│   └── podman/                        # Podman deployment tests
├── bootstrap-podman-env.sh            # Environment bootstrap
├── configure-podman-registries.sh     # Registry configuration
└── docs/tutorial-branches/
    └── chapter-XX-name/
        ├── start-chapter-resources-podman.sh   # Chapter launcher
        └── *.sh                                # Chapter-specific helpers
```

---

## Contributing

When adding new scripts:
- Place utility scripts in `scripts/`
- Place test scripts in `tests/`
- Place chapter-specific scripts in chapter directories
- Make scripts executable: `chmod +x script.sh`
- Update this README with script documentation
