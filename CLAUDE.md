# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ADEPT (Agentic Discovery and Exploration Platform for Tools) is a modular, pedagogical framework for building agentic scientific applications using the Model Context Protocol (MCP) and multiple UI frontends. This is fundamentally a **teaching tool** designed to demonstrate how LLMs, agentic tools, and workflows integrate with scientific computing.

**Key Architecture**: The framework separates concerns across multiple services:
- **MCP Servers** (3 types): Main MCP server, HPC MCP server, Sandbox MCP server - host tools over MCP protocol
- **Agent Orchestration**: Langchain/LangGraph-based agent that uses tools to fulfill user requests
- **UI Frontends**: Streamlit, JupyterLab, OpenWebUI, n8n workflow integration
- **Agent Gateway**: OpenAI-compatible API endpoint that aggregates all services (most advanced architecture)
- **Data Layer**: ChromaDB for RAG/embeddings, SQLite for structured data, Redis for session state

## Development Commands

### Setup
```bash
# Install dependencies (requires Python 3.11)
pip install uv
uv venv .venv --python 3.11
uv sync --all-extras

# Configure environment
cp .env.example .env
# Edit .env with API keys (OPENAI_API_KEY, AZURE_API_KEY, ANTHROPIC_API_KEY, etc.)
```

### Running Services

**Using Docker Compose (recommended)**:
```bash
# Build all services
docker compose build

# Run all services (detached)
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

**Using Podman (Alternative - Chapters 0-3 only)**:
```bash
# Install podman-compose
pip install podman-compose

# Rootless mode (Chapters 0-2)
cd docs/tutorial-branches/chapter-01-main
./start-chapter-resources-podman.sh

# Rootful mode (Chapter 3 - requires sandbox features)
cd docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent
sudo -E ./start-chapter-resources-podman.sh

# Key differences:
# - Uses podman-compose instead of docker compose
# - Overlay file docker-compose.podman.yaml automatically included
# - Chapter 3 requires rootful Podman (sudo -E)
# - SELinux contexts added to volume mounts (:Z suffix)
```

**Local Development (separate terminals)**:
```bash
# Terminal 1: MCP Server
uv run run-mcp-server

# Terminal 2: HPC MCP Server (if needed)
uv run run-mcp-hpc-server

# Terminal 3: Sandbox Server (if needed)
uv run run-sandbox-server

# Terminal 4: Streamlit UI
uv run run-streamlit-harness
# OR: PYTHONPATH=src uv run streamlit run src/agentic_framework_pkg/streamlit_app/app.py
```

### Testing
```bash
# Run tests (when available)
uv run pytest

# Linting with Ruff
ruff check .
ruff format --check .

