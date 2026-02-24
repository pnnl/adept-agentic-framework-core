# Chapter 03 – Development Summary

This document summarises the changes made to Chapter 03 (_LLM Sandbox and Multi-Agent Capabilities_) beyond its initial scaffold.

---

## 1. Docker Build Fixes

| Issue                                                              | Fix                                                                      |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `openjdk-17-jre-headless` not available on Debian Trixie           | Switched to `openjdk-21-jre-headless` in all Dockerfiles                 |
| `playwright install --with-deps` fails on Debian (Ubuntu-specific) | Removed `--with-deps`; pre-installed required system packages explicitly |

---

## 2. O-Series LLM Compatibility

OpenAI O-series reasoning models (`o1`, `o3`, etc.) reject `temperature=0.0`.  
`langchain_agent.py` was updated to omit the `temperature` parameter entirely when the configured model name starts with `o`.

---

## 3. HPC SSH Tool Integration

The simple SSH-based HPC tool from Chapter 01 was ported into Chapter 03's multi-server architecture.

### What was added

- **`hpc_mcp_server/tools/hpc_ssh_tool.py`** – copied and adapted from Chapter 01; provides three MCP tools:
  - `test_hpc_connection` – verifies SSH connectivity to the remote cluster
  - `submit_slurm_job` – submits a Slurm batch script via SSH
  - `check_slurm_job_status` – polls `sacct`/`squeue` for a job ID
- **`fabric>=3.0.0`** added to `pyproject.toml` for SSH execution
- Tool registered in `hpc_mcp_server/main.py`

### SSH key mounting

Host SSH keys are injected into the HPC container at runtime (never baked into the image):

```
Host machine key → Docker volume mount → /home/appuser/.ssh/hpc_key (read-only)
```

`Dockerfile.hpc` creates `/home/appuser/.ssh/` with correct `700` permissions.  
`docker-compose.yaml` accepts `HPC_SSH_KEY_PATH_HOST` (path on the developer's machine) and mounts it. See [`docs/HPC_SSH_CONFIGURATION.md`](HPC_SSH_CONFIGURATION.md) for the full setup guide.

### Agent access

The three HPC SSH tools were wired into **both** agent surfaces so they are reachable from any entry point:

| File                                         | Change                                                                       |
| -------------------------------------------- | ---------------------------------------------------------------------------- |
| `scientific_workflow/mcp_langchain_tools.py` | Added Pydantic schemas and `get_mcp_*` factory functions for each tool       |
| `mcp_server/tools/multi_agent_tool.py`       | Added tools to `get_all_mcp_tools()` (worker agents)                         |
| `scientific_workflow/langchain_agent.py`     | Added tools to `self.tools` and updated system prompt (main Streamlit agent) |

---

## 4. BLASTp Multi-Database Support

Both BLASTp tool implementations (`blastq_tool.py` via Biopython, `blast_tool.py` via direct NCBI API) already passed the `database` parameter straight to NCBI — so all databases were technically supported from day one.  
The work here was making that capability **visible to the LLM agent**:

- Docstrings in both tool files updated with a comprehensive database list
- Pydantic schema description (`PerformBlastpSearchBiopythonInput`) updated
- LangChain wrapper description updated

**Documented databases:**

| Database             | Description                                                   |
| -------------------- | ------------------------------------------------------------- |
| `nr`                 | Non-redundant protein sequences (default, most comprehensive) |
| `swissprot`          | Curated UniProt/Swiss-Prot (high-quality manual annotations)  |
| `pdb`                | Protein Data Bank (experimentally determined structures)      |
| `refseq_protein`     | NCBI Reference Sequence proteins                              |
| `refseq_select_prot` | Representative RefSeq proteins                                |
| `env_nr`             | Environmental protein sequences                               |
| `pataa`              | Patent protein sequences                                      |

Any valid NCBI protein database name is accepted.

---

## 5. Test Suite

`pytest` configuration added to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "slow: requires Docker containers + internet access",
]
```

### New test class – `TestBlastDatabasesSmoke`

Run with:
```bash
uv run pytest tests/test_mcp_tools_smoke.py::TestBlastDatabasesSmoke -v -m "not slow"
```

| Test                                                     | Tier               | What it checks                                                      |
| -------------------------------------------------------- | ------------------ | ------------------------------------------------------------------- |
| `test_blastp_schema_accepts_all_databases[*]`            | Unit (×7)          | Pydantic schema accepts each documented database                    |
| `test_blastp_schema_default_database_is_nr`              | Unit               | Default database is `nr`                                            |
| `test_blastp_wrapper_description_mentions_all_databases` | Unit               | LangChain wrapper description lists every database                  |
| `test_blastq_passes_database_to_ncbi[*]`                 | Unit (×7)          | Mocked `NCBIWWW.qblast` confirms `database` arg forwarded correctly |
| `test_blastp_swissprot_database_integration`             | Slow (integration) | Real NCBI call against `swissprot`                                  |
| `test_blastp_pdb_database_integration`                   | Slow (integration) | Real NCBI call against `pdb`                                        |
| `test_blastp_refseq_protein_database_integration`        | Slow (integration) | Real NCBI call against `refseq_protein`                             |
| `test_blastp_nr_database_integration`                    | Slow (integration) | Real NCBI call against `nr`                                         |

Async fixture decorators across the full test suite were also corrected from `@pytest.fixture` to `@pytest_asyncio.fixture`.

---

## 6. Documentation Added

| File                               | Contents                                                          |
| ---------------------------------- | ----------------------------------------------------------------- |
| `docs/HPC_SSH_CONFIGURATION.md`    | Full HPC SSH setup guide: env vars, key mounting, troubleshooting |
| `docs/HPC_SSH_TOOL_INTEGRATION.md` | Architecture notes on the tool integration                        |
| `docs/DEVELOPMENT_SUMMARY.md`      | This file                                                         |
