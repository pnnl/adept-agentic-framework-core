"""Knowledge-base MCP tools: SQL ingest, SQL query, schema inspection, and CSV RAG.

Ported from Chapter 00 ``knowledge_base_tool.py`` with the following Chapter 03
adaptations:

* Import paths adjusted for Chapter 03 package layout (logger at package root,
  not in ``core/``).
* ``execute_sql`` enforces SELECT-only via ``sqlparse`` – INSERT/UPDATE/DROP are
  rejected before they reach the database.
* ``execute_sql`` caps result sets at ``SQL_MAX_ROWS`` (env var, default 500).
* Removed unused dead imports (``SQLDatabase``, ``create_engine``).
"""

from fastmcp import FastMCP, Context
from ..state_manager import (
    DATABASE_URL,
    get_chroma_client,
    execute_async_sql_query,
    get_async_table_info,
)
from ...logger_config import get_logger  # Chapter 03: logger at package root
import pandas as pd
import os
import re
import asyncio
import sqlite3
import json
import uuid
import sqlparse  # SELECT-only guardrail
from ...core.embedding_config import get_embedding_model  # noqa: F401 – used via chroma helper
from ...core.chroma_embedding_function import get_chroma_embedding_function

logger = get_logger(__name__)


def register_tools(mcp: FastMCP):

    @mcp.tool()
    async def ingest_data(ctx: Context, file_path: str, table_name: str):
        """Loads a CSV, TSV, XLS, or XLSX file into BOTH a SQLite table (for SQL
        queries) AND a ChromaDB RAG collection (for semantic search).  Call this
        once per file before using ``execute_sql`` or ``query_csv_rag``.

        Args:
            file_path: Absolute server-accessible path to the data file.
            table_name: Logical name for the SQL table (e.g. ``proteins``).
                        Non-alphanumeric characters are stripped automatically.
        """
        logger.info(f"Ingesting data from {file_path} into table '{table_name}'")
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension == ".csv":
                df = pd.read_csv(file_path, on_bad_lines="warn")
            elif file_extension == ".tsv":
                df = pd.read_csv(file_path, sep="\t", on_bad_lines="warn")
            elif file_extension in [".xls", ".xlsx"]:
                df = pd.read_excel(file_path, dtype=object)
            else:
                return {
                    "error": (
                        f"Unsupported file type: {file_extension}. "
                        "Only .csv, .tsv, .xls, .xlsx are supported."
                    )
                }

            # Sanitise table name: keep only alphanumerics and underscores.
            table_name = re.sub(r"[^a-zA-Z0-9_]", "", table_name)
            if not table_name:
                return {"error": "table_name is empty after sanitisation."}

            # --- 1. Write to SQLite via pandas (sync sqlite3 connection) ---
            db_file_path = DATABASE_URL.split("///")[-1]
            db_dir = os.path.dirname(db_file_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

            with sqlite3.connect(db_file_path) as con:
                df.to_sql(table_name, con, if_exists="replace", index=False)

            # --- 2. Index schema + sample in ChromaDB for RAG ---
            table_schema = pd.io.sql.get_schema(df, table_name)
            sample_data = df.head(5).to_string()
            rag_text = (
                f"Table Name: {table_name}\n\n"
                f"Schema:\n{table_schema}\n\n"
                f"Sample Data:\n{sample_data}"
            )

            chroma_client = await get_chroma_client()
            chroma_ef = get_chroma_embedding_function()
            csv_rag_collection = chroma_client.get_or_create_collection(
                name="csv_rag_collection", embedding_function=chroma_ef
            )
            csv_rag_collection.add(
                ids=[str(uuid.uuid4())],
                documents=[rag_text],
                metadatas=[{"table_name": table_name, "file_path": file_path}],
            )

            # Record file upload history in ChromaDB.
            file_history_collection = chroma_client.get_or_create_collection(
                name="file_history", embedding_function=chroma_ef
            )
            file_history_collection.add(
                ids=[str(uuid.uuid4())],
                documents=[
                    json.dumps(
                        {
                            "file_name": os.path.basename(file_path),
                            "table_name": table_name,
                        }
                    )
                ],
            )

            return {
                "status": "success",
                "message": (
                    f"Successfully ingested {len(df)} rows into table '{table_name}' "
                    "and updated the RAG knowledge base."
                ),
                "row_count": len(df),
                "table_name": table_name,
                "columns": list(df.columns),
            }
        except Exception as e:
            logger.error(f"Error ingesting data: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def execute_sql(ctx: Context, query: str):
        """Executes a read-only SQL SELECT query against the SQLite knowledge-base.

        Only SELECT statements are permitted.  INSERT, UPDATE, DELETE, DROP and
        other DDL/DML statements are rejected before execution.  Results are
        capped at ``SQL_MAX_ROWS`` rows (default 500, configurable via env var).

        Always call ``get_sql_schema`` first so you know the exact table and
        column names.

        Args:
            query: A valid SQLite SELECT statement.
        """
        logger.info(f"Executing SQL query: {query}")
        try:
            # SELECT-only guardrail via sqlparse
            parsed = sqlparse.parse(query.strip())
            if not parsed or parsed[0].get_type() != "SELECT":
                return {
                    "error": (
                        "Only SELECT statements are permitted. "
                        "INSERT, UPDATE, DELETE, and DDL statements are rejected."
                    )
                }

            result = await execute_async_sql_query(query)

            # Row cap
            max_rows = int(os.getenv("SQL_MAX_ROWS", "500"))
            if isinstance(result, list) and len(result) > max_rows:
                result = result[:max_rows]
                logger.info(f"Result set truncated to {max_rows} rows (SQL_MAX_ROWS).")

            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error executing SQL query: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def get_sql_schema(ctx: Context):
        """Returns the schema (table names and column names/types) for all tables
        currently in the SQLite knowledge-base database.

        Always call this before writing a SQL query so you know the exact column
        names and their types.
        """
        logger.info("Getting SQL schema from database")
        try:
            schema = await get_async_table_info()
            return {"schemas": schema}
        except Exception as e:
            logger.error(f"Error getting SQL schema: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def query_csv_rag(ctx: Context, query: str):
        """Performs a semantic similarity search over previously ingested tabular
        data (files loaded via ``ingest_data``).

        Use this for open-ended, exploratory questions about data content.  For
        precise numeric or aggregation queries, use ``execute_sql`` instead.

        Args:
            query: A natural language question about the ingested data.
        """
        logger.info(f"Performing RAG query on CSV data: {query}")
        try:
            chroma_client = await get_chroma_client()
            chroma_ef = get_chroma_embedding_function()
            csv_rag_collection = chroma_client.get_or_create_collection(
                name="csv_rag_collection", embedding_function=chroma_ef
            )

            embedded_query = chroma_ef([query])
            results = csv_rag_collection.query(
                query_embeddings=embedded_query,
                n_results=5,
            )
            return {"status": "success", "documents": results["documents"]}
        except Exception as e:
            logger.error(f"Error performing RAG query: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def save_note(ctx: Context, note: str):
        """Saves a freeform text note to the ChromaDB notes collection.

        Args:
            note: The text content to save.
        """
        logger.info("Saving note")
        try:
            chroma_client = await get_chroma_client()
            chroma_ef = get_chroma_embedding_function()
            notes_collection = chroma_client.get_or_create_collection(
                name="notes", embedding_function=chroma_ef
            )
            notes_collection.add(ids=[str(uuid.uuid4())], documents=[note])
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error saving note: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def list_notes(ctx: Context):
        """Retrieves all previously saved notes from the ChromaDB notes collection."""
        logger.info("Listing notes")
        try:
            chroma_client = await get_chroma_client()
            chroma_ef = get_chroma_embedding_function()
            notes_collection = chroma_client.get_or_create_collection(
                name="notes", embedding_function=chroma_ef
            )
            notes = notes_collection.get()
            return {"notes": notes["documents"]}
        except Exception as e:
            logger.error(f"Error listing notes: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def list_files(ctx: Context):
        """Returns the history of all files that have been ingested via ``ingest_data``."""
        logger.info("Listing ingested files")
        try:
            chroma_client = await get_chroma_client()
            chroma_ef = get_chroma_embedding_function()
            file_history_collection = chroma_client.get_or_create_collection(
                name="file_history", embedding_function=chroma_ef
            )
            files = file_history_collection.get()
            return {"files": files["documents"]}
        except Exception as e:
            logger.error(f"Error listing files: {e}", exc_info=True)
            return {"error": str(e)}
