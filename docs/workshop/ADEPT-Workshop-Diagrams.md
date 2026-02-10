# ADEPT Workshop - Mermaid Diagrams

This file contains Mermaid diagrams for the ADEPT 2-Hour Workshop presentation. Each diagram can be rendered to PNG/SVG for inclusion in slides.

## Rendering Instructions

**Online:**
- https://mermaid.live/ - Paste code and export

**Command Line:**
```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Render diagram
mmdc -i diagram.mmd -o diagram.png -b transparent
```

**VS Code:**
- Install "Markdown Preview Mermaid Support" extension
- Preview this file to see rendered diagrams

---

## Diagram 1: ADEPT Architecture Overview (Slide 7)

```mermaid
graph TB
    subgraph "User Interface Layer"
        UI1[Streamlit]
        UI2[OpenWebUI]
        UI3[JupyterLab]
        UI4[n8n]
    end

    subgraph "Agent Orchestration Layer"
        Agent[Langchain/LangGraph Agent]
        Agent_Tasks["• Query Understanding<br/>• Tool Selection<br/>• Result Synthesis"]
    end

    subgraph "MCP Tool Servers"
        MCP1[Main MCP Server]
        MCP1_Tools["• RAG<br/>• SQL<br/>• BLAST<br/>• UniProt<br/>• PubChem"]

        MCP2[HPC MCP Server]
        MCP2_Tools["• Nextflow<br/>• GitXRay<br/>• Whisper"]

        MCP3[Sandbox MCP Server]
        MCP3_Tools["• Code Execution<br/>• Isolated Sandbox"]
    end

    subgraph "Data & State Layer"
        Data1[ChromaDB]
        Data2[SQLite]
        Data3[Redis]
        Data4[File Storage]
    end

    UI1 --> Agent
    UI2 --> Agent
    UI3 --> Agent
    UI4 --> Agent

    Agent --> Agent_Tasks
    Agent_Tasks --> MCP1
    Agent_Tasks --> MCP2
    Agent_Tasks --> MCP3

    MCP1 --> MCP1_Tools
    MCP2 --> MCP2_Tools
    MCP3 --> MCP3_Tools

    MCP1_Tools --> Data1
    MCP1_Tools --> Data2
    MCP1_Tools --> Data3
    MCP1_Tools --> Data4

    MCP2_Tools --> Data4
    MCP3_Tools --> Data4

    style Agent fill:#4A90E2,color:#fff
    style MCP1 fill:#7ED321,color:#fff
    style MCP2 fill:#F5A623,color:#fff
    style MCP3 fill:#D0021B,color:#fff
```

---

## Diagram 2: Query Flow - Behind the Scenes (Slide 16)

```mermaid
sequenceDiagram
    participant User
    participant Streamlit
    participant Agent as Langchain Agent
    participant MCP as MCP Server
    participant DB as Database

    User->>Streamlit: "Add note: Meeting at 3pm"
    Streamlit->>Agent: Forward query

    Note over Agent: Analyze query<br/>Select tool: notes_tool

    Agent->>MCP: POST /mcp/tools/notes_tool<br/>{"action": "add", "content": "Meeting at 3pm"}

    Note over MCP: Execute tool<br/>implementation

    MCP->>DB: INSERT INTO notes<br/>VALUES ('Meeting at 3pm')
    DB-->>MCP: note_id = 123

    MCP-->>Agent: {"status": "success", "note_id": 123}

    Note over Agent: Synthesize response<br/>using LLM

    Agent-->>Streamlit: "I've added your note: 'Meeting at 3pm'"
    Streamlit-->>User: Display response

    style Agent fill:#4A90E2,color:#fff
    style MCP fill:#7ED321,color:#fff
```

---

## Diagram 3: ReAct Agent Loop (Slide 21)

