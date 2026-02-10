## Agentic Framework with MCP and Streamlit

This project provides a framework for building agentic applications using the Model Context Protocol (MCP) for tool hosting and a Streamlit application as a user interface harness. It includes components for state management (ChromaDB), LLM interaction (via a LiteLLM/Azure SDK agnostic layer), and tool orchestration (using Langchain).

### Learning Objectives & Scope
It is important to understand the primary purpose of this repository:

* `A Teaching Tool for Scientific Integration`: This framework is fundamentally meant to be a teaching tool. Its main goal is to demonstrate and educate on how Large Language Models (LLMs), agentic tools, and agentic workflows can be practically integrated to support scientific processes. It serves as a hands-on guide for researchers, students, and developers looking to understand the intersection of AI and scientific computing.

<!-- * `Illustrative, Not Prescriptive`: This framework is intended to be illustrative of how existing, codified scientific tools (e.g., BLAST, UniProt APIs) can be wrapped and integrated within a modern, LLM-based reasoning model. As such, the strategic decision of when to use a deterministic, programmatic workflow versus a flexible, agentic one is considered out of scope. The focus here is on the technical "how-to," not the philosophical "why" or "when." -->

* `A Bridging Framework for Interdisciplinary Collaboration`: This framework serves as a practical teaching tool designed to foster a shared understanding of agentic AI systems across diverse teams.

  *  **For Scientific Domain SMEs (Subject Matter Experts)**: It aims to demystify the "black box" of agentic AI. By showcasing how familiar scientific tools (e.g., BLAST, UniProt APIs) are wrapped and utilized by an AI agent, SMEs can better grasp the agent's capabilities and limitations. This, in turn, empowers them to more effectively articulate the functional requirements and nuances of their scientific tools and techniques for successful integration.

  *  **For Software/Data Engineers and Data Scientists**: It provides a tangible, illustrative mechanism for understanding the complexities involved in integrating specialized scientific software and analytical tools into an LLM-based agentic framework. It highlights patterns for tool wrapping, state management, and agent orchestration, offering a clear pathway for discussing and implementing robust integrations.

<!-- * `A Teaching Tool for Scientific Integration`: This framework is fundamentally meant to be a teaching tool. Its main goal is to demonstrate and educate on how Large Language Models (LLMs), agentic tools, and agentic workflows can be practically integrated to support scientific processes. It serves as a hands-on guide for researchers, students, and developers looking to understand the intersection of AI and scientific computing. -->

* `Establishing Common Vocabulary and Expectations`: By providing a concrete example, this framework helps establish a common vocabulary around agentic systems, tool integration, and LLM interactions. This facilitates clearer communication and sets realistic expectations regarding the functionality, complexity, and potential of such systems within a scientific context.

* `Illustrative of "How-To," Not Prescriptive of "When-To"`: The framework is intended to be illustrative, demonstrating *how* existing, codified scientific tools (e.g., BLAST, UniProt APIs) can be wrapped and integrated within a modern, LLM-based reasoning model. It focuses on the technical implementation ("how-to") rather than offering prescriptive guidance on *when* to choose an agentic approach over a deterministic, programmatic workflow. That strategic decision remains out of scope.

### Tutorial

For a detailed walkthrough on setting up the development environment, adding a new tool, and running an example workflow, please refer to the [Agentic Framework Tutorial](docs/agentic-framework-tutorial.md).

### What is MCP (Model Context Protocol)

Here's a neat infographic on the MCP protocol and exemplar set of multi-agent architectures:

<img src="docs/images/MCP_Screenshot.png" alt="MCP Protocol" width="50%">

Ref: https://www.dailydoseofds.com/p/visual-guide-to-model-context-protocol-mcp/

<img src="docs/images/multi-agent-architectures.png" alt="Multi-agent architectures" width="50%">

Ref: https://langchain-ai.github.io/langgraph/concepts/multi_agent/#multi-agent-architectures

### Core Components
The architecture is designed to be modular, allowing for clear separation of concerns from user interaction down to data storage and LLM communication.

1.  **User Interface (Streamlit App - `agentic_framework_pkg.streamlit_app`)**:
    *   Serves as the primary frontend for user interaction.
    *   Provides a chat interface to communicate with the Langchain agent.
    *   Allows users to invoke specific MCP tools directly for testing or specific tasks (e.g., file uploads for RAG).
    *   Configurable via environment variables (e.g., `STREAMLIT_SERVER_PORT`, `MCP_SERVER_URL`).

2.  **Agent Orchestration (Langchain Agent - `agentic_framework_pkg.scientific_workflow.langchain_agent`)**:
    *   The central "brain" of the application, responsible for understanding user queries and orchestrating tool usage to fulfill requests.
    *   Leverages the Langchain framework (specifically `langgraph.prebuilt.create_react_agent`) for reasoning and tool dispatch.
    *   Maintains conversation history (with truncation) to provide context for interactions.
    *   Dynamically selects and invokes appropriate tools based on the user's intent and the tools' capabilities.

