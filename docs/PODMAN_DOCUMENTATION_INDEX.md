# Podman Documentation Index

**Purpose:** Central index for all Podman-related documentation
**Last Updated:** 2026-02-09
**Status:** Complete implementation, testing in progress

---

## Quick Navigation

### For Platform Engineers/System Administrators

**Starting from scratch?**
→ **[PLATFORM_ENGINEER_FROM_SCRATCH.md](PLATFORM_ENGINEER_FROM_SCRATCH.md)** ⭐ START HERE

**Already have a system configured?**
→ [PLATFORM_ENGINEER_ONBOARDING.md](PLATFORM_ENGINEER_ONBOARDING.md)

**Quick reference for commands?**
→ [PODMAN_QUICKSTART.md](PODMAN_QUICKSTART.md)

### For Developers

**Want to understand what changed?**
→ [PODMAN_BUGFIX_PROCESS.md](PODMAN_BUGFIX_PROCESS.md)

**Need implementation details?**
→ [PODMAN_IMPLEMENTATION_PROGRESS.md](PODMAN_IMPLEMENTATION_PROGRESS.md)

**Historical context?**
→ [PODMAN_BOOTSTRAP_NOTES.md](PODMAN_BOOTSTRAP_NOTES.md)

### For Users

**Comprehensive deployment guide?**
→ [podman-deployment-guide.md](podman-deployment-guide.md)

**Chapter-specific instructions?**
→ Chapter READMEs in `tutorial-branches/chapter-XX-*/README.md`

---

## Documentation Overview

### 1. PLATFORM_ENGINEER_FROM_SCRATCH.md ⭐
**Audience:** System administrators, platform engineers
**Purpose:** Complete deployment guide from a fresh system
**Use when:** Setting up ADEPT Framework with Podman for the first time

**Contents:**
- Prerequisites check and system preparation
- Step-by-step Podman installation
- Registry configuration (Docker Hub setup)
- Environment setup and bootstrapping
- Chapter deployment procedures
- Verification and testing steps
- Comprehensive troubleshooting
- Maintenance and operational guidance

**Time to deploy:** 30-45 minutes with this guide

**Key features:**
- Detects network/LDAP users automatically
- Explains why rootful mode is needed
- Provides exact commands for each step
- Includes verification at every stage
- Troubleshoots 7 common issues
- Production-ready checklist

---

### 2. PODMAN_BUGFIX_PROCESS.md
**Audience:** Developers, DevOps engineers, technical leads
**Purpose:** Documents the implementation methodology and process

**Contents:**
- Problem statement and root cause analysis
- Discovery process (test-driven approach)
- 8 issues discovered and how each was fixed
- Testing methodology and test log
- Lessons learned (technical and process)
- What worked well, what could improve
- Rollback procedures

**Key insights:**
- How network user UID limitation was discovered
- Why PATH preservation is critical with sudo
- Registry search order issue and solution
- Iterative testing approach
- Documentation-driven development

**Use when:**
- Understanding technical decisions
- Learning from implementation process
- Planning similar migrations
- Training team on methodology

---

### 3. PODMAN_IMPLEMENTATION_PROGRESS.md
**Audience:** Project managers, technical leads
**Purpose:** Detailed progress tracking and status

**Contents:**
- Implementation checklist (phases 1-4)
- Configuration issues fixed (8 total)
- File changes summary (20 files)
- Test results and verification
- Success criteria
- Known limitations
- Next steps

**Use when:**
- Tracking implementation status
- Reporting progress to stakeholders
- Understanding scope of changes
- Planning testing activities

---

### 4. PODMAN_BOOTSTRAP_NOTES.md
**Audience:** All users
**Purpose:** Historical record of installation and issues encountered

**Contents:**
- System information
- Installation steps
- Storage configuration issues
- Subuid/subgid configuration
- newuidmap errors and resolution
- Configuration fixes applied
- Testing results
- Usage instructions

**Use when:**
- Understanding historical context
- Troubleshooting similar issues
- Learning about environment-specific problems
- Referencing past solutions

---

### 5. podman-deployment-guide.md
**Audience:** All users
**Purpose:** Comprehensive deployment and usage guide

**Contents:**
- Why Podman vs Docker
- Installation instructions (multiple platforms)
- Chapter compatibility matrix
- Rootless vs rootful mode explanation
- Step-by-step setup
- Known issues and limitations (numbered)
- Performance considerations
- Migration from Docker
- Troubleshooting (extensive)
- FAQ

**Use when:**
- Need comprehensive reference
- Comparing Docker and Podman
- Understanding architecture choices
- Deep-diving into specific topics

---

### 6. PODMAN_QUICKSTART.md
**Audience:** Experienced users
**Purpose:** Quick reference for common operations

**Contents:**
- Prerequisites
- Installation (condensed)
- Bootstrap process
- Launch commands (all chapters)
- Separate commands for standard vs network users
- Troubleshooting (concise)