```mermaid
graph TD
    Start([User Query]) --> Think1{Agent: Thought}
    Think1 --> |"Need to search proteins"| Action1[Action: blast_search]
    Action1 --> Observe1[Observation: Found 5 hits]

    Observe1 --> Think2{Agent: Thought}
    Think2 --> |"Need details on top hit"| Action2[Action: uniprot_info]
    Action2 --> Observe2[Observation: P12345 is Insulin]

    Observe2 --> Think3{Agent: Thought}
    Think3 --> |"Have enough info"| Final[Final Answer]
    Final --> End([Return to User])

    style Think1 fill:#FFE4B5
    style Think2 fill:#FFE4B5
    style Think3 fill:#FFE4B5
    style Action1 fill:#90EE90
    style Action2 fill:#90EE90
    style Observe1 fill:#87CEEB
    style Observe2 fill:#87CEEB
    style Final fill:#FFB6C1
```

---

## Diagram 4: Single Agent vs Multi-Agent (Slide 22)

### Single Agent Architecture

```mermaid
graph LR
    User --> Agent[Agent]
    Agent --> Tools[All Tools]
    Tools --> Response[Response]
    Response --> User

    style Agent fill:#4A90E2,color:#fff
```

### Multi-Agent Architecture

```mermaid
graph TD
    User --> Planner[Planner Agent]
    Planner --> |Creates Plan| Supervisor[Supervisor Agent]

    Supervisor --> Worker1[Worker 1<br/>RAG Tools]
    Supervisor --> Worker2[Worker 2<br/>BLAST Tools]
    Supervisor --> Worker3[Worker 3<br/>Code Execution]

    Worker1 --> Result1[Result 1]
    Worker2 --> Result2[Result 2]
    Worker3 --> Result3[Result 3]

    Result1 --> Supervisor
    Result2 --> Supervisor
    Result3 --> Supervisor

    Supervisor --> Synthesis[Synthesize Results]
    Synthesis --> User

    style Planner fill:#9B59B6,color:#fff
    style Supervisor fill:#E74C3C,color:#fff
    style Worker1 fill:#3498DB,color:#fff
    style Worker2 fill:#2ECC71,color:#fff
    style Worker3 fill:#F39C12,color:#fff
```

---

## Diagram 5: MCP Tool Registration Flow (Slide 17)

```mermaid
graph TB
    subgraph "Tool Implementation"
        ToolCode["tools/notes.py<br/>@mcp.tool()<br/>async def notes_tool()"]
    end

    subgraph "MCP Server Registration"
        MainPy["main.py<br/>from tools import notes<br/>notes.register_tools(mcp)"]
    end

    subgraph "Langchain Wrapper"
        Schema["NotesToolInput<br/>(Pydantic Schema)"]
        Wrapper["MCPToolWrapper<br/>(HTTP Client)"]
    end

    subgraph "Agent"
        AgentCode["langchain_agent.py<br/>tools = [<br/>  get_mcp_notes_tool(),<br/>  ...<br/>]"]
    end

    ToolCode --> MainPy
    MainPy --> |"HTTP Endpoint"| Wrapper
    Schema --> Wrapper
    Wrapper --> AgentCode

    style ToolCode fill:#7ED321,color:#fff
    style MainPy fill:#4A90E2,color:#fff
    style Wrapper fill:#F5A623,color:#fff
    style AgentCode fill:#D0021B,color:#fff
```

---

## Diagram 6: RAG Architecture (Slide 20)

```mermaid
graph TB
    subgraph "Document Upload"
        PDF[PDF Document] --> Parse[Parse Text]
        Parse --> Chunk[Chunk into Segments]
        Chunk --> Embed1[Generate Embeddings]
        Embed1 --> Store[Store in ChromaDB]
    end

    subgraph "Query Time"
        Query[User Query] --> Embed2[Embed Query]
        Embed2 --> Search[Similarity Search<br/>in ChromaDB]
        Store --> Search
        Search --> Retrieve[Retrieve Top K Chunks]
        Retrieve --> LLM[Send to LLM<br/>as Context]
        LLM --> Answer[Generate Answer]
    end

    style Parse fill:#7ED321,color:#fff
    style Embed1 fill:#4A90E2,color:#fff
    style Store fill:#F5A623,color:#fff
    style Search fill:#D0021B,color:#fff
    style LLM fill:#9B59B6,color:#fff
```