3.  **Langchain Tool Wrappers (`agentic_framework_pkg.scientific_workflow.mcp_langchain_tools`)**:
    *   Act as bridges or adapters, making MCP-hosted tools compatible with the Langchain agent framework.
    *   The `MCPToolWrapper` class handles the communication layer, invoking tools on the MCP server via HTTP requests.
    *   Define input schemas (using Pydantic) for each tool, ensuring data is correctly structured for both Langchain and the MCP tool.
    *   Manage the propagation of session IDs (`mcp_session_id`) from the agent to the MCP tools, enabling stateful interactions.

4.  **Tool Execution Layer (MCP Servers)**:
    *   **Main MCP Server (`agentic_framework_pkg.mcp_server`)**:
        *   A dedicated server (`fastmcp`) that hosts and exposes a wide range of individual tools over the Model Context Protocol (MCP).
        *   Decouples tool implementation from the agent logic, allowing tools to be developed, scaled, and maintained independently.
        *   Manages its own session state and can interact with persistent storage (like ChromaDB for RAG tools).
        *   Hosts the sophisticated multi-agent session management tools.
    *   **HPC MCP Server (`agentic_framework_pkg.hpc_mcp_server`)**:
        *   A separate `fastmcp` server designed to host tools requiring more intensive computational resources or specific environments (e.g., Nextflow, local BLAST, Whisper).
        *   Runs as a distinct service, often in its own container with specialized dependencies.
        *   Can also interact with the `LLMAgnosticClient` for tasks like summarization post-HPC processing.
        *   Configurable via environment variables (e.g., `HPC_MCP_SERVER_HOST`, `HPC_MCP_SERVER_PORT`).
    *   **Sandbox MCP Server (`agentic_framework_pkg.sandbox_mcp_server`)**:
        *   A highly specialized `fastmcp` server designed to execute arbitrary Python code in a secure, isolated environment using the `llm-sandbox` library.
        *   This server runs in a container with elevated privileges (`privileged: true` in Docker Compose) to enable the `nsjail` sandboxing mechanism. This has significant security implications and should be used with caution.
        *   Allows the agent to perform dynamic calculations, data manipulation, or any task that can be solved with code, without compromising the host system.

5.  **Individual Tools (`agentic_framework_pkg.mcp_server.tools` and `agentic_framework_pkg.hpc_mcp_server.tools`)**:
    *   Modular Python scripts that implement specific functionalities. Examples include:
        *   **Document RAG (`csv_rag_tool.py`)**: Handles document (CSV, PDF, DOCX, images) processing for Retrieval Augmented Generation. It chunks documents, generates embeddings, stores them in ChromaDB, and allows querying of the indexed data.
        *   **Web Browsing (`websearch_tool.py`)**: Performs web searches using Playwright for robust, modern browser automation.
        *   **Code Execution (`code_execution_tool.py`)**: Executes Python, JavaScript, or shell code in a secure `nsjail` sandbox via the `llm-sandbox` library.
        *   **Scientific Database APIs**: Tools for interacting with public databases like UniProt (`uniprot_tool.py`), PubChem (`pubchem_tool.py`), and NCBI BLAST (`blastq_tool.py` using Biopython).
        *   **Materials Science (`jarvis_alignn_tool.py`) [in-progress]**: Predicts material properties from crystal structures using the ALIGNN model.
        *   **HPC Pipeline Wrappers**:
            *   `nextflow_blast_tool.py`: Wraps a Nextflow pipeline for running large-scale BLAST searches.
            *   `video_processing_tool.py`: Wraps a pipeline for video/audio download, transcription (Whisper), summarization, and RAG indexing.
        *   **Multi-Agent Orchestration (`multi_agent_tool.py`)**: A sophisticated suite of tools for managing teams of AI agents. This includes creating sessions, generating plans with a dedicated "Planner" agent, allowing for human-in-the-loop plan editing and approval, executing the plan with a "Supervisor" agent, listing active sessions, and terminating them.
    *   Each tool is registered with the MCP server and can be invoked remotely.

6.  **LLM Interaction (LLM Agnostic Layer - `agentic_framework_pkg.core.llm_agnostic_layer`)**:
    *   Provides a unified interface for interacting with different Large Language Models (LLMs) for tasks like text generation and embedding creation.
    *   Abstracts away the specifics of different LLM providers (e.g., OpenAI, Azure OpenAI, NVIDIA NIMs, Ollama).
    *   Primarily uses `LiteLLM` for broad compatibility and can also leverage specific SDKs like the Azure OpenAI SDK.
    *   Configured through environment variables, allowing easy switching between models and providers (e.g., `OPENAI_API_KEY`, `AZURE_API_BASE`, `EMBEDDING_DEFAULT_MODEL`, `RAG_DEFAULT_MODEL`, `NVIDIA_API_KEY`).

