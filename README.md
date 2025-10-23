
# ADEPT: Agentic Discovery and Exploration Platform for Tools

ADEPT is a modular framework for building agentic scientific applications using the Model Context Protocol (MCP) and Streamlit. It demonstrates how to integrate LLMs, agentic tools, and workflows for scientific discovery, with a focus on teaching and rapid prototyping.

**Key Features:**
- Modular architecture: Streamlit UI, OpenWebUI backend, MCP tool servers, and Langchain agent orchestration
- Tool wrapping for scientific APIs (BLAST, UniProt, PubChem, RAG, etc.)
- Multi-agent orchestration (static plan and dynamic graph modes)
- LLM-agnostic layer (OpenAI, Azure, NVIDIA, Ollama, etc.)
- Persistent state management with ChromaDB
- **Progressive learning path**: 7 tutorial chapters (0-6) with increasing complexity

For a detailed walkthrough, see the [Agentic Framework Tutorial](docs/agentic-framework-tutorial.md). Each tutorial chapter builds upon the previous one, allowing users to learn progressively from basic concepts to advanced multi-agent orchestration.


---

## Quick Start

**Docker Compose (Recommended):**

1. Copy `.env.example` to `.env` and edit as needed:
    ```bash
    cp .env.example .env
    # Edit .env for API keys and config
    ```
2. Build and run all services:
    ```bash
    docker compose build
    docker compose up -d
    ```
3. Access the Streamlit UI at [http://localhost:8501](http://localhost:8501)

**For OpenWebUI integration and advanced options, see the [tutorial](docs/agentic-framework-tutorial.md).**

**Local Development:**

1. Install Python 3.11+ and `uv`:
    ```bash
    pip install uv
    uv venv .venv --python 3.11
    uv sync --all-extras
    ```
2. Run servers and app (in separate terminals):
    ```bash
    uv run run-mcp-server
    uv run run-streamlit-harness
    ```

---


## Contributing

Contributions are welcome! Please open issues or pull requests for bug fixes, new tools, or documentation improvements. See [local_development.md](docs/local_development.md) for developer setup.

All contributors must follow the [Pacific Northwest National Laboratory](https://www.pnnl.gov/) open source guidelines and include the appropriate [disclaimer](DISCLAIMER) and [license](LICENSE) notices.

---


## Citation

If you use ADEPT in your research, please cite:

> George, A., Bilbao, A., Agarwal, K., Mejia-Rodriguez, D., Samantray, S., Kim, H., Rice, P. S., Jacob, B., Baer, M., Raugei, S., Cheung, M. S., & Rigor, P. (2025). ADEPT: A Pedagogical Framework for Integrating Agentic AI with Deterministic Scientific Workflows. Zenodo. https://doi.org/10.5281/zenodo.17315801

---


## Documentation & Resources

- [Tutorial: Setup, Tool Development, Example Workflows](docs/agentic-framework-tutorial.md)
- [Tool User Guide](docs/agentic-framework-tool-user-guide.md)
- [Sample User Queries](docs/agentic-framework-user-queries.md)
- [Licenses](docs/agentic-framework-licenses.md)
- [Helm/Kubernetes Deployment Guide](infra/helm/README.md)

---

```