# Format code
ruff format .
```

### Tutorial Chapters

The repository is organized into progressive tutorial chapters in `docs/tutorial-branches/`:
- **chapter-00**: Introduction with basic tools (RAG, SQL, notes)
- **chapter-01**: Main architecture with Langchain agent
- **chapter-02**: HPC MCP server + LangGraph Chain-of-Thought
- **chapter-03**: Sandbox execution + Multi-agent capabilities
- **chapter-04**: Kubernetes deployment with Helm
- **chapter-05**: OpenWebUI integration
- **chapter-06**: Agent Gateway with dynamic tool registration via stdio

Each chapter has its own `start-chapter-resources.sh` script.

## Architecture Patterns

### MCP Tool Registration
Tools are registered in MCP servers using `@mcp.tool()` decorator:

1. Create tool file in `src/agentic_framework_pkg/mcp_server/tools/your_tool.py`
2. Define `register_tools(mcp: FastMCP)` function
3. Register in `src/agentic_framework_pkg/mcp_server/main.py`

Tools must accept `ctx: Context` and optionally `mcp_session_id: Optional[str]`.

### Langchain Tool Wrappers
MCP tools are wrapped for Langchain in `src/agentic_framework_pkg/scientific_workflow/mcp_langchain_tools.py`:

1. Define Pydantic input schema
2. Create `MCPToolWrapper` instance pointing to MCP server endpoint
3. Add to agent's tool list in `langchain_agent.py`

### LLM Agnostic Layer
`LLMAgnosticClient` in `core/llm_agnostic_layer.py` provides unified interface for:
- OpenAI, Azure OpenAI, NVIDIA NIMs, Ollama
- Text generation via LiteLLM
- Embeddings for RAG
- Configured entirely via environment variables

### Multi-Agent Orchestration
Two modes available in `multi_agent_tool.py`:
- **Router Mode**: Static plan created by Planner, executed by Supervisor with worker delegation
- **Graph Mode**: Dynamic LangGraph-based state machine with adaptive task routing

### Agent Gateway (Chapter 6)
Most advanced pattern:
- Single OpenAI-compatible API (`/v1/chat/completions`) for all frontends
- Dynamic tool registration via stdio protocol (any CLI tool/Docker container)
- Centralized vector database server
- Keycloak authentication support
- Redis-based session checkpointing

## Docker Compose Files

Projects may have multiple compose files:
- `docker-compose.yaml`: Base services (MCP servers, Streamlit, ChromaDB)
- `docker-compose-openwebui.yaml`: OpenWebUI backend service
- `docker-compose-hpc.yaml`: HPC-specific services
- `docker-compose-jupyterlab.yaml`: JupyterLab interface
- `docker-compose-n8n.yaml`: n8n workflow automation
- `docker-compose-redis.yaml`: Redis for state management

Use multiple files: `docker compose -f docker-compose.yaml -f docker-compose-openwebui.yaml up -d`

## Key Files and Structure

```
src/agentic_framework_pkg/
├── core/
│   ├── llm_agnostic_layer.py      # LLM abstraction layer (LiteLLM/Azure SDK)
│   └── logger_config.py            # Centralized logging
├── mcp_server/                     # Main MCP tool server
│   ├── main.py                     # Server entry point, tool registration
│   ├── server.py                   # FastMCP server setup
│   ├── state_manager.py            # Session/DB initialization
│   ├── vector_state_manager.py     # ChromaDB logic for RAG
│   └── tools/                      # Individual tool implementations
├── hpc_mcp_server/                 # HPC tools (Nextflow, Whisper, GitXRay)
├── sandbox_mcp_server/             # Code execution in nsjail sandbox
├── scientific_workflow/            # Langchain agent orchestration
│   ├── langchain_agent.py          # Main agent class
│   ├── mcp_langchain_tools.py      # Langchain tool wrappers
│   ├── graph_builder.py            # Custom StateGraph for split-stream
│   └── agent_state.py              # Agent state type definitions
├── streamlit_app/                  # Streamlit UI frontend
├── agent_gateway/                  # OpenAI-compatible gateway (ch. 6)
├── openwebui_mcp_backend/          # OpenAPI tool proxy for OpenWebUI
└── vector_db_server/               # Standalone ChromaDB server
```

## Important Environment Variables

```bash
# LLM Provider Keys
OPENAI_API_KEY=
AZURE_API_KEY=
AZURE_API_BASE=
ANTHROPIC_API_KEY=
NVIDIA_API_KEY=

# Model Configuration
LANGCHAIN_LLM_MODEL=gpt-4o-mini
EMBEDDING_DEFAULT_MODEL=text-embedding-3-small
RAG_DEFAULT_MODEL=gpt-4o-mini

# MCP Server URLs (internal Docker networking)
MCP_SERVER_URL=http://mcp_server:8080/mcp
HPC_MCP_SERVER_URL=http://hpc_mcp_server:8081/mcp
SANDBOX_MCP_SERVER_URL=http://sandbox_mcp_server:8082/mcp

# Data Persistence
CHROMA_DB_PATH=./data/persistent_chroma_db  # Or :memory: for ephemeral
VECTOR_DB_URL=http://vector_db_server:8001  # For standalone ChromaDB

# Server Ports
MCP_SERVER_PORT=8080
HPC_MCP_SERVER_PORT=8081
STREAMLIT_SERVER_PORT=8501
AGENT_GATEWAY_PORT=8081  # Exposed as 8083 in docker-compose

# Agent Gateway (Chapter 6)
AGENT_GATEWAY_AUTH_ENABLED=true
REDIS_URL=redis://redis:6379/0
KEYCLOAK_URL=http://keycloak:8180