7.  **Data Persistence & State Management (`agentic_framework_pkg.mcp_server.state_manager`)**:
    *   Manages the storage and retrieval of persistent data, primarily for RAG embeddings and session context.
    *   Utilizes **ChromaDB** as the vector database for storing and querying document embeddings.
    *   Supports persistent disk storage (configured via `CHROMA_DB_PATH`, defaulting to `./data/persistent_chroma_db` relative to where the server runs).
    *   Provides asynchronous functions for database operations, often using `asyncio.to_thread` to bridge synchronous library calls into an async environment.

8.  **Logging (`agentic_framework_pkg.logger_config`)**:
    *   A centralized logging setup to ensure consistent and configurable logging across all components of the framework.

### Setup and Running with Docker Compose

The recommended way to build and run the application is using Docker Compose, which will manage the MCP servers (webservice database query and HPC tools) and Streamlit app containers.
The `docker-compose.yml` in the project root defines the services, their shared volumes, and network settings.

1.  **Prerequisites:**
    *   Docker and Docker Compose installed.
    *   Python 3.11 or higher (for local development setup, though Docker handles this).
    *   `uv` installed (for local development setup, though Docker handles this).

2.  **Configuration:**
    *   Copy the `.env.example` file to `.env` in the project root:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file to configure:
        *   LLM credentials (OpenAI, Azure, etc.) and default models.
        *   `CHROMA_DB_PATH` for persistent ChromaDB storage (or `:memory:` for ephemeral).
        *   `MCP_SERVER_URL_FOR_LANGCHAIN` in the Streamlit container's environment to point to the MCP server service (e.g., `http://mcp_server:8080/mcp` if your service is named `mcp_server`).
        *   **Security Note**: The `sandbox_mcp_server` in `docker-compose.yml` runs with `privileged: true`. This is necessary for the `llm-sandbox` to function but reduces container isolation. Understand the risks before deploying in a production environment.
        *   Other server/app ports if needed.

3.  **Build and Run:**
    *   Navigate to the project root directory in your terminal.
    *   Build the Docker images:
        ```bash
        docker compose build
        ```
    *   Launch the containers (in detached mode):
        ```bash
        docker compose up -d
        ```
    *   To view logs:
        ```bash
        docker compose logs -f
        ```
    *   To stop the containers:
        ```bash
        docker compose down
        ```

### Alternative: Running with Podman

**Podman** provides a Docker-compatible container runtime without requiring a daemon. Chapter 3 supports Podman but requires **rootful mode** due to sandbox security requirements.

**One-Time Setup:**
Bootstrap the Podman Python environment (from project root):
```bash
cd ../../..  # Navigate to project root
./bootstrap-podman-env.sh

# Activate environment
source .venv-podman/bin/activate
# OR: source ./activate-podman-env.sh
```

**Quick Start:**
```bash
# From this chapter directory (with environment activated)
# Chapter 3 REQUIRES rootful Podman (sudo)
sudo -E ./start-chapter-resources-podman.sh
```

**Requirements:**
- Podman 4.0+
- Python 3.9+ (for bootstrap script)
- **Root access** (sudo) for sandbox features

**⚠️ Security Note:**
Chapter 3's sandbox server uses `nsjail` which requires privileged container mode. This must run with rootful Podman (sudo). Only use in trusted development environments.

**Compatibility:**
- ✅ Chapters 0-2: Full rootless Podman support
- ⚠️ Chapter 3: Requires rootful Podman (`sudo -E`)

**Alternative:** If uncomfortable with rootful mode, use Docker for Chapter 3:
```bash
./start-chapter-resources.sh
```

For detailed Podman setup, security implications, and troubleshooting, see the [Podman Deployment Guide](../../../docs/podman-deployment-guide.md).

### Local Development (Alternative)

You can also run the components locally, but you'll need to manage dependencies and separate processes yourself.

1.  **Install Dependencies:**
    *   Ensure you have Python 3.11+ and `uv`.
    *   Navigate to the project root.
    *   Install dependencies:
        ```bash
        pip install uv
        uv venv .venv --python 3.11
        uv sync --all-extras
        ```
2.  **Run MCP Server:**
    *   Navigate to the project root.
    *   Run the server (ensure `.env` is configured):
        ```bash
        uv run python -m agentic_framework_pkg.mcp_server.main
        ```
    * Note: if you're already running services in the default port `8080`, you'll encounter a `address already in use` error. Please adjust the code with the appropriate port if needed.