---

## Diagram 7: Chapter Progression (Slide 9)

```mermaid
graph LR
    Ch0[Chapter 0<br/>Introduction<br/>Core Tools] --> Ch1[Chapter 1<br/>Main Architecture<br/>Langchain Agent]
    Ch1 --> Ch2[Chapter 2<br/>HPC Tools<br/>Chain-of-Thought]
    Ch2 --> Ch3[Chapter 3<br/>Sandbox<br/>Multi-Agent]
    Ch3 --> Ch4[Chapter 4<br/>Kubernetes<br/>Helm Deployment]
    Ch4 --> Ch5[Chapter 5<br/>OpenWebUI<br/>Integration]
    Ch5 --> Ch6[Chapter 6<br/>Agent Gateway<br/>Dynamic Tools]

    style Ch0 fill:#7ED321,color:#fff
    style Ch1 fill:#7ED321,color:#fff
    style Ch2 fill:#7ED321,color:#fff
    style Ch3 fill:#7ED321,color:#fff
    style Ch4 fill:#4A90E2,color:#fff
    style Ch5 fill:#4A90E2,color:#fff
    style Ch6 fill:#4A90E2,color:#fff

    Ch0 -.->|Podman ✓| Podman1[ ]
    Ch1 -.->|Podman ✓| Podman2[ ]
    Ch2 -.->|Podman ✓| Podman3[ ]
    Ch3 -.->|Podman ✓| Podman4[ ]
    Ch4 -.->|Docker Only| Docker1[ ]
    Ch5 -.->|Docker Only| Docker2[ ]
    Ch6 -.->|Docker Only| Docker3[ ]

    style Podman1 fill:#2ECC71
    style Podman2 fill:#2ECC71
    style Podman3 fill:#2ECC71
    style Podman4 fill:#2ECC71
    style Docker1 fill:#3498DB
    style Docker2 fill:#3498DB
    style Docker3 fill:#3498DB
```

---

## Diagram 8: Deployment Options (Slide 31)

```mermaid
graph TB
    subgraph "Development"
        Dev[Single Server<br/>Docker Compose]
        Dev_Desc["• All services on one machine<br/>• Good for: Dev, demos<br/>• Chapters 0-3"]
    end

    subgraph "Enterprise"
        K8s[Kubernetes<br/>Helm Charts]
        K8s_Desc["• Scalable, HA<br/>• Good for: Production<br/>• Chapter 4"]
    end

    subgraph "Team Deployment"
        OpenWebUI[OpenWebUI<br/>Integration]
        OpenWebUI_Desc["• User management<br/>• Good for: Teams<br/>• Chapter 5"]
    end

    subgraph "Advanced"
        Gateway[Agent Gateway<br/>OpenAI API]
        Gateway_Desc["• Dynamic tools<br/>• Good for: Extensibility<br/>• Chapter 6"]
    end

    Dev --> Dev_Desc
    K8s --> K8s_Desc
    OpenWebUI --> OpenWebUI_Desc
    Gateway --> Gateway_Desc

    style Dev fill:#7ED321,color:#fff
    style K8s fill:#4A90E2,color:#fff
    style OpenWebUI fill:#F5A623,color:#fff
    style Gateway fill:#9B59B6,color:#fff
```

---

## Diagram 9: Container Status Check (Slide 13)