**Use when:**
- Already familiar with Podman
- Need quick command reference
- Launching specific chapters
- Quick troubleshooting

---

### 7. PLATFORM_ENGINEER_ONBOARDING.md
**Audience:** Platform engineers joining the project
**Purpose:** Onboarding guide with architecture overview

**Contents:**
- ADEPT Framework overview
- Architecture summary
- Environment prerequisites
- Docker and Podman setup options
- Deployment procedures
- Operational tasks
- Monitoring and logging
- Troubleshooting decision tree
- Security considerations
- Performance tuning

**Use when:**
- Onboarding new platform engineers
- Need architectural context
- Planning operations
- Setting up monitoring

---

### 8. Chapter READMEs
**Location:** `tutorial-branches/chapter-XX-*/README.md`
**Audience:** Chapter users
**Purpose:** Chapter-specific deployment instructions

**Contents:**
- Chapter overview and learning objectives
- Docker deployment instructions
- Podman deployment instructions (with warnings)
- Network user detection and rootful mode
- Verification steps
- Troubleshooting

**Use when:**
- Deploying specific chapters
- Understanding chapter requirements
- Chapter-specific issues

---

## Documentation Relationships

```
Platform Engineer From-Scratch Guide (START HERE)
    ├── References → Platform Engineer Onboarding
    ├── References → Podman Deployment Guide
    ├── References → Podman Quickstart
    └── References → Bootstrap Notes

Bugfix Process Document
    ├── References → Implementation Progress
    ├── Documents → All technical decisions
    └── Explains → Why changes were made

Implementation Progress Tracker
    ├── Tracks → All file changes
    ├── Records → Test results
    └── Links → All other documentation

Bootstrap Notes (Historical)
    ├── Records → Original installation
    ├── Documents → Issues encountered
    └── Tracks → Evolution of solution
```

---

## Common Scenarios

### Scenario 1: Fresh Deployment on New System
**Path:** PLATFORM_ENGINEER_FROM_SCRATCH.md → Test → Success

**Steps:**
1. Read PLATFORM_ENGINEER_FROM_SCRATCH.md
2. Follow prerequisites check
3. Install Podman
4. Run registry configuration
5. Bootstrap environment
6. Deploy Chapter 0
7. Verify all services
8. Success!

**Time:** 30-45 minutes

---

### Scenario 2: Troubleshooting Deployment Issues
**Path:** Check error → PLATFORM_ENGINEER_FROM_SCRATCH.md troubleshooting → podman-deployment-guide.md known issues

**Common issues:**
- PATH not preserved → Use `sudo env "PATH=$PATH"`
- Registry errors → Run `configure-podman-registries.sh`
- newuidmap errors → Must use rootful mode
- Permission errors → Check SELinux labels

**References:**
- PLATFORM_ENGINEER_FROM_SCRATCH.md § Troubleshooting
- podman-deployment-guide.md § Known Issues and Limitations
- PODMAN_QUICKSTART.md § Troubleshooting

---

### Scenario 3: Understanding Why Rootful Mode
**Path:** PODMAN_BOOTSTRAP_NOTES.md → PODMAN_BUGFIX_PROCESS.md

**Key documents:**
1. PODMAN_BOOTSTRAP_NOTES.md § Resolution Update
   - Explains newuidmap limitation
   - Documents testing attempts
2. PODMAN_BUGFIX_PROCESS.md § Problem Statement
   - Root cause analysis
   - Why no workaround exists
3. podman-deployment-guide.md § Known Issues #1
   - Network/LDAP user limitation
   - References to upstream issues

---

### Scenario 4: Training New Team Members
**Path:** Start with overview → Hands-on deployment → Deep dive

**Recommended order:**
1. **Overview:** podman-deployment-guide.md (30 min read)
2. **Hands-on:** PLATFORM_ENGINEER_FROM_SCRATCH.md (45 min deploy)
3. **Architecture:** PLATFORM_ENGINEER_ONBOARDING.md (1 hour)
4. **Deep dive:** PODMAN_BUGFIX_PROCESS.md (optional, 30 min)

**Total time:** 2-3 hours for complete onboarding

---

## Key Concepts Explained

### Network vs Local Users
**Where:** PLATFORM_ENGINEER_FROM_SCRATCH.md, podman-deployment-guide.md

**Key points:**
- Network users have UID > 100000 (LDAP/NIS authentication)
- newuidmap doesn't work with high UIDs
- MUST use rootful Podman for network users
- Check with: `id -u`

### Rootless vs Rootful Podman
**Where:** podman-deployment-guide.md § Rootless vs Rootful Mode

**Key points:**
- Rootless = no sudo, enhanced security
- Rootful = requires sudo, similar to Docker
- Network users can't use rootless (newuidmap limitation)
- Chapter 3 requires rootful for ALL users (sandbox)