# Debugging
LITELLM_VERBOSE=False
LOG_LEVEL=INFO
```

## Security Notes

- **Sandbox Server**: Runs with `privileged: true` in Docker for nsjail sandboxing. Understand security implications before production use.
- **Platform Architecture**: Some services may specify `platform: linux/amd64`. Remove this line on ARM-based machines (Apple Silicon) to build native images.
- **Secrets**: Use `.env` file (gitignored). Never commit API keys. GitLab CI includes TruffleHog secret scanning.

## Adding a New Tool

1. **Create Tool File**: `src/agentic_framework_pkg/mcp_server/tools/my_tool.py`
   ```python
   from fastmcp import FastMCP, Context
   from typing import Optional, Dict, Any

   def register_tools(mcp: FastMCP):
       @mcp.tool()
       async def my_tool_name(ctx: Context, param: str, mcp_session_id: Optional[str] = None) -> Dict[str, Any]:
           """Tool description for LLM."""
           await ctx.info(f"Executing my_tool with {param}")
           # Implementation
           return {"result": "success"}
   ```

2. **Register in MCP Server**: `src/agentic_framework_pkg/mcp_server/main.py`
   ```python
   from .tools import my_tool

   def setup_mcp_server():
       my_tool.register_tools(mcp)
   ```

3. **Create Langchain Wrapper**: `src/agentic_framework_pkg/scientific_workflow/mcp_langchain_tools.py`
   ```python
   from pydantic import BaseModel, Field

   class MyToolInput(BaseModel):
       param: str = Field(description="Description for LLM")
       mcp_session_id: Optional[str] = Field(default=None)

   def get_mcp_my_tool_langchain(mcp_server_url: str, mcp_session_id: str) -> MCPToolWrapper:
       return MCPToolWrapper(
           name="my_tool_name",
           description="Tool description",
           mcp_server_url=mcp_server_url,
           mcp_tool_name="my_tool_name",
           args_schema=MyToolInput,
           default_session_id=mcp_session_id
       )
   ```

4. **Add to Agent**: `src/agentic_framework_pkg/scientific_workflow/langchain_agent.py`
   ```python
   from .mcp_langchain_tools import get_mcp_my_tool_langchain

   # In ScientificWorkflowAgent.__init__:
   tools.append(get_mcp_my_tool_langchain(mcp_server_url, session_id))
   ```

## Testing Patterns

- Tests are located in `tests/` directories (e.g., `chapter-06-*/tests/`)
- Use `pytest` with `pytest-asyncio` for async tests
- Mock MCP server responses when testing Langchain wrappers
- Test tool registration independently from agent integration

## Kubernetes Deployment

Helm charts are in `infra/helm/`:
```bash
# Install to local cluster (Docker Desktop)
helm install adept-framework ./infra/helm -f ./infra/helm/values-local.yaml

# Access via port-forward
kubectl port-forward svc/streamlit-app 8501:8501
```

See `infra/helm/README.md` for detailed deployment instructions.

## Common Gotchas

- **Port conflicts**: Default ports are 8080 (MCP), 8081 (HPC), 8082 (Sandbox), 8501 (Streamlit). Adjust if already in use.
- **WSL vs native paths**: When using WSL on Windows, ensure Docker Desktop is configured for WSL 2 backend.
- **ChromaDB persistence**: Path `./data/persistent_chroma_db` is relative to where the server runs (container working dir or local dir).
- **Session IDs**: `mcp_session_id` is critical for stateful tools. Always pass through from UI to agent to tools.
- **LiteLLM model names**: Use format like `azure/deployment-name` or `ollama/model-name` when configuring models.
- **Environment loading**: `.env` file must be in project root. Some services load it explicitly via `python-dotenv`.

## Support and Documentation

- Full tutorial: `docs/agentic-framework-tutorial.md`
- Tool user guide: `docs/agentic-framework-tool-user-guide.md`
- Sample queries: `docs/agentic-framework-user-queries.md`
- Local development: `docs/local_development.md`
- Helm deployment: `infra/helm/README.md`
- Report issues: GitHub Issues (link in README)