```mermaid
graph LR
    Start([Start]) --> Check{docker ps}

    Check -->|4 containers running| Success[✓ All Services Up]
    Check -->|< 4 containers| Debug[Debug]

    Success --> Test1[Test: curl localhost:11434]
    Success --> Test2[Test: curl localhost:8080/health]
    Success --> Test3[Test: Open localhost:8501]

    Test1 --> |OK| Ready1[Ollama ✓]
    Test2 --> |OK| Ready2[MCP Server ✓]
    Test3 --> |OK| Ready3[Streamlit ✓]

    Debug --> Logs[Check Logs:<br/>docker logs container_name]
    Logs --> Fix[Fix Issues]
    Fix --> Check

    style Success fill:#2ECC71,color:#fff
    style Debug fill:#E74C3C,color:#fff
    style Ready1 fill:#2ECC71,color:#fff
    style Ready2 fill:#2ECC71,color:#fff
    style Ready3 fill:#2ECC71,color:#fff
```

---

## Diagram 10: Scientific Workflow Example (Slide 23-26)

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant RAG as RAG Tool
    participant BLAST as BLAST Tool
    participant UniProt as UniProt Tool
    participant PubChem as PubChem Tool

    User->>Agent: "Analyze protein from my document,<br/>find similar sequences,<br/>suggest drug targets"

    Note over Agent: Step 1: Extract info from doc
    Agent->>RAG: Query document for protein sequence
    RAG-->>Agent: Found sequence: MKVLWA...

    Note over Agent: Step 2: Search for similar proteins
    Agent->>BLAST: Search sequence MKVLWA...
    BLAST-->>Agent: Top hit: P12345 (E-value: 1e-50)

    Note over Agent: Step 3: Get protein details
    Agent->>UniProt: Get info for P12345
    UniProt-->>Agent: P12345 = Insulin (Homo sapiens)

    Note over Agent: Step 4: Find drug targets
    Agent->>PubChem: Search compounds targeting insulin
    PubChem-->>Agent: Found 15 compounds

    Note over Agent: Synthesize results
    Agent-->>User: "Found Insulin protein<br/>15 potential drug compounds:<br/>1. Metformin (CID: 4091)<br/>2. Insulin glargine (CID: 5311281)<br/>..."

    style Agent fill:#4A90E2,color:#fff
```

---

## Diagram 11: LLM Provider Architecture (Slide 32)

```mermaid
graph TB
    App[ADEPT Application] --> LLMClient[LLM Agnostic Client]

    LLMClient --> LiteLLM[LiteLLM Router]

    LiteLLM --> OpenAI[OpenAI<br/>gpt-4o, gpt-4o-mini]
    LiteLLM --> Azure[Azure OpenAI<br/>Custom deployments]
    LiteLLM --> Ollama[Ollama<br/>llama3.2, mistral]
    LiteLLM --> NVIDIA[NVIDIA NIM<br/>llama-3.1-70b]
    LiteLLM --> Anthropic[Anthropic<br/>claude-opus-4-6]
    LiteLLM --> Other[100+ other providers]

    style App fill:#9B59B6,color:#fff
    style LLMClient fill:#E74C3C,color:#fff
    style LiteLLM fill:#F39C12,color:#fff
    style OpenAI fill:#2ECC71,color:#fff
    style Azure fill:#3498DB,color:#fff
    style Ollama fill:#E67E22,color:#fff
    style NVIDIA fill:#1ABC9C,color:#fff
