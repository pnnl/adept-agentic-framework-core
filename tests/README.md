# ADEPT Framework Test Suite

This directory contains all test suites for the ADEPT framework.

## Structure

```
tests/
├── podman/                      # Podman deployment tests
│   ├── test-podman-deployment.sh   # Comprehensive test suite
│   ├── quick-test.sh               # Fast smoke tests
│   └── README.md                    # Podman testing guide
└── README.md                    # This file
```

## Test Suites

### Podman Deployment Tests (`podman/`)

Tests for validating Podman deployments across all chapters (0-3).

**Run comprehensive test suite:**
```bash
sudo ./tests/podman/test-podman-deployment.sh [0|1|2|3|all]
```

**Run quick smoke test:**
```bash
./tests/podman/quick-test.sh [0|1]
```

See [tests/podman/README.md](podman/README.md) for detailed documentation.

---

## Future Test Suites

Planned additions:
- `integration/` - Integration tests for tool execution
- `performance/` - Performance benchmarking tests
- `docker/` - Docker deployment tests (comparison)
- `unit/` - Unit tests for Python modules
- `e2e/` - End-to-end workflow tests

---

## Documentation

- [PODMAN_TESTING.md](../docs/PODMAN_TESTING.md) - Comprehensive testing guide
- [PODMAN_IMPLEMENTATION_PROGRESS.md](../docs/PODMAN_IMPLEMENTATION_PROGRESS.md) - Implementation tracking
