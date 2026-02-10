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

Here's a neat infographic on the MCP protocol:

<img src="docs/images/MCP_Screenshot.png" alt="MCP Protocol" width="50%">

Ref: https://www.dailydoseofds.com/p/visual-guide-to-model-context-protocol-mcp/


### Core Components
The architecture is designed to be modular, allowing for clear separation of concerns from user interaction down to data storage and LLM communication.

1.  **User Interface (Streamlit App - `agentic_framework_pkg.streamlit_app`)**:
    *   Serves as the primary frontend for user interaction.
    *   Provides a chat interface to communicate with the Langchain agent.
    *   Allows users to invoke specific MCP tools directly for testing or specific tasks (e.g., file uploads for RAG).
    *   Configurable via environment variables (e.g., `STREAMLIT_SERVER_PORT`, `MCP_SERVER_URL`).

2.  **Agent Orchestration (Langchain Agent - `agentic_framework_pkg.scientific_workflow.langchain_agent`)**:
    *   The central "brain" of the application, responsible for understanding user queries and orchestrating tool usage to fulfill requests.
    *   Leverages the Langchain framework (specifically `create_openai_tools_agent` or similar) for reasoning and tool dispatch.
    *   Maintains conversation history (with truncation) to provide context for interactions.
    *   Dynamically selects and invokes appropriate tools based on the user's intent and the tools' capabilities.

3.  **Langchain Tool Wrappers (`agentic_framework_pkg.scientific_workflow.mcp_langchain_tools`)**:
    *   Act as bridges or adapters, making MCP-hosted tools compatible with the Langchain agent framework.
    *   The `MCPToolWrapper` class handles the communication layer, invoking tools on the MCP server via HTTP requests.
    *   Define input schemas (using Pydantic) for each tool, ensuring data is correctly structured for both Langchain and the MCP tool.
    *   Manage the propagation of session IDs (`mcp_session_id`) from the agent to the MCP tools, enabling stateful interactions.

4.  **Tool Execution Layer (MCP Server - `agentic_framework_pkg.mcp_server`)**:
    *   A dedicated server (`fastmcp`) that hosts and exposes individual tools over the Multi-Component Protocol (MCP).
    *   Decouples tool implementation from the agent logic, allowing tools to be developed, scaled, and maintained independently.
    *   Manages its own session state and can interact with persistent storage (like ChromaDB for RAG tools).
    *   Configurable via environment variables (e.g., `MCP_SERVER_HOST`, `MCP_SERVER_PORT`).

5.  **Individual Tools (`agentic_framework_pkg.mcp_server.tools`)**:
    *   Modular Python scripts that implement specific functionalities. Examples include:
        *   **`general_tools.py`**: Basic utilities (e.g., datetime, session management helpers).
        *   **`csv_rag_tool.py`**: Handles document (CSV, PDF, DOCX, images) processing for Retrieval Augmented Generation (RAG). It chunks documents, generates embeddings via the `LLMAgnosticClient`, stores them in ChromaDB, and allows querying this indexed data.
        *   **`uniprot_tool.py`**: Interacts with the UniProt biological database API.
        *   **`websearch_tool.py`**: Performs web searches (e.g., using Tavily API).
        *   **`pubchem_tool.py`**: Interacts with the PubChem chemical database API.
        *   **`blast_tool.py`**: Performs biological sequence searches (BLAST).
    *   Each tool is registered with the MCP server and can be invoked remotely.

6.  **LLM Interaction (LLM Agnostic Layer - `agentic_framework_pkg.core.llm_agnostic_layer`)**:
    *   Provides a unified interface for interacting with different Large Language Models (LLMs) for tasks like text generation and embedding creation.
    *   Abstracts away the specifics of different LLM providers (e.g., OpenAI, Azure OpenAI, NVIDIA NIMs, Ollama).
    *   Primarily uses `LiteLLM` for broad compatibility and can also leverage specific SDKs like the Azure OpenAI SDK.
    *   Configured through environment variables, allowing easy switching between models and providers (e.g., `OPENAI_API_KEY`, `AZURE_API_BASE`, `EMBEDDING_DEFAULT_MODEL`, `RAG_DEFAULT_MODEL`, `NVIDIA_API_KEY`).

7.  **Data Persistence & State Management (`agentic_framework_pkg.mcp_server.state_manager`)**:
    *   Manages the storage and retrieval of persistent data, primarily for RAG embeddings and session context.
    *   Utilizes **ChromaDB** as the vector database for storing and querying document embeddings.
    *   Supports both persistent disk storage (configured via `CHROMA_DB_PATH`, defaulting to `./data/persistent_chroma_db` relative to where the server runs) and in-memory operation (`:memory:` for ephemeral storage).
    *   Provides asynchronous functions for database operations, often using `asyncio.to_thread` to bridge synchronous library calls into an async environment.