```

---

## Diagram 12: Testing Workflow (Slide 34)

```mermaid
graph TD
    Start([Start Tests]) --> PreReq[Prerequisites Tests]

    PreReq --> |✓| Env[Environment Tests]
    PreReq --> |✗| Fail1[❌ Install missing tools]

    Env --> |✓| Config[Configuration Tests]
    Env --> |✗| Fail2[❌ Fix .env or config files]

    Config --> |✓| Deploy{Deploy Services?}
    Config --> |✗| Fail3[❌ Fix compose files]

    Deploy --> |Yes| Runtime[Runtime Tests]
    Deploy --> |No| Report1[Report: Config OK]

    Runtime --> |✓| Network[Network Tests]
    Runtime --> |✗| Fail4[❌ Check container logs]

    Network --> |✓| Health[Health Checks]
    Network --> |✗| Fail5[❌ Check ports/firewall]

    Health --> |✓| Success[✅ All Tests Passed]
    Health --> |✗| Fail6[❌ Check endpoints]

    Fail1 --> End([Exit])
    Fail2 --> End
    Fail3 --> End
    Fail4 --> End
    Fail5 --> End
    Fail6 --> End
    Report1 --> End
    Success --> End

    style Success fill:#2ECC71,color:#fff
    style Fail1 fill:#E74C3C,color:#fff
    style Fail2 fill:#E74C3C,color:#fff
    style Fail3 fill:#E74C3C,color:#fff
    style Fail4 fill:#E74C3C,color:#fff
    style Fail5 fill:#E74C3C,color:#fff
    style Fail6 fill:#E74C3C,color:#fff
```

---

## Diagram 13: Workshop Timeline (For Facilitator)

```mermaid
gantt
    title 2-Hour Workshop Timeline
    dateFormat HH:mm
    axisFormat %H:%M

    section Setup
    Intro & Welcome           :done, 00:00, 10m
    Prerequisites Check       :done, 00:10, 5m

    section Architecture
    ADEPT Overview           :00:15, 10m
    Architecture Deep Dive   :00:25, 5m

    section Lab 1
    Deploy Chapter 0         :crit, 00:30, 15m
    Test & Verify            :00:45, 10m

    section Tools
    MCP Architecture         :00:55, 10m
    Agent Decision Making    :01:05, 10m

    section Lab 2
    RAG Upload               :crit, 01:15, 5m
    Scientific Workflow      :crit, 01:20, 15m

    section Advanced
    Advanced Features        :01:35, 10m
    Deployment Options       :01:45, 5m

    section Wrap-up
    Q&A                      :01:50, 10m
```

---

## Usage Examples

### Rendering Individual Diagrams

**Mermaid Live Editor:**
1. Go to https://mermaid.live/
2. Copy diagram code (including ```mermaid and ```)
3. Edit/customize
4. Click "Download PNG" or "Download SVG"

**Command Line:**
```bash
# Extract diagram to file
cat ADEPT-Workshop-Diagrams.md | \
  sed -n '/```mermaid/,/```/p' | \
  head -n -1 | tail -n +2 > diagram1.mmd

# Render
mmdc -i diagram1.mmd -o diagram1.png \
  -b transparent \
  -w 1920 \
  -H 1080
```

**Python Script:**
```python
import subprocess
import re

# Extract all diagrams from markdown
with open('ADEPT-Workshop-Diagrams.md', 'r') as f:
    content = f.read()

diagrams = re.findall(r'```mermaid\n(.*?)```', content, re.DOTALL)

for i, diagram in enumerate(diagrams):
    with open(f'diagram_{i+1}.mmd', 'w') as f:
        f.write(diagram)

    subprocess.run([
        'mmdc',
        '-i', f'diagram_{i+1}.mmd',
        '-o', f'diagram_{i+1}.png',
        '-b', 'transparent'
    ])
```

### Customization Options

**Color Themes:**
```mermaid
%%{init: {'theme':'dark'}}%%
graph TD
    ...
```

Available themes: default, dark, forest, neutral

**Custom Colors:**
```mermaid
graph TD
    A[Node] --> B[Node]
    style A fill:#f9f,stroke:#333,stroke-width:4px
    style B fill:#bbf,stroke:#f66,stroke-width:2px
```

**Font Size:**
```mermaid
%%{init: {'themeVariables': {'fontSize': '20px'}}}%%
graph TD
    ...
```

---

**End of Diagrams File**

These diagrams are ready to render and include in your workshop slides!
