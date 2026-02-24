# SQL Query Support – Integration Plan for Chapter 03

## Source: Chapter 00

Chapter 00 already has a complete, working SQL + RAG agent. This plan is a direct **port and adaptation** of that pattern into Chapter 03's multi-server, multi-agent architecture.

---

## What Chapter 00 Already Implements

### `state_manager.py` – persistence layer

| Function                                    | What it does                                                                       |
| ------------------------------------------- | ---------------------------------------------------------------------------------- |
| `DATABASE_URL`                              | `sqlite+aiosqlite:///./data/agentic_framework.db` (from env)                       |
| `get_async_db_engine()`                     | Singleton SQLAlchemy async engine (`create_async_engine`)                          |
| `execute_async_sql_query(query)`            | Runs any SQL; returns `list[dict]` for SELECT, `{"status": "success"}` for DDL/DML |
| `get_async_table_info()`                    | Uses `inspect(conn)` via `run_sync` to return all table schemas as a string        |
| `get_chroma_client()`                       | Singleton ChromaDB persistent client                                               |
| `initialize_db()` / `close_db_connection()` | Lifecycle hooks                                                                    |

### `mcp_server/tools/knowledge_base_tool.py` – MCP tools (7 tools)

| Tool                                 | Description                                                                                      |
| ------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `ingest_data(file_path, table_name)` | CSV/TSV/XLS/XLSX → **SQLite** via `pandas.to_sql` + schema+sample summary → **ChromaDB** for RAG |
| `execute_sql(query)`                 | Passes raw SQL to `execute_async_sql_query`; no guardrails in ch00                               |
| `get_sql_schema()`                   | Returns full schema string via `get_async_table_info()`                                          |
| `query_csv_rag(query)`               | Embed query → ChromaDB similarity search over ingested table summaries                           |
| `save_note(note)` / `list_notes()`   | Freeform notes in ChromaDB                                                                       |
| `list_files()`                       | File ingestion history from ChromaDB                                                             |

### `scientific_workflow/mcp_langchain_tools.py` – LangChain wrappers

Chapter 00 uses the same `MCPToolWrapper(BaseTool)` pattern that already exists in Chapter 03. Factory functions exposed:
- `get_mcp_sql_tool_langchain()` — wraps `execute_sql`
- `get_mcp_ingest_data_tool_langchain()` — wraps `ingest_data`
- `get_mcp_sql_schema_tool_langchain()` — wraps `get_sql_schema`
- `get_mcp_rag_tool_langchain()` — wraps `query_csv_rag`
- `get_mcp_list_files_tool_langchain()` — wraps `list_files`

---

## What Chapter 03 Already Has (Gaps to Fill)

Chapter 03 inherits the Chapter 01 RAG pipeline (ChromaDB-backed, per-session), but its `state_manager.py` is **ChromaDB-only** — it has no SQLite engine, no `execute_async_sql_query`, and no `get_async_table_info`. The `knowledge_base_tool.py` from Chapter 00 does not exist in Chapter 03.

---

## Implementation Plan

### Step 1 – Extend `state_manager.py` with the SQL engine

The Chapter 00 pattern maps cleanly. Add to Chapter 03's `mcp_server/state_manager.py`:

```python
# Add these imports
import aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect

# Config (read from .env)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/agentic_framework.db")

# Singleton async engine (mirrors chapter-00 pattern exactly)
_async_engine = None
_async_engine_lock = asyncio.Lock()

async def get_async_db_engine():
    ...

async def execute_async_sql_query(query: str) -> list[dict]:
    """SELECT → list[dict], DDL/DML → {"status": "success"}"""
    ...

async def get_async_table_info() -> str:
    """Returns all table schemas as a human-readable string for the LLM."""
    ...
```

The existing `initialize_db()` call in `main.py` should also call `get_async_db_engine()`.

### Step 2 – Port `knowledge_base_tool.py` from Chapter 00

Copy `chapter-00/src/.../tools/knowledge_base_tool.py` to Chapter 03 with these adaptations:

