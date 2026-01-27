from fastmcp import FastMCP, Context
from ..state_manager import (
    DATABASE_URL,
    get_chroma_client,
    execute_async_sql_query,
    get_async_table_info,
)
from ...core.logger_config import get_logger
import pandas as pd
import os
import re
import asyncio
import sqlite3
import json
import uuid
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine
from ...core.embedding_config import get_embedding_model
from ...core.chroma_embedding_function import get_chroma_embedding_function

logger = get_logger(__name__)


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def ingest_data(ctx: Context, file_path: str, table_name: str):
        logger.info(f"Ingesting data from {file_path} into table {table_name}")
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
                    "error": f"Unsupported file type: {file_extension}. Only .csv, .tsv, .xls, .xlsx are supported."
                }

            # Sanitize table name
            table_name = re.sub(r"[^a-zA-Z0-9_]", "", table_name)

            # Correctly parse the database file path from the DATABASE_URL
            db_path = DATABASE_URL.split("///")[1]

            # Let pandas handle the synchronous connection
            with sqlite3.connect(db_path) as con:
                df.to_sql(table_name, con, if_exists="replace", index=False)

            # Generate text representation for RAG
            table_schema = pd.io.sql.get_schema(df, table_name)
            sample_data = df.head(5).to_string()
            rag_text = f"Table Name: {table_name}\n\nSchema:\n{table_schema}\n\nSample Data:\n{sample_data}"

            # Store in ChromaDB for RAG
            chroma_client = await get_chroma_client()
            chroma_embedding_function = get_chroma_embedding_function()
            csv_rag_collection = chroma_client.get_or_create_collection(
                name="csv_rag_collection", embedding_function=chroma_embedding_function
            )

            csv_rag_collection.add(
                ids=[str(uuid.uuid4())],
                documents=[rag_text],
                metadatas=[{"table_name": table_name, "file_path": file_path}],
            )

            # Record file upload in ChromaDB
            file_history_collection = chroma_client.get_or_create_collection(
                name="file_history", embedding_function=chroma_embedding_function
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
                "message": f"Successfully ingested {len(df)} rows into table {table_name} and updated RAG knowledge base.",
            }
        except Exception as e:
            logger.error(f"Error ingesting data: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def execute_sql(ctx: Context, query: str):
        logger.info(f"Executing SQL query: {query}")
        try:
            result = await execute_async_sql_query(query)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error executing SQL query: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def save_note(ctx: Context, note: str):
        logger.info(f"Saving note")
        try:
            chroma_client = await get_chroma_client()
            chroma_embedding_function = get_chroma_embedding_function()
            notes_collection = chroma_client.get_or_create_collection(
                name="notes", embedding_function=chroma_embedding_function
            )
            notes_collection.add(ids=[str(uuid.uuid4())], documents=[note])
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error saving note: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def list_notes(ctx: Context):
        logger.info(f"Listing notes")
        try:
            chroma_client = await get_chroma_client()
            chroma_embedding_function = get_chroma_embedding_function()
            notes_collection = chroma_client.get_or_create_collection(
                name="notes", embedding_function=chroma_embedding_function
            )
            notes = notes_collection.get()
            return {"notes": notes["documents"]}
        except Exception as e:
            logger.error(f"Error listing notes: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def list_files(ctx: Context):
        logger.info(f"Listing files")
        try:
            chroma_client = await get_chroma_client()
            chroma_embedding_function = get_chroma_embedding_function()
            file_history_collection = chroma_client.get_or_create_collection(
                name="file_history", embedding_function=chroma_embedding_function
            )
            files = file_history_collection.get()
            return {"files": files["documents"]}
        except Exception as e:
            logger.error(f"Error listing files: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def get_sql_schema(ctx: Context):
        logger.info(f"Getting SQL schema from database")
        try:
            schema = await get_async_table_info()
            return {"schemas": schema}
        except Exception as e:
            logger.error(f"Error getting SQL schema: {e}", exc_info=True)
            return {"error": str(e)}

    @mcp.tool()
    async def query_csv_rag(ctx: Context, query: str):
        logger.info(f"Performing RAG query on CSV data: {query}")
        try:
            chroma_client = await get_chroma_client()
            chroma_embedding_function = get_chroma_embedding_function()
            csv_rag_collection = chroma_client.get_or_create_collection(
                name="csv_rag_collection", embedding_function=chroma_embedding_function
            )

            # Embed the query manually
            embedded_query = chroma_embedding_function([query])

            results = csv_rag_collection.query(
                query_embeddings=embedded_query,
                n_results=5,  # Retrieve top 5 relevant documents
            )
            return {"status": "success", "documents": results["documents"]}
        except Exception as e:
            logger.error(f"Error performing RAG query: {e}", exc_info=True)
            return {"error": str(e)}
