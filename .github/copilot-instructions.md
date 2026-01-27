# GitHub Copilot Instructions for ADEPT Agentic Framework

## Project context
This repository hosts **ADEPT**, a pedagogical framework for building agentic scientific applications.
- **Structure**: The codebase is organized as a series of progressive tutorial chapters located in `docs/tutorial-branches/`.
- **No Shared Root Code**: There is no central `src` directory. Each chapter folder (e.g., `chapter-01-main`) is a **completely self-contained project** with its own `src`, `pyproject.toml`, and `docker-compose.yaml`.
- **Primary Stack**: Python 3.11+, FastMCP, LangChain, Streamlit, Docker Compose.

## Architecture & Data Flow
- **Microservices-First**: Applications are composed of loosely coupled Docker containers:
  - **Streamlit App**: The frontend UI (`src/.../streamlit_app`).
  - **MCP Servers**: One or more servers hosting tools (`src/.../mcp_server`).
  - **Auxiliary**: ChromaDB (vector store), LLM Sandbox, HPC gateways.
- **Inter-Service Communication**:
  - The Streamlit app communicates with the Agent via LangChain.
  - The Agent calls tools served by MCP Servers.
  - **Evolution**: Early chapters are simple (App -> 1 Server); later chapters use specialized gateways and orchestrators.

## Development Workflow
1. **Identify the Active Chapter**: Always verify which `chapter-XX` folder is the target. Do not edit across chapters unless explicitly porting features.
2. **Build & Run**:
   - **Docker**: The standard way to run is via the helper script: `./start-chapter-resources.sh` (handles cleanup) or `docker compose up --build`.
   - **Local (uv)**: Uses `uv` for dependency management. Run `uv sync` within a chapter directory to set up the environment.
3. **Environment**:
   - Secrets and config are in `.env` files.
   - **Action**: Always ensure `.env` exists (copy from `.env.example`) before running.

## Coding Conventions
- **Tool Definitions (FastMCP)**:
  - Use `@mcp.tool()` decorator.
  - **Must** use type hints and docstrings (these become the tool schema for the LLM).
  - Return structured data (JSON/Dict) or clear text summaries. Avoid returning raw large blobs unless necessary.
- **Scientific Python**:
  - Use `pathlib` for file paths.
  - External scientific tools (BLAST, RDKit) should be wrapped in `try/except` blocks to prevent server crashes on bad input.
- **Structure**:
  - `src/agentic_framework_pkg/` is the python package root in each chapter.
  - Split logic: `core` (business logic), `mcp_server` (tool definitions), `streamlit_app` (UI).

## Critical Files
- `start-chapter-resources.sh`: Lifecycle script for the chapter (up/down/clean).
- `docker-compose.yaml`: Service definition.
- `pyproject.toml`: Dependencies (managed by `uv`).