| Chapter 00                                                                                                   | Chapter 03 adaptation                                                                 |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `from ..state_manager import DATABASE_URL, get_chroma_client, execute_async_sql_query, get_async_table_info` | Same imports — functions added in Step 1                                              |
| `from ...core.logger_config import get_logger`                                                               | `from ...logger_config import get_logger` (Chapter 03 path)                           |
| `from ...core.embedding_config import get_embedding_model`                                                   | Use Chapter 03's `LLMAgnosticClient` embedding approach OR port `embedding_config.py` |
| `from ...core.chroma_embedding_function import get_chroma_embedding_function`                                | Port `chroma_embedding_function.py` from Chapter 00 if not present                    |
| No SQL guardrails on `execute_sql`                                                                           | **Add SELECT-only enforcement** using `sqlparse` (see Step 3)                         |

Check which embedding files Chapter 03 already has:

```bash
ls chapter-03/src/agentic_framework_pkg/core/
```

If `embedding_config.py` and `chroma_embedding_function.py` are absent, copy them from Chapter 00.

### Step 3 – Add SELECT-only guardrail to `execute_sql`

Chapter 00's `execute_sql` passes any SQL through. For Chapter 03 add:

```python
import sqlparse

@mcp.tool()
async def execute_sql(ctx: Context, query: str):
    parsed = sqlparse.parse(query.strip())
    if not parsed or parsed[0].get_type() != "SELECT":
        return {"error": "Only SELECT statements are permitted."}
    result = await execute_async_sql_query(query)
    # Cap at SQL_MAX_ROWS (default 500)
    max_rows = int(os.getenv("SQL_MAX_ROWS", "500"))
    if isinstance(result, list) and len(result) > max_rows:
        result = result[:max_rows]
    return {"status": "success", "result": result}
```

### Step 4 – Register in `mcp_server/main.py`

```python
from .tools import knowledge_base_tool   # or sql_query_tool if renamed

# Inside start_mcp_server() after existing registrations:
knowledge_base_tool.register_tools(mcp)
```

Also ensure `initialize_db()` in `main.py` calls `get_async_db_engine()`.

### Step 5 – Add LangChain wrappers to `mcp_langchain_tools.py`

Port the five factory functions from Chapter 00 verbatim, updating only the `mcp_client_url` env var to `DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN` (the Chapter 03 convention):

```python
class SQLQueryInput(BaseModel):
    query: str = Field(
        description="A SQLite SELECT statement. Call get_sql_schema first to discover table and column names."
    )
    mcp_session_id: Optional[str] = Field(None, description="MCP session ID.")

def get_mcp_sql_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="execute_sql",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="execute_sql",
        description="Executes a read-only SQL SELECT query against the database. "
                    "Always call get_sql_schema first. Only SELECT is permitted.",
        args_schema=SQLQueryInput,
        mcp_session_id=mcp_session_id,
    )

# + get_mcp_ingest_data_tool_langchain
# + get_mcp_sql_schema_tool_langchain
# + get_mcp_rag_tool_langchain
# + get_mcp_list_files_tool_langchain
```

### Step 6 – Expose tools to agents

**`langchain_agent.py`** — add to `self.tools`:
```python
get_mcp_ingest_data_tool_langchain,
get_mcp_sql_schema_tool_langchain,
get_mcp_sql_tool_langchain,
get_mcp_rag_tool_langchain,
get_mcp_list_files_tool_langchain,
```

Update system prompt to include:
```
You can work with structured data files (CSV, Excel) using two approaches:
1. SQL queries (precise, structured): ingest_data → get_sql_schema → execute_sql
2. Semantic search (fuzzy, contextual): ingest_data → query_csv_rag
Use SQL for counting, aggregation, filtering. Use RAG for open-ended questions about content.
```

**`multi_agent_tool.py`** — add the same five tools to `get_all_mcp_tools()` so data-analyst worker agents can use them.

### Step 7 – Dependencies

