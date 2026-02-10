# ADEPT Framework: Building Agentic Scientific Applications
## 2-Hour Workshop

**Workshop Overview:**
- **Duration:** 2 hours (120 minutes)
- **Format:** Presentation + Hands-on
- **Target Audience:** Scientists, researchers, platform engineers, developers
- **Prerequisites:** Basic Python knowledge, familiarity with containers (Docker/Podman)

---

## Workshop Outline

| Section | Topic | Duration | Type |
|---------|-------|----------|------|
| 1 | Introduction & Setup | 15 min | Lecture + Setup |
| 2 | What is ADEPT? Architecture Overview | 15 min | Lecture |
| 3 | Hands-on: Getting Started (Chapter 0) | 25 min | Lab |
| 4 | MCP Tools & Agent Orchestration | 20 min | Lecture + Demo |
| 5 | Hands-on: Running Scientific Workflows | 20 min | Lab |
| 6 | Advanced Features & Deployment | 15 min | Lecture |
| 7 | Q&A and Next Steps | 10 min | Discussion |

**Total:** 120 minutes

---

# Section 1: Introduction & Setup
**Duration:** 15 minutes (0:00 - 0:15)

## Slide 1: Welcome
**Title:** Building Agentic Scientific Applications with ADEPT

**Content:**
- Welcome to the ADEPT Framework Workshop
- Today's goal: Understand and deploy agentic systems for scientific discovery
- Hands-on approach: You'll run real workflows by the end

**Speaker Notes:**
- Introduce yourself and your background with agentic systems
- Ask audience about their experience level:
  - Who has worked with LLMs/AI agents?
  - Who has deployed containerized applications?
  - Who works in scientific computing/HPC environments?
- Set expectations: Mix of theory and practice
- Mention that all materials are open source and available

---

## Slide 2: Workshop Agenda
**Title:** What We'll Cover Today

**Content:**
1. ✅ Setup & Introduction (15 min)
2. 📐 Architecture Overview (15 min)
3. 🔨 Hands-on: Deploy Chapter 0 (25 min)
4. 🛠️ MCP Tools & Agents (20 min)
5. 🧪 Hands-on: Scientific Workflows (20 min)
6. 🚀 Advanced Features (15 min)
7. 💬 Q&A & Next Steps (10 min)

**Speaker Notes:**
- Walk through the agenda quickly
- Emphasize the two hands-on sessions
- Let attendees know they can ask questions anytime
- Mention breaks (if applicable for your format)

---

## Slide 3: Prerequisites Check
**Title:** What You'll Need

**Content:**
**Hardware:**
- Laptop with 8GB+ RAM, 20GB+ disk space
- Internet connection for pulling containers

**Software (Choose Your Path):**
- **Option 1 (Recommended):** Docker Desktop
- **Option 2 (Linux/HPC):** Podman
- Git, Python 3.11+, Terminal/Command Line

**API Keys (Optional for basic demo):**
- OpenAI API key OR
- Azure OpenAI credentials OR
- Local Ollama installation

**Speaker Notes:**
- Do a quick poll: How many have these installed?
- For those without Docker/Podman: They can follow along visually, set up later
- Mention that API keys are optional - Chapter 0 includes Ollama for local testing
- Direct people to setup instructions: `docs/agentic-framework-tutorial.md`
- Share repository URL: https://github.com/pnnl/adept-agentic-framework-core

---

## Slide 4: Quick Setup (Live Demo)
**Title:** Let's Get Started

**Content:**
```bash
# 1. Clone the repository
git clone https://github.com/pnnl/adept-agentic-framework-core.git
cd adept-agentic-framework-core

# 2. Choose your path:

# Docker (macOS/Windows/Linux):
cp .env.example .env
docker compose build

# Podman (Linux/HPC - Chapters 0-3):
sudo ./configure-podman-registries.sh
./bootstrap-podman-env.sh
source .venv-podman/bin/activate
```

**Speaker Notes:**
- Walk through these commands on your screen
- Have attendees start the clone now (it takes time)
- While cloning, explain:
  - Repository structure
  - The .env file purpose (API keys, configuration)
  - Why two paths (Docker vs Podman)