### Registry Configuration
**Where:** PLATFORM_ENGINEER_FROM_SCRATCH.md § Podman Configuration

**Key points:**
- Podman searches Red Hat registry first by default
- Docker Hub images won't be found without configuration
- `configure-podman-registries.sh` sets docker.io as primary
- Must run once before deploying chapters

### PATH Preservation with sudo
**Where:** PODMAN_BUGFIX_PROCESS.md § Issue #7

**Key points:**
- sudo resets PATH for security
- podman-compose installed in ~/.local/bin
- Must use: `sudo env "PATH=$PATH"` to preserve
- Scripts attempt auto-restore but explicit is better

---

## File Locations

### Project Root
```
adept-agentic-framework-core/
├── configure-podman-registries.sh (NEW - registry setup)
├── bootstrap-podman-env.sh (Python venv setup)
├── activate-podman-env.sh (helper script)
├── .env (API keys - user creates)
└── .venv-podman/ (Python virtual environment)
```

### Documentation
```
docs/
├── PLATFORM_ENGINEER_FROM_SCRATCH.md (NEW ⭐)
├── PODMAN_BUGFIX_PROCESS.md (NEW)
├── PODMAN_IMPLEMENTATION_PROGRESS.md
├── PODMAN_BOOTSTRAP_NOTES.md
├── podman-deployment-guide.md
├── PODMAN_QUICKSTART.md
├── PODMAN_DOCUMENTATION_INDEX.md (this file)
└── PLATFORM_ENGINEER_ONBOARDING.md (updated)
```

### Chapter Scripts
```
docs/tutorial-branches/
├── chapter-00-introduction/
│   ├── docker-compose.yaml
│   ├── docker-compose.podman.yaml (overlay)
│   ├── start-chapter-resources-podman.sh (updated)
│   └── README.md (updated)
├── chapter-01-main/
│   ├── docker-compose.yaml
│   ├── docker-compose.podman.yaml (overlay)
│   ├── start-chapter-resources-podman.sh (updated)
│   └── README.md (updated)
├── chapter-02-hpc-mcp-server-with-cot/
│   └── ... (same structure)
└── chapter-03-llm-sandbox-and-multi-agent/
    └── ... (same structure)
```

---

## Testing Status

**Current Status:** Implementation complete, testing in progress

**Completed:**
- ✅ All configuration files fixed (8 issues)
- ✅ All startup scripts updated (4 chapters)
- ✅ All documentation written (11 files)
- ✅ Registry configuration script created
- ✅ Error message testing passed

**In Progress:**
- ⏳ Chapter 0 full system test
- ⏳ Services startup verification
- ⏳ Performance benchmarking

**Pending:**
- ⏳ Chapters 1-3 testing
- ⏳ Production deployment validation
- ⏳ User acceptance testing

---

## Quick Command Reference

### One-Time Setup
```bash
# Configure registries (REQUIRED ONCE)
sudo ./configure-podman-registries.sh

# Bootstrap environment (REQUIRED ONCE)
./bootstrap-podman-env.sh
```

### Every Session
```bash
# Activate environment
source .venv-podman/bin/activate

# Launch chapter (network users)
cd docs/tutorial-branches/chapter-XX-name
sudo env "PATH=$PATH" ./start-chapter-resources-podman.sh
```

### Verification
```bash
# Check containers
sudo podman ps

# Check logs
sudo podman logs <container_name>

# Test endpoints
curl http://localhost:8501  # Streamlit
curl http://localhost:8080/health  # MCP Server
```

---

## Support

**Questions about:**
- **Deployment:** See PLATFORM_ENGINEER_FROM_SCRATCH.md
- **Architecture:** See PLATFORM_ENGINEER_ONBOARDING.md
- **Troubleshooting:** See podman-deployment-guide.md § Troubleshooting
- **Commands:** See PODMAN_QUICKSTART.md
- **History:** See PODMAN_BOOTSTRAP_NOTES.md
- **Process:** See PODMAN_BUGFIX_PROCESS.md

**Still stuck?**
1. Check troubleshooting sections in multiple docs
2. Review container logs: `sudo podman logs <container>`
3. Verify configuration: Follow verification steps
4. Create GitHub issue with error logs

---

## Document Maintenance

**When to update this index:**
- New documentation added
- Documentation reorganized
- Major changes to deployment process
- New troubleshooting guides created
- User feedback indicates confusion

**Maintainer:** ADEPT Framework Team
**Last Review:** 2026-02-09
**Next Review:** After testing complete

---

**Navigation:**
- [↑ Back to Main README](../README.md)
- [→ Start Deployment](PLATFORM_ENGINEER_FROM_SCRATCH.md)
- [→ Quick Commands](PODMAN_QUICKSTART.md)
- [→ Full Guide](podman-deployment-guide.md)