Add to `pyproject.toml`:

```toml
"sqlalchemy[asyncio]>=2.0.0",  # async engine
"sqlparse>=0.5.0",             # SELECT-only guardrail
```

`aiosqlite` is already listed. `pandas` is already present. `sqlalchemy` may already be present (check via `uv run python -c "import sqlalchemy"`).

### Step 8 – `DATABASE_URL` in `.env.example`

```bash
# SQLite database for SQL query tool (chapter 03)
DATABASE_URL="sqlite+aiosqlite:///./data/agentic_framework.db"
SQL_MAX_ROWS=500   # Cap on rows returned by execute_sql
```

### Step 9 – Sample data file

Add `data/sample_proteomics.csv` (~100 synthetic rows):

```
protein_id,gene_name,molecular_weight_kda,expression_level,p_value,organism,cellular_location
P12345,TP53,43.7,3.2,0.001,human,nucleus
P67890,EGFR,134.3,1.8,0.045,human,membrane
...
```

Enables realistic test queries:
- *"How many human proteins have expression_level > 2.0?"*
- *"What is the average molecular weight grouped by organism?"*
- *"Show the top 5 proteins by expression level in human."*

---

## Testing Plan

New class `TestSqlQueryToolSmoke` in `tests/test_mcp_tools_smoke.py`.

### Unit tests (no Docker required, `uv run pytest -m "not slow"`)

| Test                                                | What it checks                                                                       |
| --------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `test_ingest_data_creates_table`                    | Mock `aiosqlite`/`to_sql`; verify table is created with correct name                 |
| `test_get_sql_schema_returns_columns`               | `get_async_table_info` returns expected schema string                                |
| `test_execute_sql_select_returns_rows`              | Mocked engine returns rows; tool wraps them in `{"status":"success","result":[...]}` |
| `test_execute_sql_rejects_drop_table`               | `sqlparse` block returns error dict, does not raise                                  |
| `test_execute_sql_rejects_insert`                   | Same                                                                                 |
| `test_execute_sql_rejects_update`                   | Same                                                                                 |
| `test_execute_sql_caps_result_rows`                 | > 500 rows truncated to 500                                                          |
| `test_sql_langchain_schemas_valid`                  | `SQLQueryInput`, `IngestDataInput` accept valid inputs                               |
| `test_sql_wrapper_descriptions_mention_schema_step` | Tool descriptions mention `get_sql_schema` so LLM knows the workflow                 |

### Integration tests (`@pytest.mark.slow`, require Docker + shared volume)

| Test                              | Agent query                                                                        |
| --------------------------------- | ---------------------------------------------------------------------------------- |
| `test_sql_ingest_and_count`       | *"Load sample_proteomics.csv and count proteins with expression > 2.0"*            |
| `test_sql_aggregation`            | *"What is the average molecular weight grouped by organism?"*                      |
| `test_sql_top_n`                  | *"Give me the top 5 proteins by expression level"*                                 |
| `test_rag_query_on_ingested_data` | *"Search the ingested data for membrane-associated proteins"*                      |
| `test_sql_and_rag_combined`       | *"Find membrane proteins using RAG, then use SQL to get their average expression"* |

---

## Data Flow Diagram

```
User: "Load proteins.csv and how many human proteins have p_value < 0.05?"
        │
        ▼
Agent → ingest_data(file_path="proteins.csv", table_name="proteins")
            │
            ├─ pandas.read_csv() → sqlite3.connect() → df.to_sql("proteins", ...)
            │                      [proteins table in agentic_framework.db]
            │
            └─ schema + sample → ChromaDB "csv_rag_collection"
                                  [for future RAG queries on same data]
        │
        ▼
Agent → get_sql_schema()
    ← "Table: proteins (protein_id TEXT, gene_name TEXT, expression_level REAL,
                          p_value REAL, organism TEXT, ...)"
        │
        ▼
Agent → execute_sql("SELECT COUNT(*) as cnt FROM proteins
                     WHERE organism='human' AND p_value < 0.05")
    ← {"status": "success", "result": [{"cnt": 31}]}
        │
        ▼
"There are 31 human proteins with p_value < 0.05."
```