8.  **Logging (`agentic_framework_pkg.logger_config`)**:
    *   A centralized logging setup to ensure consistent and configurable logging across all components of the framework.

### Setup and Running with Docker Compose

The recommended way to build and run the application is using Docker Compose, which will manage the MCP server and Streamlit app containers.

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

### Alternative: Running with Podman

Podman provides a Docker-compatible interface without requiring a daemon. This chapter fully supports rootless Podman.

1.  **Prerequisites:**
    *   Podman 4.0+ installed
    *   Python 3.9+

2.  **One-Time Setup:**
    Bootstrap the Podman Python environment (from project root):
    ```bash
    cd ../../..  # Navigate to project root
    ./bootstrap-podman-env.sh
    ```

    This creates a virtual environment with:
    - podman Python library
    - podman-compose
    - python-dotenv and other dependencies

3.  **Activate Environment:**
    ```bash
    # From project root
    source .venv-podman/bin/activate
    # OR use helper script:
    source ./activate-podman-env.sh
    ```

4.  **Configuration:**
    *   Same `.env` configuration as Docker (see above)

5.  **Run with Podman:**
    ```bash
    # From chapter directory
    cd docs/tutorial-branches/chapter-01-main
    ./start-chapter-resources-podman.sh
    ```

    The script will:
    - Check for Podman and podman-compose
    - Automatically include Podman-specific overlays
    - Build images and start containers
    - Handle clean shutdown with Ctrl+C

4.  **Access:**
    *   Same endpoints as Docker:
        - Streamlit: http://localhost:8501
        - MCP Server: http://localhost:8080

**Compatibility:**
- ✅ Chapter 1: Full rootless Podman support
- ✅ Chapter 0-2: Full rootless Podman support
- ⚠️ Chapter 3: Requires rootful Podman (use `sudo -E`)

For detailed Podman setup and troubleshooting, see the [Podman Deployment Guide](../../../docs/podman-deployment-guide.md).
    *   To stop the containers:
        ```bash
        docker compose down
        ```

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
3.  **Run Streamlit App:**
    *   Navigate to the project root.
    *   Run the app (ensure `.env` is configured, especially `MCP_SERVER_URL`):
        ```bash
        uv run python -m agentic_framework_pkg.streamlit_app.main
        ```

### Project Structure

```
agentic_framework/
├── Dockerfile.mcp_server
├── Dockerfile.streamlit_app
├── docker-compose.yml # (Assumed to exist for Docker Compose setup)
├── .env.example
├── pyproject.toml
├── uv.lock # (Optional, if generated)
└── src/
    └── agentic_framework_pkg/
        ├── __init__.py
        ├── core/
        │   ├── __init__.py
        │   └── llm_agnostic_layer.py
        ├── logger_config.py
        ├── mcp_server/
        │   ├── __init__.py
        │   ├── main.py
        │   ├── server.py # (Assumed FastMCP server instance)
        │   ├── state_manager.py # ChromaDB state
        │   └── tools/
        │       ├── __init__.py
        │       ├── csv_rag_tool.py
        │       ├── general_tools.py
        │       ├── uniprot_tool.py
        │       └── websearch_tool.py
        ├── scientific_workflow/
        │   ├── __init__.py
        │   ├── langchain_agent.py # Langchain agent logic
        │   └── mcp_langchain_tools.py # Langchain wrappers
        └── streamlit_app/
            ├── __init__.py
            └── main.py # Streamlit app entry point
```

### Extending the Framework

*   **Add New MCP Tools:** Create new modules in `src/agentic_framework_pkg/mcp_server/tools/`, implement functions decorated with `@mcp.tool()`, and register them in `src/agentic_framework_pkg/mcp_server/main.py`.
*   **Add New Langchain Tools:** Create new `MCPToolWrapper` instances and Pydantic schemas in `src/agentic_framework_pkg/scientific_workflow/mcp_langchain_tools.py` for your new MCP tools, and add them to the `tools` list in `ScientificWorkflowAgent`.
*   **Enhance Agent Logic:** Modify `ScientificWorkflowAgent` to handle more complex workflows, add memory, or integrate other Langchain features.
*   **Update Streamlit UI:** Modify `src/agentic_framework_pkg/streamlit_app/main.py` to add new UI elements for interacting with new tools or agent capabilities.
*   **Integrate More LLMs:** The `LLMAgnosticClient` is designed to work with LiteLLM, which supports many providers. Configure new models via environment variables.

```