3.  **Run HPC MCP Server:**
    *   Navigate to the project root.
    *   Run the server (ensure `.env` is configured):
        ```bash
        uv run python -m agentic_framework_pkg.hpc_mcp_server.main
        ```
    * Note: if you're already running services in the default port `8081`, you'll encounter a `address already in use` error. Please adjust the code with the appropriate port if needed.
4.  **Run Streamlit App:**
    *   Navigate to the project root.
    *   Run the app (ensure `.env` is configured, especially `MCP_SERVER_URL`):
        ```bash
        uv run python -m agentic_framework_pkg.streamlit_app.main
        ```
    * Note: if you're already running services in the default port `8581`, you'll encounter a `address already in use` error. Please adjust the code with the appropriate port if needed.

### Project Structure

```
agentic_framework/
├── docker-compose.yml # (Required for Docker Compose setup)
├── Dockerfile.mcp_server # Dockerfile for the MCP server
├── Dockerfile.streamlit_app # Dockerfile for main Streamlit UI app that leverages Langchain
├── Dockerfile.hpc # Dockerfile for the HPC MCP Server
├── .env.example # This is just an example file you'll need to copy to `.env` and populate with keys/tokens.
├── pyproject.toml
├── uv.lock # (Optional, if generated)
└── src/
    └── agentic_framework_pkg/
        ├── __init__.py
        ├── core/
        │   ├── __init__.py
        │   └── llm_agnostic_layer.py # Abstraction for different LLM providers
        ├── logger_config.py
        ├── mcp_server/
        │   ├── __init__.py
        │   ├── main.py
        │   ├── server.py
        │   ├── state_manager.py # Session and DB initialization
        │   ├── vector_state_manager.py # ChromaDB logic for RAG
        │   └── tools/
        │       ├── __init__.py
        │       ├── alphafold_tool.py
        │       ├── blastq_tool.py
        │       ├── csv_rag_tool.py
        │       ├── general_tools.py
        │       ├── jarvis_alignn_tool.py
        │       ├── multi_agent_tool.py
        │       ├── pubchem_tool.py
        │       ├── uniprot_tool.py
        │       ├── websearch_tool.py
        ├── hpc_mcp_server/ # New HPC server component
        │   ├── __init__.py
        │   ├── main.py
        │   ├── server.py
        │   └── tools/
        │       ├── __init__.py
        │       ├── gitxray_tool.py
        │       ├── nextflow_blast_tool.py
        │       └── video_processing_tool.py
        ├── sandbox_mcp_server/ # New Sandbox server for code execution
        │   ├── __init__.py
        │   ├── main.py
        │   ├── server.py
        │   └── tools/
        │       └── code_execution_tool.py
        ├── scientific_workflow/
        │   ├── __init__.py
        │   ├── langchain_agent.py # Langchain agent logic
        │   └── mcp_langchain_tools.py # Langchain wrappers
        └── streamlit_app/
            ├── __init__.py
            ├── main.py # Streamlit app entry point (launcher)
            └── app.py  # Main Streamlit application logic
```

### Extending the Framework

*   **Add New MCP Tools:** Create new modules in `src/agentic_framework_pkg/mcp_server/tools/`, implement functions decorated with `@mcp.tool()`, and register them in `src/agentic_framework_pkg/mcp_server/main.py`.
*   **Add New Langchain Tools:** Create new `MCPToolWrapper` instances and Pydantic schemas in `src/agentic_framework_pkg/scientific_workflow/mcp_langchain_tools.py` for your new MCP tools, and add them to the `tools` list in `ScientificWorkflowAgent`.
*   **Enhance Agent Logic:** Modify `ScientificWorkflowAgent` to handle more complex workflows, add memory, or integrate other Langchain features.
*   **Update Streamlit UI:** Modify `src/agentic_framework_pkg/streamlit_app/main.py` to add new UI elements for interacting with new tools or agent capabilities.
*   **Integrate More LLMs:** The `LLMAgnosticClient` is designed to work with LiteLLM, which supports many providers. Configure new models via environment variables.


### Documentation & Demos

Explore the framework's architecture, capabilities, and a detailed scientific use case through our supplementary materials:

-   **Interactive Architecture & Workflow Demo:** Dive into a visual and interactive explanation of how the Agentic Framework operates and orchestrates various tools.
    [Launch Interactive Demo](docs/agentic-framework-page.html)

-   **Whitepaper (PDF):** Read the full technical paper (draft!) detailing the framework's design, components, security considerations, and future directions.
    [Download Whitepaper PDF](docs/whitepaper/agentic-framework-paper.pdf)

-   **Sample Queries:** Review and use these [sample queriestext](docs/agentic-framework-user-queries.md) as you explore the codebase and interact with the framework.

###

```