---

## Files to Create / Modify

| Action              | File                                                                                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Modify**          | `src/agentic_framework_pkg/mcp_server/state_manager.py` – add `DATABASE_URL`, `get_async_db_engine`, `execute_async_sql_query`, `get_async_table_info` |
| **Copy + adapt**    | `src/agentic_framework_pkg/mcp_server/tools/knowledge_base_tool.py` (from Chapter 00) – add SELECT guardrail + row cap                                 |
| **Copy if missing** | `src/agentic_framework_pkg/core/embedding_config.py` (from Chapter 00)                                                                                 |
| **Copy if missing** | `src/agentic_framework_pkg/core/chroma_embedding_function.py` (from Chapter 00)                                                                        |
| **Modify**          | `src/agentic_framework_pkg/mcp_server/main.py` – register `knowledge_base_tool`, call `get_async_db_engine()` in `initialize_db`                       |
| **Modify**          | `src/agentic_framework_pkg/scientific_workflow/mcp_langchain_tools.py` – add 5 SQL/RAG factory functions                                               |
| **Modify**          | `src/agentic_framework_pkg/scientific_workflow/langchain_agent.py` – add 5 tools + update system prompt                                                |
| **Modify**          | `src/agentic_framework_pkg/mcp_server/tools/multi_agent_tool.py` – add 5 tools to `get_all_mcp_tools()`                                                |
| **Modify**          | `pyproject.toml` – add `sqlalchemy[asyncio]>=2.0.0`, `sqlparse>=0.5.0`                                                                                 |
| **Modify**          | `.env.example` – add `DATABASE_URL`, `SQL_MAX_ROWS`                                                                                                    |
| **Create**          | `data/sample_proteomics.csv` – synthetic test data                                                                                                     |
| **Modify**          | `tests/test_mcp_tools_smoke.py` – add `TestSqlQueryToolSmoke`                                                                                          |

---

## Key Differences from Chapter 00

| Concern           | Chapter 00              | Chapter 03 (this plan)                                 |
| ----------------- | ----------------------- | ------------------------------------------------------ |
| SQL guardrail     | None — any SQL accepted | `sqlparse` rejects non-SELECT                          |
| Row cap           | None                    | `SQL_MAX_ROWS` env var (default 500)                   |
| Session isolation | Single shared DB        | Still single DB (shared upload dir pattern)            |
| Tool wrappers     | Simple `MCPToolWrapper` | Same pattern + `mcp_session_id` param added            |
| Multi-agent       | N/A                     | Tools added to worker agents via `get_all_mcp_tools()` |

---

## Background: What Chapter 01 Already Provided (context only)

Chapter 01 introduced two data-access patterns that Chapter 03 also inherits:

| Component               | File                                 | What it does                                                                                                                                                 |
| ----------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **RAG (vector search)** | `mcp_server/tools/csv_rag_tool.py`   | Reads CSV / XLSX / PDF / DOCX, chunks text, embeds via `LLMAgnosticClient`, stores chunks in ChromaDB. A semantic query returns the closest matching chunks. |
| **Vector store**        | `mcp_server/vector_store_manager.py` | Singleton ChromaDB wrapper (`add_documents`, `query_collection`). Session-scoped collections named `{session_id}_{file_id}`.                                 |
| **Session state**       | `mcp_server/state_manager.py`        | Tracks uploaded-file metadata (file ID, collection name, segment count) in ChromaDB.                                                                         |

### The gap

RAG answers *"what does this document say about X?"* — semantic, approximate.  
It cannot answer *"how many rows have value > 5?"* or *"aggregate column Y by group Z"*. Tabular, structured questions require **SQL**.

`aiosqlite` is already listed in `pyproject.toml` but is unused. The full implementation plan above (Steps 1–9) supersedes the earlier chapter-01-based approach.