- Mention that build will take 5-10 minutes (we'll do it during next section)
- Start the build process and let it run in background

---

# Section 2: What is ADEPT? Architecture Overview
**Duration:** 15 minutes (0:15 - 0:30)

## Slide 5: The Problem We're Solving
**Title:** Why Agentic Scientific Applications?

**Content:**
**Traditional Scientific Workflows:**
- ❌ Manual data gathering from multiple sources
- ❌ Copy-paste between tools and notebooks
- ❌ Repetitive tasks that could be automated
- ❌ Difficult to reproduce and share

**Agentic Approach:**
- ✅ LLM-powered agent orchestrates tools automatically
- ✅ Natural language queries drive workflows
- ✅ Reproducible, shareable, extensible
- ✅ Scales from laptop to HPC cluster

**Speaker Notes:**
- Share a concrete example:
  - "Imagine asking: 'Find me all proteins related to COVID-19 and their potential drug targets'"
  - Traditional: Hours of manual searching, copy-paste, script writing
  - Agentic: One query, agent uses RAG → BLAST → UniProt → PubChem automatically
- Emphasize that this is about augmenting scientists, not replacing them
- The agent handles the "plumbing," scientist focuses on questions

---

## Slide 6: What is ADEPT?
**Title:** ADEPT: Agentic Discovery and Exploration Platform for Tools

**Content:**
**Key Characteristics:**
- 🎓 **Pedagogical:** Designed for teaching and learning
- 🧩 **Modular:** Swap components easily (LLMs, tools, UIs)
- 🔧 **Tool-Focused:** Everything is exposed as MCP tools
- 📚 **Progressive:** 7 tutorial chapters, increasing complexity
- 🌐 **LLM-Agnostic:** OpenAI, Azure, NVIDIA, Ollama, etc.

**Use Cases:**
- Bioinformatics workflows (BLAST, UniProt, PubChem)
- Document analysis with RAG
- HPC job orchestration
- Multi-agent research tasks

**Speaker Notes:**
- ADEPT is fundamentally a teaching framework
  - Great for prototyping, learning, adapting
  - Production-ready architecture patterns
- Emphasize modularity:
  - Don't like Streamlit? Use OpenWebUI, JupyterLab, or build your own
  - Want different LLM? Just change environment variables
  - Need new tools? Simple plugin architecture
- Developed at Pacific Northwest National Laboratory (PNNL)
- Open source, actively maintained

---

## Slide 7: Architecture Overview
**Title:** ADEPT Architecture - The Big Picture

**Content:**
```
┌─────────────────────────────────────────────────────┐
│                   User Interface                    │
│  Streamlit │ OpenWebUI │ JupyterLab │ n8n          │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Agent Orchestration                    │
│         (Langchain/LangGraph Agent)                 │
│  • Query understanding                              │
│  • Tool selection & execution                       │
│  • Result synthesis                                 │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
│  Main MCP    │ │   HPC    │ │  Sandbox   │
│   Server     │ │MCP Server│ │ MCP Server │
│              │ │          │ │            │
│ • RAG        │ │• Nextflow│ │• Code Exec │
│ • SQL        │ │• GitXRay │ │• Isolated  │
│ • BLAST      │ │• Whisper │ │  Sandbox   │
│ • UniProt    │ │          │ │            │
│ • PubChem    │ │          │ │            │
└──────────────┘ └──────────┘ └────────────┘
        │              │              │
┌───────▼──────────────▼──────────────▼──────┐
│          Data & State Layer                │
│  ChromaDB │ SQLite │ Redis │ File Storage  │
└────────────────────────────────────────────┘
```

**Speaker Notes:**
- Walk through each layer from top to bottom:
  1. **UI Layer:** Multiple frontends, all talk to same backend
  2. **Agent Layer:** The "brain" - decides which tools to use
  3. **MCP Servers:** Three specialized servers hosting tools
     - Main: Core scientific tools
     - HPC: Specialized for HPC environments
     - Sandbox: Safe code execution
  4. **Data Layer:** Persistent storage for embeddings, data, state
- Emphasize separation of concerns:
  - UI doesn't know about tools directly
  - Agent doesn't know how tools are implemented
  - Tools are hot-swappable via MCP protocol
- This is the architecture for Chapters 4-6; simpler versions in 0-3

---

## Slide 8: What is MCP?
**Title:** Model Context Protocol (MCP)

**Content:**
**MCP is an open protocol for connecting LLMs to tools**

**Traditional Approach:**
```python
# Tool tightly coupled to agent
def my_tool(param):
    # Implementation here
    pass

agent.add_tool(my_tool)  # Direct function call
```

**MCP Approach:**
```python
# Tool exposed via HTTP/STDIO
@mcp.tool()
async def my_tool(ctx: Context, param: str):
    # Implementation here
    pass

# Agent calls via protocol
agent.call_tool("my_tool", {"param": "value"})
```

**Benefits:**
- 🔌 **Language-agnostic:** Python, Node.js, Rust, etc.
- 🌐 **Network-accessible:** Tools can be remote services
- 🔒 **Sandboxed:** Tools run in isolated environments
- 📦 **Reusable:** Same tool, multiple agents/UIs

**Speaker Notes:**
- MCP is like REST APIs for AI agents
- Compare to how microservices communicate
- Key insight: Tools don't need to know about the LLM/agent
- This enables:
  - Different teams building different tools
  - Tools in different languages
  - Tools running on different machines
- Anthropic's MCP protocol (open standard)
- Show MCP documentation: https://modelcontextprotocol.io/

---

## Slide 9: Progressive Tutorial Structure
**Title:** Learning Path: 7 Chapters

**Content:**
| Chapter | Focus | Container Support |
|---------|-------|-------------------|
| **0** | Introduction - Core tools (RAG, SQL, BLAST) | Docker, Podman ✅ |
| **1** | Main architecture with Langchain agent | Docker, Podman ✅ |
| **2** | HPC MCP server + Chain-of-Thought | Docker, Podman ✅ |
| **3** | Sandbox execution + Multi-agent | Docker, Podman ✅ |
| **4** | Kubernetes deployment with Helm | Docker only |
| **5** | OpenWebUI integration | Docker only |
| **6** | Agent Gateway + Dynamic tools | Docker only |

**Today's Focus:** Chapters 0-2

**Speaker Notes:**
- Each chapter is a complete, runnable system
- Progressive complexity:
  - Ch 0-1: Basic agentic system
  - Ch 2-3: Advanced features (HPC, multi-agent)
  - Ch 4-6: Production deployment patterns
- Podman support for Ch 0-3 (ideal for HPC/Linux)
- All chapters in separate git directories (`docs/tutorial-branches/`)
- You can run any chapter independently
- Today we'll focus on Chapters 0-2 (most foundational)

---

# Section 3: Hands-on - Getting Started (Chapter 0)
**Duration:** 25 minutes (0:30 - 0:55)

## Slide 10: Chapter 0 Overview
**Title:** Hands-on Lab 1: Deploy Chapter 0

**Content:**
**What's in Chapter 0?**
- 🦙 **Ollama:** Local LLM (llama3.2 3B)
- 🧠 **MCP Server:** Core scientific tools
  - RAG (document Q&A)
  - SQL database queries
  - BLAST protein search
  - UniProt protein info
  - PubChem chemical search
- 🖥️ **Streamlit UI:** Chat interface
- 📓 **JupyterLab:** Notebook interface

**Goal:** Get a working agentic system running locally

**Speaker Notes:**
- This is a complete system you can run on a laptop
- Ollama provides local LLM (no API key needed)
- All tools are functional, not stubs
- Takes 5-10 minutes to start (downloading models)
- Once running, you'll be able to ask scientific questions
- Show the Chapter 0 README quickly: `docs/tutorial-branches/chapter-00-introduction/README.md`

---

## Slide 11: Deployment - Docker Path
**Title:** Lab Instructions: Docker Deployment

**Content:**
```bash
# Navigate to Chapter 0
cd docs/tutorial-branches/chapter-00-introduction

# Configure environment
cp .env.example .env
# Edit .env if you have API keys (optional for Chapter 0)

# Start services (foreground mode)
./start-chapter-resources.sh

# Wait for "All services are ready!"
# Then access:
# • Streamlit UI: http://localhost:8501
# • MCP Server: http://localhost:8080
# • JupyterLab: http://localhost:8888
```

**Expected Output:**
```
Starting Chapter 0 resources...
Building images...
Starting containers...
✓ Ollama model loaded (llama3.2:3b)
✓ MCP Server ready
✓ Streamlit App ready
All services are ready!
```

**Speaker Notes:**
- Walk through this step-by-step on your screen
- Start the deployment now (while you talk)
- Explain what's happening:
  - Script checks for old containers, cleans them
  - Builds Docker images (first time: 5-10 min)
  - Starts services in dependency order
  - Pulls Ollama model (first time: 2-3 min)
- Show Docker Desktop (if using) with containers running
- Troubleshooting tips:
  - Port conflicts: Change ports in docker-compose.yaml
  - Build failures: Check Docker memory limits (need 4GB+)

---

## Slide 12: Deployment - Podman Path (Linux/HPC)
**Title:** Lab Instructions: Podman Deployment

**Content:**
```bash
# One-time setup (if not done earlier)
sudo ./configure-podman-registries.sh
./bootstrap-podman-env.sh
source .venv-podman/bin/activate

# Navigate to Chapter 0
cd docs/tutorial-branches/chapter-00-introduction

# Start services
# Standard users (UID < 100000):
./start-chapter-resources-podman.sh

# Network/LDAP users (UID > 100000):
sudo -E ./start-chapter-resources-podman.sh

# Access same URLs as Docker
```

**Podman Notes:**
- ✅ Daemon-less, rootless capable
- ✅ Ideal for HPC environments
- ✅ Docker-compatible commands
- ⚠️ Chapters 0-3 only

**Speaker Notes:**
- If you're on Linux, demonstrate Podman path
- Explain the UID check: `id -u`
  - < 100000: Local user (rootless works)
  - > 100000: Network/LDAP user (need rootful)
- Show bootstrap output quickly
- Mention that Podman and Docker achieve the same result
- For this workshop, either path works
- If attendees have issues, they can use the other path

---

## Slide 13: Verification & Testing
**Title:** Verify Your Deployment

**Content:**
**Check Container Status:**
```bash
# Docker:
docker ps

# Podman:
podman ps

# Expected: 4 containers running
# - ollama_ch00
# - agentic_mcp_server_ch00
# - agentic_streamlit_app_ch00
# - agentic_jupyterlab_ch00
```

**Test Endpoints:**
```bash
# Ollama
curl http://localhost:11434/api/tags

# MCP Server
curl http://localhost:8080/health

# Open browser: http://localhost:8501
```

**Automated Tests (Optional):**
```bash
# Docker:
./verify-services.sh

# Podman:
sudo -E ./tests/podman/quick-test.sh 0
```

**Speaker Notes:**
- Show `docker ps` or `podman ps` output
- All containers should be "Up" status
- Walk through opening Streamlit in browser
- Show the Streamlit interface:
  - Chat input at bottom
  - Session management on sidebar
  - Model selection (should show llama3.2:3b)
- Test a simple query: "Hello, what can you help me with?"
- Show agent's response listing available tools
- If time permits, show JupyterLab at :8888

---

## Slide 14: Tour of the UI
**Title:** Streamlit Interface Walkthrough

**Content:**
**Streamlit Components:**
1. **Sidebar:**
   - Session Management (New/Load/Delete)
   - Model Selection (Ollama, OpenAI, Azure)
   - Clear Chat button

2. **Main Chat Area:**
   - User messages (you)
   - Agent responses
   - Tool execution logs
   - Thinking/reasoning traces

3. **Chat Input:**
   - Type queries naturally
   - Agent interprets and uses tools

**First Query to Try:**
```
What tools do you have available?
```

**Speaker Notes:**
- Give attendees time to explore the UI
- Explain session management:
  - Each session has unique ID
  - History persisted in SQLite
  - Can save and load sessions
- Model selection dropdown:
  - Default: Ollama (local)
  - If they added API keys: Can switch to OpenAI/Azure
- Show the agent's response to "What tools do you have available?"
  - Should list: rag_query, sql_query, blast_search, uniprot_info, pubchem_search, notes_tool
- Mention that tool execution logs are visible (transparency)

---

## Slide 15: Simple Tool Examples
**Title:** Try These Queries

**Content:**
**Query 1: Notes Tool (Simplest)**
```
Add a note: "Today we learned about ADEPT"
```

**Query 2: SQL Database**
```
What tables are in the database?
```

**Query 3: RAG Query (if you've uploaded docs)**
```
Summarize the documentation you have access to
```

**Expected Behavior:**
- Agent thinks about which tool to use
- Executes the tool
- Returns results in natural language

**Speaker Notes:**
- Walk through Query 1 live:
  - Type it in the chat
  - Agent should use `notes_tool` to add the note
  - Then you can ask: "What notes do I have?" to retrieve
- Query 2 demonstrates SQL tool:
  - Should return table names from SQLite database
  - Try follow-up: "Show me some sample data from [table_name]"
- Query 3 requires documents in RAG:
  - If none uploaded yet, agent will say no documents available
  - We'll do document upload in next hands-on section
- Give attendees 5 minutes to try queries
- Walk around (if in-person) or monitor chat (if virtual) for questions

---

## Slide 16: Behind the Scenes
**Title:** What Just Happened?

**Content:**
**Query Flow:**
```
User: "Add a note: Meeting at 3pm"
  ↓
Langchain Agent (in Streamlit backend)
  → Analyzes query
  → Selects tool: notes_tool
  → Calls MCP Server: /mcp/tools/notes_tool
  ↓
MCP Server (port 8080)
  → Receives tool call
  → Executes notes_tool implementation
  → Stores in SQLite database
  → Returns: {"status": "success", "note_id": 123}
  ↓
Agent
  → Receives response
  → Synthesizes natural language
  ↓
User: "I've added your note: 'Meeting at 3pm'"
```

**Key Points:**
- 🧠 Agent decides which tool(s) to use
- 🔌 MCP protocol for tool communication
- 💾 Persistent storage (SQLite, ChromaDB)

**Speaker Notes:**
- This is the core agent loop
- Break down each step:
  1. User query comes into Streamlit
  2. Streamlit calls Langchain agent
  3. Agent (using LLM) decides which tool fits
  4. Agent makes HTTP call to MCP server
  5. MCP server executes Python tool implementation
  6. Result returned via HTTP
  7. Agent (using LLM) formats response
  8. Streamlit displays to user
- Everything is logged (check logs with `docker logs` or `podman logs`)
- This same pattern works for all tools, regardless of complexity

---

# Section 4: MCP Tools & Agent Orchestration
**Duration:** 20 minutes (0:55 - 1:15)

## Slide 17: MCP Tool Architecture
**Title:** How Tools Are Built

**Content:**
**Tool Implementation (Python):**
```python
# In: src/agentic_framework_pkg/mcp_server/tools/notes.py

from fastmcp import FastMCP, Context
from typing import Optional

def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def notes_tool(
        ctx: Context,
        action: str,
        content: Optional[str] = None,
        mcp_session_id: Optional[str] = None
    ) -> dict:
        """
        Store and retrieve notes.

        Args:
            action: 'add' or 'list'
            content: Note content (for 'add')
            mcp_session_id: Session ID for context
        """
        await ctx.info(f"Notes tool: {action}")

        if action == "add":
            # Store in database
            note_id = db.add_note(content)
            return {"status": "success", "note_id": note_id}

        elif action == "list":
            # Retrieve from database
            notes = db.get_notes()
            return {"notes": notes}
```

**Registration in MCP Server:**
```python
# In: src/agentic_framework_pkg/mcp_server/main.py

from .tools import notes

def setup_mcp_server():
    notes.register_tools(mcp)  # Register our tool
```

**Speaker Notes:**
- Tools are Python async functions with `@mcp.tool()` decorator
- `Context` provides logging, session access
- Docstring is sent to LLM (important!)
- Return value is serialized to JSON
- Tools can access databases, APIs, file systems
- Registration is centralized in main.py
- Show the actual code on GitHub if possible
- Emphasize simplicity: ~20 lines to add a tool

---

## Slide 18: Tool Wrapping for Langchain
**Title:** Connecting MCP Tools to Langchain Agent

**Content:**
**Langchain Tool Wrapper:**
```python
# In: src/agentic_framework_pkg/scientific_workflow/mcp_langchain_tools.py

from pydantic import BaseModel, Field
from .mcp_tool_wrapper import MCPToolWrapper

class NotesToolInput(BaseModel):
    """Input schema for notes tool"""
    action: str = Field(description="Action: 'add' or 'list'")
    content: Optional[str] = Field(
        default=None,
        description="Note content (required for 'add')"
    )

def get_mcp_notes_tool(mcp_server_url: str) -> MCPToolWrapper:
    return MCPToolWrapper(
        name="notes_tool",
        description="Store and retrieve notes",
        mcp_server_url=mcp_server_url,
        mcp_tool_name="notes_tool",
        args_schema=NotesToolInput
    )
```

**Adding to Agent:**
```python
# In: src/agentic_framework_pkg/scientific_workflow/langchain_agent.py

tools = [
    get_mcp_notes_tool(mcp_server_url),
    get_mcp_rag_query_tool(mcp_server_url),
    get_mcp_sql_query_tool(mcp_server_url),
    # ... other tools
]

agent = create_react_agent(llm, tools)
```

**Speaker Notes:**
- Two-step process:
  1. Implement tool in MCP server (Python)
  2. Wrap tool for Langchain (also Python)
- Pydantic schema defines inputs for LLM
- MCPToolWrapper handles HTTP communication
- Agent gets a list of BaseTool instances
- Langchain's ReAct agent decides which to call
- This separation allows:
  - MCP server to be reused by other frameworks
  - Agent to be swapped (LangGraph, AutoGPT, etc.)

---

## Slide 19: Scientific Tools Deep Dive
**Title:** BLAST & UniProt Tools

**Content:**
**BLAST (Basic Local Alignment Search Tool):**
```python
@mcp.tool()
async def blast_search(
    ctx: Context,
    sequence: str,
    program: str = "blastp",
    database: str = "nr"
) -> dict:
    """Search for similar protein sequences"""
    # Calls NCBI BLAST API
    # Returns: alignment results with E-values
```

**Use Case:**
```
User: "Find proteins similar to MKVLWAALLVTFLAGCQA"
Agent: → Uses blast_search tool
        → Returns: Hits in UniProt with similarity scores
```

**UniProt (Protein Database):**
```python
@mcp.tool()
async def uniprot_info(
    ctx: Context,
    uniprot_id: str
) -> dict:
    """Get detailed protein information"""
    # Calls UniProt REST API
    # Returns: protein name, function, structure, etc.
```

**Use Case:**
```
User: "What does protein P12345 do?"
Agent: → Uses uniprot_info tool
        → Returns: Function, organism, gene names
```

**Speaker Notes:**
- These are real scientific tools, not toys
- BLAST is core bioinformatics tool
  - Used daily by thousands of researchers
  - ADEPT provides natural language interface
- UniProt is authoritative protein database
  - Tool wraps their REST API
  - Results returned in structured format
- Agent can chain tools:
  1. BLAST to find similar proteins
  2. UniProt to get details on each hit
  3. PubChem to find related compounds
- Show example query: "Find proteins similar to [sequence] and their associated drugs"

---

## Slide 20: RAG Tool Architecture
**Title:** Document Q&A with RAG

**Content:**
**RAG = Retrieval Augmented Generation**

**How it Works:**
1. **Document Upload:**
   - User uploads PDF/text
   - Document chunked into segments
   - Embeddings generated (via OpenAI/Azure/local)
   - Stored in ChromaDB vector database

2. **Query Time:**
   - User asks question
   - Question embedded
   - ChromaDB finds relevant chunks (similarity search)
   - Chunks sent to LLM as context
   - LLM generates answer

**Implementation:**
```python
@mcp.tool()
async def rag_query(
    ctx: Context,
    query: str,
    collection_name: str = "default",
    top_k: int = 5
) -> dict:
    """Query documents using RAG"""
    # 1. Embed query
    query_embedding = embeddings_model.embed(query)

    # 2. Search ChromaDB
    results = chromadb.query(
        collection=collection_name,
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    # 3. Return chunks as context
    return {"chunks": results["documents"]}
```

**Speaker Notes:**
- RAG is critical for grounding LLM responses in your data
- Without RAG: LLM only knows training data
- With RAG: LLM can answer questions about your specific documents
- ChromaDB is vector database (stores embeddings)
- Embeddings are vector representations of text
  - Similar text → similar vectors
  - Fast similarity search via vector distance
- Show embedding model config in .env:
  - `EMBEDDING_DEFAULT_MODEL=text-embedding-3-small`
  - Can use OpenAI, Azure, or local models
- Document upload happens via Streamlit file uploader
- We'll try this in next hands-on section

---

## Slide 21: Agent Decision Making
**Title:** How the Agent Chooses Tools

**Content:**
**ReAct (Reasoning + Acting) Pattern:**

```
User Query: "Find proteins similar to MKVLWA and get details on the top hit"

Agent Reasoning:
┌────────────────────────────────────────┐
│ Thought: I need to search for similar │
│ proteins first using BLAST             │
└────────────────────────────────────────┘
          ↓
┌────────────────────────────────────────┐
│ Action: blast_search                   │
│ Input: sequence="MKVLWA"               │
└────────────────────────────────────────┘
          ↓
┌────────────────────────────────────────┐
│ Observation: Found 5 hits, top is      │
│ UniProt ID: P12345 (E-value: 1e-50)    │
└────────────────────────────────────────┘
          ↓
┌────────────────────────────────────────┐
│ Thought: Now I need details on P12345  │
└────────────────────────────────────────┘
          ↓
┌────────────────────────────────────────┐
│ Action: uniprot_info                   │
│ Input: uniprot_id="P12345"             │
└────────────────────────────────────────┘
          ↓
┌────────────────────────────────────────┐
│ Observation: P12345 is Insulin         │
│ (Homo sapiens), regulates glucose...   │
└────────────────────────────────────────┘
          ↓
┌────────────────────────────────────────┐
│ Final Answer: The top protein hit is   │
│ Insulin (P12345), which regulates...   │
└────────────────────────────────────────┘
```

**Key Components:**
- 💭 **Thought:** Agent plans next step
- 🎯 **Action:** Agent selects and calls tool
- 👀 **Observation:** Agent sees tool result
- 🔁 **Loop:** Repeat until answer found

**Speaker Notes:**
- This is the ReAct pattern (Yao et al., 2022)
- Agent doesn't execute all tools blindly
- It reasons about which tool to use and when
- LLM sees:
  - User query
  - Available tools (names + descriptions)
  - Previous thoughts/actions/observations
- LLM outputs next thought/action in structured format
- Framework parses and executes action
- This enables multi-step reasoning
- Show Streamlit logs (if verbose mode enabled)
- Mention that some queries need 1 step, others need 10+

---

## Slide 22: Multi-Agent Architecture (Chapter 3)
**Title:** Advanced: Multi-Agent Orchestration

**Content:**
**Single Agent vs Multi-Agent:**

**Single Agent (Chapters 0-2):**
```
User → Agent → Tools → Response
```

**Multi-Agent (Chapter 3):**
```
User → Planner Agent
        ↓ (creates plan)
       Supervisor Agent
        ↓ (delegates tasks)
   ┌────┼────┐
   ↓    ↓    ↓
Worker1 Worker2 Worker3
 (RAG) (BLAST) (Code)
   ↓    ↓    ↓
Supervisor (synthesizes)
   ↓
User ← Final Response
```

**Benefits:**
- 📋 **Planning:** Break complex tasks into subtasks
- ⚡ **Parallel:** Execute independent tasks simultaneously
- 🎯 **Specialization:** Each agent has focused tools
- 🔄 **Coordination:** Supervisor manages workflow

**Example Query:**
```
"Analyze this protein sequence, find similar sequences,
and write Python code to visualize the results"
```
→ Planner creates 3-step plan
→ Worker1: Analyzes sequence
→ Worker2: Runs BLAST
→ Worker3: Generates Python visualization code
→ Supervisor: Combines results

**Speaker Notes:**
- Multi-agent is optional, but powerful for complex tasks
- Chapter 3 introduces this architecture
- Two modes:
  1. **Router mode:** Static plan, supervisor delegates
  2. **Graph mode:** Dynamic LangGraph state machine
- Each worker agent has subset of tools
- Prevents "tool overload" (too many tools confuse agent)
- Parallel execution speeds up multi-step workflows
- We won't demo this today (out of time), but it's in the tutorial
- Reference: `docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent`

---

# Section 5: Hands-on - Running Scientific Workflows
**Duration:** 20 minutes (1:15 - 1:35)

## Slide 23: Scientific Workflow Lab
**Title:** Hands-on Lab 2: RAG + Protein Analysis

**Content:**
**Scenario:**
You're researching a protein and need to:
1. Upload a research paper (PDF)
2. Ask questions about the paper using RAG
3. Extract protein sequence from paper
4. Find similar proteins using BLAST
5. Get drug information for the protein

**Files Provided:**
- Sample PDF: `docs/sample-data/sample-protein-paper.pdf` (create if needed)
- Or use any scientific PDF you have

**Time:** 15 minutes hands-on

**Speaker Notes:**
- This mirrors a real research workflow
- We'll do this step-by-step together
- First, I'll demo the full workflow
- Then attendees try on their own with different queries
- If no sample PDF, use any PDF (even the ADEPT tutorial PDF works!)

---

## Slide 24: Step 1 - Upload Document
**Title:** Upload Document for RAG

**Content:**
**In Streamlit UI:**

1. Look for "Upload Document" section (sidebar or main area)
   - If not visible: Ask "Can I upload a document?"
   - Agent will provide upload instructions

2. Upload your PDF:
   - File uploader widget appears
   - Select PDF file
   - Wait for processing message

3. Verify upload:
   ```
   Ask: "What documents do you have?"
   ```
   Expected: Agent lists uploaded document

**What's Happening:**
- PDF is parsed into text
- Text chunked (default: 1000 char chunks)
- Each chunk embedded (vector)
- Vectors stored in ChromaDB
- Collection named after document

**Speaker Notes:**
- Show this live in your Streamlit instance
- Upload process takes 10-30 seconds depending on document size
- If using OpenAI embeddings: Requires API key in .env
- If using local Ollama embeddings: Slower but works offline
- Check MCP server logs for upload progress:
  ```bash
  docker logs -f agentic_mcp_server_ch00
  ```
- Common issues:
  - "No embedding model configured" → Check .env file
  - Timeout → Document too large (try smaller PDF)

---

## Slide 25: Step 2 - Query the Document
**Title:** Ask Questions Using RAG

**Content:**
**Try These Queries:**

**Query 1: Summarization**
```
Summarize the main findings of the uploaded document
```

**Query 2: Specific Information**
```
What protein sequences are mentioned in this document?
```

**Query 3: Extraction**
```
Extract any protein accession numbers or UniProt IDs
from this document
```

**Expected Behavior:**
- Agent uses `rag_query` tool
- Retrieves relevant chunks from ChromaDB
- LLM generates answer based on chunks
- Cites specific sections (if verbose mode enabled)

**Speaker Notes:**
- Walk through Query 1 live
- Show how agent responds with information from YOUR document
- Not generic knowledge - specific to uploaded content
- Try asking something NOT in the document:
  ```
  What is the capital of France?
  ```
  Agent should say "Not in uploaded documents" (if grounded properly)
- Give attendees 5 minutes to try their own queries
- Encourage creative questions about their documents

---

## Slide 26: Step 3 - Multi-Tool Workflow
**Title:** Chain Tools Together

**Content:**
**Complex Query (Multiple Tools):**

```
Based on the uploaded document, find the protein sequence
mentioned, search for similar proteins using BLAST,
and tell me about the top hit
```

**Expected Workflow:**
1. Agent uses `rag_query` → Finds protein sequence in doc
2. Agent uses `blast_search` → Searches NCBI database
3. Agent uses `uniprot_info` → Gets details on top hit
4. Agent synthesizes final answer

**Alternative Workflow:**
```
Find information about insulin in my document, then
search PubChem for drugs that target insulin receptors
```

**Workflow:**
1. Agent uses `rag_query` → Finds insulin info
2. Agent uses `pubchem_search` → Searches compounds
3. Agent returns compound list with activities

**Speaker Notes:**
- This is where agentic systems shine
- Single query → Multiple tool calls → Coherent answer
- Agent handles:
  - Which tools to call
  - In what order
  - How to combine results
- Show the full workflow in Streamlit logs
- Point out the thinking traces (Thought/Action/Observation)
- This would take manual effort:
  1. Read PDF manually
  2. Copy sequence
  3. Go to NCBI website
  4. Paste into BLAST
  5. Wait for results
  6. Copy top hit ID
  7. Go to UniProt
  8. Search for ID
  9. Read result
- Agent does all this in 30-60 seconds

---

## Slide 27: Step 4 - Experiment!
**Title:** Try Your Own Workflows

**Content:**
**Challenge Queries:**

**Easy:**
```
- List all the tools you have access to
- Add a note with today's date and what you learned
- Query the database for existing notes
```

**Medium:**
```
- Search for proteins related to [disease name]
- Find chemical compounds that target [protein name]
- Summarize the methods section of the uploaded paper
```

**Hard:**
```
- Analyze this protein sequence [paste sequence], find
  similar sequences, get details on top 3 hits, and
  suggest potential drug targets
```

**10 Minutes:** Free exploration

**Speaker Notes:**
- Let attendees experiment
- Walk around (in-person) or monitor chat (virtual)
- Help with debugging:
  - Tool not found → Check MCP server is running
  - Timeout → Query too complex, try breaking it down
  - Empty response → Check tool logs for errors
- Encourage sharing interesting results
- Ask: "Who found something surprising?"
- Show off any particularly good agent reasoning examples

---

## Slide 28: Troubleshooting Common Issues
**Title:** When Things Go Wrong

**Content:**
**Issue 1: Agent doesn't use the right tool**
- **Cause:** Ambiguous query
- **Fix:** Be more specific
  - ❌ "Tell me about protein"
  - ✅ "Use UniProt to get information about protein P12345"

**Issue 2: Tool returns empty results**
- **Cause:** No data matches query
- **Fix:** Check tool input
  - View tool call logs
  - Try simpler query
  - Verify data exists (e.g., document uploaded for RAG)

**Issue 3: Agent gets stuck in loop**
- **Cause:** Tool returns unexpected format
- **Fix:** Restart agent or session
  - Clear chat
  - New session

**Issue 4: Timeout errors**
- **Cause:** LLM taking too long, external API slow
- **Fix:** Wait and retry, or use faster model

**Debugging Commands:**
```bash
# View MCP server logs
docker logs agentic_mcp_server_ch00

# View Streamlit logs
docker logs agentic_streamlit_app_ch00

# Check container health
docker ps
```

**Speaker Notes:**
- These are the most common issues beginners face
- Agent behavior is probabilistic - sometimes it makes odd choices
- Better prompt engineering helps:
  - Be specific about which tool to use
  - Provide context
  - Break complex queries into steps
- If all else fails:
  - Check logs (most errors logged)
  - Restart containers
  - Check GitHub issues: github.com/pnnl/adept-agentic-framework-core/issues

---

# Section 6: Advanced Features & Deployment
**Duration:** 15 minutes (1:35 - 1:50)

## Slide 29: Chapter 2 - HPC Integration
**Title:** HPC MCP Server (Chapter 2)

**Content:**
**HPC-Specific Tools:**

1. **Nextflow Workflows:**
   - Submit bioinformatics pipelines
   - Monitor job status
   - Retrieve results

2. **GitXRay Code Analysis:**
   - Analyze GitHub repositories
   - Extract code structure
   - Generate documentation

3. **Whisper Audio Transcription:**
   - Transcribe audio files
   - Useful for lab notes, meetings

**Architecture:**
```
Streamlit → Langchain Agent
                ↓
         ┌──────┴──────┐
         ↓             ↓
    Main MCP      HPC MCP
   (Port 8080)  (Port 8081)
    • RAG           • Nextflow
    • BLAST         • GitXRay
    • UniProt       • Whisper
```

**Deployment:**
```bash
cd docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot
./start-chapter-resources.sh  # or -podman.sh
```

**Speaker Notes:**
- Chapter 2 adds second MCP server (HPC-focused tools)
- Agent can access tools from both servers
- Nextflow is popular workflow engine in HPC
  - Define pipelines in DSL
  - Agent can submit and monitor
- GitXRay analyzes git repos
  - "Summarize the codebase at github.com/..."
- Whisper for audio transcription
  - "Transcribe this meeting recording and summarize key points"
- Chain-of-Thought (CoT) prompting improved in Chapter 2
- We won't deploy this today (time), but it's straightforward

---

## Slide 30: Chapter 3 - Sandbox Execution
**Title:** Safe Code Execution (Chapter 3)

**Content:**
**Sandbox MCP Server:**

- Executes Python code in isolated nsjail sandbox
- Limited resources (CPU, memory, time)
- No network access, no file system access (except temp)
- Perfect for:
  - Data analysis scripts
  - Visualization generation
  - Math/science calculations

**Example Workflow:**
```
User: "Calculate the molecular weight of C6H12O6
       and write Python code to verify"

Agent:
1. Uses pubchem_search to find glucose (C6H12O6)
2. Uses sandbox_execute to run:
   ```python
   C = 12.01
   H = 1.008
   O = 16.00
   mw = 6*C + 12*H + 6*O
   print(f"Molecular weight: {mw} g/mol")
   ```
3. Returns: "Molecular weight: 180.156 g/mol"
```

**Security:**
- nsjail provides kernel-level isolation
- Requires privileged container (Docker/Podman)
- Podman rootful mode required for Chapter 3

**Speaker Notes:**
- Sandbox execution is powerful but dangerous
- nsjail is Linux kernel sandboxing tool
  - Used by Google for security
  - Isolates processes from host system
- Code runs in minimal environment:
  - Python 3.11 + numpy/pandas
  - No pip install (security)
  - No network calls
- Use cases:
  - Agent generates code to solve problem
  - Runs code safely
  - Returns results
- Important: Review code before execution in production!
- Chapter 3 also adds multi-agent architecture
- Deployment: `cd chapter-03-*; sudo -E ./start-chapter-resources-podman.sh`

---

## Slide 31: Production Deployment Options
**Title:** Deploying ADEPT in Production

**Content:**
**Deployment Paths:**

**1. Single Server (Chapters 0-3):**
- Docker Compose / Podman Compose
- All services on one machine
- Good for: Dev, small teams, demos

**2. Kubernetes (Chapter 4):**
- Helm charts provided
- Scalable, highly available
- Good for: Enterprise, multi-tenant

**3. OpenWebUI Integration (Chapter 5):**
- Plug into existing OpenWebUI
- Leverage OpenWebUI's user management
- Good for: Teams already using OpenWebUI

**4. Agent Gateway (Chapter 6):**
- OpenAI-compatible API endpoint
- Dynamic tool registration (stdio protocol)
- Any CLI tool → Agent tool
- Good for: Flexible, extensible deployments

**Resource Requirements:**
| Component | CPU | RAM | Storage |
|-----------|-----|-----|---------|
| Ollama (local) | 4 cores | 8 GB | 10 GB |
| MCP Servers | 2 cores | 4 GB | 2 GB |
| Streamlit | 1 core | 2 GB | 1 GB |
| ChromaDB | 1 core | 4 GB | 10+ GB |

**Speaker Notes:**
- Production deployment depends on scale
- Small team (< 10 users): Docker Compose on single VM
- Medium (10-100 users): Kubernetes with 3-5 nodes
- Large (100+ users): K8s with autoscaling, load balancing
- Chapter 4 Helm charts include:
  - Deployments for all services
  - Services, Ingress
  - PersistentVolumeClaims for data
  - ConfigMaps, Secrets management
- OpenWebUI integration (Ch 5):
  - ADEPT becomes "backend" for OpenWebUI
  - Users interact via OpenWebUI's polished interface
- Agent Gateway (Ch 6) is most advanced:
  - Single API endpoint
  - Tools registered dynamically
  - Any container/CLI → Agent tool
- Show Helm README: `infra/helm/README.md`

---

## Slide 32: LLM Provider Options
**Title:** LLM Agnostic Layer

**Content:**
**Supported LLM Providers:**

| Provider | Configuration | Best For |
|----------|--------------|----------|
| **Ollama** | Local, no API key | Offline, privacy-sensitive |
| **OpenAI** | `OPENAI_API_KEY` | Fast, high-quality |
| **Azure OpenAI** | `AZURE_API_KEY`, `AZURE_API_BASE` | Enterprise, compliance |
| **NVIDIA NIM** | `NVIDIA_API_KEY` | HPC with GPUs |
| **LiteLLM** | Proxy for 100+ providers | Flexibility |

**Switching Providers:**
```bash
# Edit .env file
LANGCHAIN_LLM_MODEL=gpt-4o-mini           # OpenAI
# OR
LANGCHAIN_LLM_MODEL=azure/my-deployment   # Azure
# OR
LANGCHAIN_LLM_MODEL=ollama/llama3.2:3b    # Ollama
# OR
LANGCHAIN_LLM_MODEL=nvidia_nim/meta/llama-3.1-70b-instruct # NVIDIA
```

**Restart services:**
```bash
docker compose restart
```

**Implementation:**
- Unified `LLMAgnosticClient` class
- Uses LiteLLM library under the hood
- All prompts, tool calls standardized
- Just change environment variable!

**Speaker Notes:**
- This is a killer feature
- Same code works with any LLM
- No vendor lock-in
- Test with Ollama (cheap/free), deploy with OpenAI (quality)
- LiteLLM handles:
  - API format differences
  - Authentication
  - Rate limiting, retries
  - Cost tracking
- Show .env file with all LLM configs
- Mention model selection dropdown in Streamlit
  - Users can switch models per-session
- Some tools require embeddings:
  - `EMBEDDING_DEFAULT_MODEL=text-embedding-3-small`
  - Can also be Ollama, Azure, etc.

---

## Slide 33: Monitoring & Observability
**Title:** Logging and Debugging

**Content:**
**Built-in Logging:**

**1. Application Logs:**
```bash
# View real-time logs
docker logs -f agentic_mcp_server_ch00
docker logs -f agentic_streamlit_app_ch00

# Search logs
docker logs agentic_mcp_server_ch00 | grep ERROR
```

**2. Agent Reasoning Traces:**
- Visible in Streamlit UI
- Thought → Action → Observation loops
- Enable verbose mode in config

**3. Tool Execution Logs:**
- Each tool call logged with:
  - Timestamp
  - Input parameters
  - Execution time
  - Output/errors

**4. LiteLLM Logging:**
```python
# In .env
LITELLM_VERBOSE=True  # Log all LLM API calls
```

**Helper Scripts (Chapter 0):**
```bash
# Cross-reference all logs
./check-service-logs.sh summary

# Verify services health
./verify-services.sh

# Clean up stale processes
sudo ./scripts/cleanup-stale-processes.sh
```

**Speaker Notes:**
- Observability is critical for debugging agents
- Agent behavior is non-deterministic
- Logs help understand:
  - Why agent chose tool X over tool Y
  - What parameters were passed
  - What errors occurred
- Streamlit UI shows reasoning (if enabled)
- Production deployments should use:
  - Centralized logging (ELK, Grafana Loki)
  - Metrics (Prometheus)
  - Tracing (OpenTelemetry)
- Show live log tailing:
  ```bash
  docker logs -f agentic_mcp_server_ch00
  ```
- Point out log format: timestamp, level, message

---

## Slide 34: Testing Framework
**Title:** Automated Testing (Podman)

**Content:**
**Test Suite (Podman Deployments):**

**1. Comprehensive Tests:**
```bash
# Test specific chapter
sudo -E ./tests/podman/test-podman-deployment.sh 0

# Test all chapters
sudo -E ./tests/podman/test-podman-deployment.sh all
```

**Test Categories:**
- ✅ Prerequisites (Podman, podman-compose, Python)
- ✅ Environment (.env files, registry config)
- ✅ Chapter configuration (compose files, overlays)
- ✅ Runtime (container status, logs, no errors)
- ✅ Networking (endpoint accessibility)

**2. Quick Smoke Tests:**
```bash
# Fast validation (< 10 seconds)
./tests/podman/quick-test.sh 0
./tests/podman/quick-test.sh 1
```

**CI/CD Integration:**
```yaml
# Example GitLab CI
test-chapter-0:
  script:
    - sudo -E ./tests/podman/test-podman-deployment.sh 0
  only:
    - merge_requests
```

**Documentation:**
- See `docs/PODMAN_TESTING.md` for full guide

**Speaker Notes:**
- Test suite ensures deployment correctness
- Catches configuration errors before runtime
- Especially useful for Podman (more complex than Docker)
- Tests are idempotent (can run multiple times)
- Quick test for fast feedback loop
- Comprehensive test for CI/CD pipelines
- Tests don't require services to be running (mostly)
- Runtime tests DO require containers up
- Show test output example:
  ```
  ✓ PASS: Podman installed
  ✓ PASS: podman-compose found
  ✓ PASS: .env file exists
  ✓ PASS: docker-compose.yaml valid
  ...
  Summary: 17/17 tests passed
  ```
- Encourage adding tests when contributing

---

## Slide 35: Contributing & Community
**Title:** Get Involved

**Content:**
**How to Contribute:**

**1. Report Issues:**
- GitHub Issues: github.com/pnnl/adept-agentic-framework-core/issues
- Include: Steps to reproduce, logs, environment details

**2. Add New Tools:**
- Fork repository
- Create tool in `src/agentic_framework_pkg/mcp_server/tools/`
- Register tool in `main.py`
- Submit pull request

**3. Improve Documentation:**
- Tutorial improvements
- Fix typos
- Add examples
- Translate to other languages

**4. Share Use Cases:**
- Blog posts
- Conference talks
- Papers (please cite!)

**Citation:**
```bibtex
@software{adept2025,
  author = {George, A. and Bilbao, A. and Agarwal, K. et al.},
  title = {ADEPT: A Pedagogical Framework for Integrating
           Agentic AI with Deterministic Scientific Workflows},
  year = {2025},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.17315801}
}
```

**Community:**
- GitHub Discussions (coming soon)
- Discord/Slack (TBD)
- Monthly community calls (TBD)

**Speaker Notes:**
- ADEPT is open source (license in repo)
- Developed at PNNL, but community-driven
- We welcome contributions:
  - New scientific tools
  - UI improvements
  - Deployment guides for other platforms
  - Bug fixes
- Citation is appreciated if you use in research
- Future plans:
  - Community calls for users/developers
  - Discord/Slack for real-time help
  - Contribution guidelines being finalized
- Show GitHub repo structure
- Star the repo! (helps visibility)

---

# Section 7: Q&A and Next Steps
**Duration:** 10 minutes (1:50 - 2:00)

## Slide 36: Key Takeaways
**Title:** What We Learned Today

**Content:**
**Core Concepts:**
1. ✅ **Agentic Systems:** LLM + Tools + Orchestration
2. ✅ **MCP Protocol:** Standard for connecting LLMs to tools
3. ✅ **ADEPT Architecture:** Modular, extensible, pedagogical
4. ✅ **Deployment:** Docker/Podman, single server to K8s
5. ✅ **Scientific Tools:** RAG, BLAST, UniProt, PubChem, etc.

**Hands-on Experience:**
- ✅ Deployed Chapter 0 (local agentic system)
- ✅ Ran scientific workflows (RAG + protein analysis)
- ✅ Observed agent reasoning (Thought/Action/Observation)
- ✅ Chained multiple tools together

**Next Steps:**
- 📚 Complete remaining tutorial chapters (1-6)
- 🛠️ Add your own scientific tools
- 🚀 Deploy in your HPC environment
- 🌟 Star the GitHub repo and contribute!

**Speaker Notes:**
- Recap the main points
- Emphasize what attendees can do NOW:
  - They have working system on their laptop
  - Can experiment with their own data
  - Can read tutorial chapters sequentially
- Remind them of resources:
  - Tutorial: `docs/agentic-framework-tutorial.md`
  - Tool guide: `docs/agentic-framework-tool-user-guide.md`
  - Deployment guides: `docs/PODMAN_QUICKSTART.md`, etc.
- Encourage sharing their experiences:
  - What worked?
  - What was confusing?
  - What features do they need?

---

## Slide 37: Next Steps - Continuing the Journey
**Title:** Your Learning Path

**Content:**
**Immediate (This Week):**
1. Complete Chapter 0 exploration
   - Try all tools
   - Upload your own documents
   - Run protein analysis workflows

2. Read documentation:
   - Tool User Guide (understand each tool)
   - Tutorial Outline (plan your learning path)

**Short-term (This Month):**
3. Deploy Chapter 1 (Langchain agent)
   - Understand agent architecture
   - Customize prompts

4. Deploy Chapter 2 (HPC tools)
   - Try Nextflow workflows
   - Explore GitXRay

5. Deploy Chapter 3 (Multi-agent)
   - Run complex workflows
   - Experiment with sandbox execution

**Long-term (This Quarter):**
6. Add your own tool
   - Follow Part 2 of tutorial
   - Integrate domain-specific API

7. Production deployment
   - Chapter 4 (Kubernetes)
   - Chapter 6 (Agent Gateway)

8. Contribute back to community!

**Speaker Notes:**
- Give attendees a roadmap
- Set realistic expectations:
  - Each chapter takes 2-4 hours to fully understand
  - Adding custom tools: 1-2 days (first time)
  - Production deployment: 1-2 weeks (depending on infrastructure)
- Mention that they can skip chapters if they want
  - Each chapter is self-contained
  - Can go directly to Ch 4 (K8s) if that's their need
- Encourage forming study groups
  - Work through chapters together
  - Share knowledge
- Offer ongoing support (if applicable):
  - Office hours?
  - Follow-up workshops?
  - 1-on-1 consultations?

---

## Slide 38: Resources & Links
**Title:** Helpful Resources

**Content:**
**ADEPT Documentation:**
- 📦 GitHub: https://github.com/pnnl/adept-agentic-framework-core
- 📚 Tutorial: `docs/agentic-framework-tutorial.md`
- 🛠️ Tool Guide: `docs/agentic-framework-tool-user-guide.md`
- 🐳 Podman Guide: `docs/PODMAN_QUICKSTART.md`
- 🧪 Testing Guide: `docs/PODMAN_TESTING.md`

**Related Technologies:**
- 🔌 MCP Protocol: https://modelcontextprotocol.io/
- 🦜 Langchain: https://langchain.com/
- 🔗 LangGraph: https://langchain-ai.github.io/langgraph/
- 🦙 Ollama: https://ollama.com/
- 🐋 Docker: https://docker.com/
- 🦭 Podman: https://podman.io/

**Scientific APIs:**
- 🧬 NCBI BLAST: https://blast.ncbi.nlm.nih.gov/
- 🔬 UniProt: https://uniprot.org/
- ⚗️ PubChem: https://pubchem.ncbi.nlm.nih.gov/

**Citation:**
- 📄 DOI: 10.5281/zenodo.17315801

**Speaker Notes:**
- These links are in the README and documentation
- Attendees should bookmark the GitHub repo
- MCP documentation is essential reading
- Langchain/LangGraph docs helpful for customization
- Scientific API docs useful when adding new tools
- Mention that all URLs are in slide deck (if sharing slides)
- Share contact information for follow-up questions

---

## Slide 39: Q&A
**Title:** Questions?

**Content:**
**Common Questions:**

**Q: Can I use this without API keys?**
A: Yes! Chapter 0 includes Ollama (local LLM). Fully offline capable.

**Q: How do I add my own tool?**
A: Tutorial Part 2 covers this. ~50 lines of Python. PR welcome!

**Q: Does this work on Windows?**
A: Yes, via WSL 2 + Docker Desktop. See tutorial for setup.

**Q: Can I deploy on HPC cluster?**
A: Yes! Podman support (Chapters 0-3) or Kubernetes (Chapter 4).

**Q: Is this production-ready?**
A: Architecture is solid. Pedagogical framework → Adapt for production. Security review recommended.

**Q: How do I get help?**
A: GitHub Issues, documentation, community (forming).

**Open Floor:**
- What questions do you have?
- What would you like to see demonstrated?
- What's your use case?

**Speaker Notes:**
- Reserve full 10 minutes for Q&A
- Encourage questions throughout (if not already doing so)
- Common questions to anticipate:
  - Cost (LLM API usage)
  - Performance (latency, throughput)
  - Security (code execution, data privacy)
  - Customization (swapping components)
  - Troubleshooting (common errors)
- Have answers ready for these
- If you don't know answer: "Great question, I'll find out and follow up"
- Collect questions for documentation improvements
- Offer to stay after for 1-on-1 questions

---

## Slide 40: Thank You!
**Title:** Thank You for Attending

**Content:**
**Workshop Complete! 🎉**

**You've learned:**
- ✅ Agentic system architecture
- ✅ MCP protocol and tools
- ✅ Deploying ADEPT locally
- ✅ Running scientific workflows
- ✅ Next steps for customization

**Stay Connected:**
- ⭐ Star the repo: github.com/pnnl/adept-agentic-framework-core
- 🐛 Report issues: GitHub Issues
- 💬 Join discussions: (coming soon)
- 📧 Contact: [your email or team contact]

**Survey (Optional):**
- [Link to post-workshop survey]
- Help us improve future workshops!

**Thank you!**

**Speaker Notes:**
- Thank attendees for their time and participation
- Encourage them to:
  - Continue exploring on their own
  - Reach out with questions
  - Share their experiences
  - Contribute to the project
- If you have a survey, share the link
  - Feedback helps improve workshops
- Offer to stay for additional questions
- Share slides (if not already shared)
- Remind them containers are still running on their machines
  - Can continue experimenting
  - `Ctrl+C` to stop when done
  - `docker compose down` to clean up
- Thank any co-instructors or TAs
- Provide contact information for follow-up

---

# Appendix: Backup Slides

## Backup Slide 1: Troubleshooting - Docker
**Title:** Docker-Specific Issues

**Content:**
**Issue: Cannot connect to Docker daemon**
```
Error: Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```
**Fix:**
- Ensure Docker Desktop is running
- macOS/Windows: Check system tray for Docker icon
- Linux: `sudo systemctl start docker`

**Issue: Out of disk space**
```
Error: No space left on device
```
**Fix:**
```bash
# Clean up old images and containers
docker system prune -a

# Increase disk space in Docker Desktop settings
# Preferences → Resources → Disk image size
```

**Issue: Port already in use**
```
Error: Bind for 0.0.0.0:8501 failed: port is already allocated
```
**Fix:**
- Find process using port: `lsof -i :8501` (macOS/Linux)
- Kill process or change port in docker-compose.yaml

---

## Backup Slide 2: Troubleshooting - Podman
**Title:** Podman-Specific Issues

**Content:**
**Issue: insufficient UIDs available**
```
Error: potentially insufficient UIDs or GIDs available
```
**Fix:**
```bash
sudo usermod --add-subuids 100000-165535 $USER
sudo usermod --add-subgids 100000-165535 $USER
podman system migrate
```

**Issue: lsetxattr operation not supported**
```
Error: lsetxattr /path: operation not supported
```
**Fix:** NFS home directory issue
```bash
# Bootstrap script already handles this
# Verify storage config:
cat ~/.config/containers/storage.conf
# Should show: graphroot = "/tmp/podman-storage-$USER"
```

**Issue: Permission denied (rootless)**
```
Error: Operation not permitted
```
**Fix:** Use rootful mode
```bash
sudo -E ./start-chapter-resources-podman.sh
```

---

## Backup Slide 3: Advanced Configuration
**Title:** Customizing Your Deployment

**Content:**
**Custom Models:**
```bash
# .env file
LANGCHAIN_LLM_MODEL=gpt-4o           # Upgrade to GPT-4o
EMBEDDING_DEFAULT_MODEL=text-embedding-3-large  # Better embeddings
RAG_DEFAULT_MODEL=claude-opus-4-6    # Use Claude for RAG
```

**Custom Ports:**
```yaml
# docker-compose.yaml
services:
  streamlit_app:
    ports:
      - "8502:8501"  # Change host port
```

**Custom ChromaDB Location:**
```bash
# .env file
CHROMA_DB_PATH=/mnt/shared/chroma_db  # Network storage
```

**Custom Tool Configuration:**
```bash
# .env file
BLAST_MAX_HITS=20         # Return more BLAST results
RAG_CHUNK_SIZE=500        # Smaller chunks for RAG
RAG_CHUNK_OVERLAP=50      # Overlap between chunks
```

---

## Backup Slide 4: Performance Tuning
**Title:** Optimizing Performance

**Content:**
**LLM Selection:**
- **Fast:** gpt-4o-mini, claude-haiku (< 1 sec)
- **Balanced:** gpt-4o, claude-sonnet (2-3 sec)
- **Quality:** opus-4-6, gpt-4o (3-5 sec)
- **Local:** ollama/llama3.2:3b (5-10 sec, no cost)

**Embedding Models:**
- **Fast:** text-embedding-3-small (OpenAI)
- **Quality:** text-embedding-3-large (OpenAI)
- **Local:** ollama/nomic-embed-text (slower, free)

**Caching:**
```python
# Enable LLM caching in Langchain
from langchain.cache import InMemoryCache
llm.cache = InMemoryCache()
```

**Parallel Tool Execution:**
- Multi-agent mode (Chapter 3)
- Independent tools run simultaneously
- 2-3x speedup for complex queries

**Resource Allocation:**
```yaml
# docker-compose.yaml
services:
  mcp_server:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## Backup Slide 5: Security Considerations
**Title:** Production Security

**Content:**
**⚠️ Important Security Notes:**

**1. Sandbox Execution (Chapter 3):**
- Runs in privileged container
- Review all code before execution
- Consider disabling in untrusted environments

**2. API Keys:**
- Never commit .env file to git
- Use secrets management (Kubernetes Secrets, Vault)
- Rotate keys regularly

**3. Network Isolation:**
```yaml
# docker-compose.yaml
networks:
  adept-internal:
    driver: bridge
    internal: true  # No external access
```

**4. User Authentication:**
- Streamlit has no built-in auth
- Use reverse proxy (nginx + basic auth)
- Or integrate OpenWebUI (Chapter 5)

**5. Input Validation:**
- Validate all user inputs
- Sanitize file uploads
- Limit file sizes

**6. Rate Limiting:**
- Implement at reverse proxy level
- Or in Agent Gateway (Chapter 6)

---

## Backup Slide 6: Cost Management
**Title:** Managing LLM API Costs

**Content:**
**Cost Estimation (Monthly):**

**Light Usage (10 queries/day):**
- Model: gpt-4o-mini
- Tokens: ~500K/month
- **Cost: ~$5/month**

**Medium Usage (100 queries/day):**
- Model: gpt-4o
- Tokens: ~5M/month
- **Cost: ~$100/month**

**Heavy Usage (1000 queries/day):**
- Model: gpt-4o
- Tokens: ~50M/month
- **Cost: ~$1000/month**

**Cost Reduction Strategies:**
1. Use Ollama for development (free)
2. Cache LLM responses
3. Use cheaper models (gpt-4o-mini vs gpt-4o)
4. Implement usage limits per user
5. Batch requests where possible
6. Use local embeddings (Ollama)

**Monitoring Costs:**
```bash
# LiteLLM tracks costs
LITELLM_VERBOSE=True  # In .env

# Check logs for cost tracking:
docker logs agentic_mcp_server | grep "cost"
```

---

# Workshop Facilitator Notes

## Preparation Checklist (1 Day Before)

**Technical Setup:**
- [ ] Test all commands on clean machine (VM or fresh install)
- [ ] Verify Docker/Podman installations work
- [ ] Download/cache Docker images (saves time: `docker compose pull`)
- [ ] Test sample workflows end-to-end
- [ ] Prepare backup laptop (demo machine) in case attendee setup fails
- [ ] Have mobile hotspot ready (if internet unreliable)

**Materials:**
- [ ] Slides exported to PDF (backup if live demo fails)
- [ ] Sample PDFs for RAG demo prepared
- [ ] Workshop survey link ready
- [ ] Printed one-page quick reference (optional)
- [ ] Name tags (if in-person)

**Communication:**
- [ ] Send pre-workshop email with setup instructions
- [ ] Share GitHub repo link in advance
- [ ] Create Slack/Discord channel for workshop (optional)
- [ ] Prepare Zoom/virtual setup (if remote)

## During Workshop - Facilitator Checklist

**Section 1 (Setup):**
- [ ] Start recording (if applicable)
- [ ] Share screen with terminal visible
- [ ] Have attendees start `git clone` and `docker compose build` ASAP
- [ ] While building, proceed with architecture slides

**Section 3 (Hands-on 1):**
- [ ] Start Chapter 0 on your demo machine
- [ ] Keep terminal window visible for troubleshooting
- [ ] Have Docker/Podman logs open in separate window
- [ ] Walk around (in-person) to help with issues
- [ ] Collect common errors for quick troubleshooting slide

**Section 5 (Hands-on 2):**
- [ ] Upload sample PDF beforehand (saves time)
- [ ] Demonstrate full workflow first
- [ ] Then let attendees experiment
- [ ] Encourage sharing interesting results

**Throughout:**
- [ ] Monitor time closely (use timer)
- [ ] Adjust pace based on audience engagement
- [ ] Skip backup slides if running behind
- [ ] Save time for Q&A (critical!)

## Post-Workshop Follow-up

**Immediate (Same Day):**
- [ ] Share slides and recording
- [ ] Send survey link
- [ ] Answer any unanswered questions

**Short-term (Within Week):**
- [ ] Compile feedback
- [ ] Update documentation based on common issues
- [ ] Write blog post or summary
- [ ] Thank attendees (email)

**Long-term:**
- [ ] Schedule follow-up workshop (advanced topics)
- [ ] Create GitHub Discussions for continued support
- [ ] Consider office hours or drop-in sessions

## Contingency Plans

**If Docker Build Fails:**
- Use Podman instead
- Or use pre-built images from Docker Hub (if available)
- Or proceed with slides only, show pre-recorded demo

**If Internet Fails:**
- Offline mode: Use Ollama (already included)
- RAG demo with pre-loaded documents
- No external API calls needed

**If Attendees Can't Get Setup Working:**
- Show from your demo machine
- Pair up attendees (help each other)
- Offer post-workshop 1-on-1 setup help

**If Running Out of Time:**
- Skip backup slides
- Abbreviate Sections 4 or 6 (less hands-on)
- Extend Q&A invite to email/office hours

## Tips for Success

**Engagement:**
- Ask questions throughout (don't just lecture)
- Encourage attendees to share their use cases
- Use polls (if virtual): "Who has used tool X?"
- Celebrate successes: "Great! Who else got it working?"

**Technical:**
- Use large font in terminal (24pt+)
- Dark theme for terminals (easier to see)
- Zoom in on code when showing
- Use syntax highlighting in slides

**Pacing:**
- Go slower than you think necessary
- Pause after each command for attendees to catch up
- Repeat important information
- Summarize at end of each section

**Accessibility:**
- Provide captions (if virtual)
- Offer materials in advance for review
- Accommodate different learning speeds
- Record for later viewing

---

**End of Workshop Deck**
