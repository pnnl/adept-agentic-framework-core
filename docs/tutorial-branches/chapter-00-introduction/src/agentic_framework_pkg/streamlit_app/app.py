import streamlit as st
import os
import uuid
import json
import asyncio
import time
from typing import List, Dict

from agentic_framework_pkg.scientific_workflow.langchain_agent import (
    ScientificWorkflowAgent,
)
from agentic_framework_pkg.mcp_server.state_manager import get_chroma_client
from agentic_framework_pkg.core.logger_config import get_logger
from fastmcp import Client as MCPClient

from agentic_framework_pkg.core.chroma_embedding_function import (
    get_chroma_embedding_function,
)

from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)

st.set_page_config(page_title="CSV/TSV SQL Agent", layout="wide")

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://agentic_mcp_server_ch00:8080/mcp")
SHARED_UPLOAD_DIR = "/app/data/uploaded_files"
os.makedirs(SHARED_UPLOAD_DIR, exist_ok=True)

# Initialize ChromaDB client and embedding function
chroma_client = asyncio.run(get_chroma_client())
chroma_embedding_function = get_chroma_embedding_function()

chat_history_collection = chroma_client.get_or_create_collection(
    name="chat_history", embedding_function=chroma_embedding_function
)
file_history_collection = chroma_client.get_or_create_collection(
    name="file_history", embedding_function=chroma_embedding_function
)
notes_collection = chroma_client.get_or_create_collection(
    name="notes", embedding_function=chroma_embedding_function
)

if "chat_history" not in st.session_state:
    # Load chat history from ChromaDB
    history = chat_history_collection.get()
    st.session_state.chat_history = sorted(
        [json.loads(doc) for doc in history["documents"]], key=lambda x: x["timestamp"]
    )

if "agent_instance" not in st.session_state:
    try:
        st.session_state.agent_instance = ScientificWorkflowAgent()
    except ValueError as e:
        st.error(f"Failed to initialize agent: {e}")
        st.session_state.agent_instance = None

st.title("CSV/TSV SQL Agent")


async def call_mcp_tool(tool_name: str, **kwargs):
    async with MCPClient(MCP_SERVER_URL) as client:
        result = await client.call_tool(tool_name, arguments=kwargs)
        return result.content  # Return the raw content


with st.sidebar:
    st.header("Upload CSV/TSV")
    uploaded_files = st.file_uploader(
        "Choose CSV or TSV files", type=["csv", "tsv"], accept_multiple_files=True
    )
    if uploaded_files:
        if len(uploaded_files) > 5:
            st.warning("Please select a maximum of 5 files at a time.")
        else:
            if st.button("Ingest Files"):
                for uploaded_file in uploaded_files:
                    table_name = os.path.splitext(uploaded_file.name)[0]
                    file_path = os.path.join(SHARED_UPLOAD_DIR, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getvalue())

                    result = asyncio.run(
                        call_mcp_tool(
                            "ingest_data", file_path=file_path, table_name=table_name
                        )
                    )
                    if "status" in result and result["status"] == "success":
                        st.success(
                            f"Successfully ingested {uploaded_file.name} as table '{table_name}'."
                        )
                    elif "error" in result:
                        st.error(
                            f"Error ingesting {uploaded_file.name}: {result['error']}"
                        )
                    else:
                        st.write(str(result))

    st.header("File History")
    file_history_result = asyncio.run(call_mcp_tool("list_files"))
    if file_history_result and "files" in file_history_result:
        for file_info in file_history_result["files"]:
            st.write(
                f"- **{file_info['file_name']}** as table `{file_info['table_name']}`"
            )

    st.header("Notes")
    note_text = st.text_area("Save a note")
    if st.button("Save Note"):
        asyncio.run(call_mcp_tool("save_note", note=note_text))
        st.success("Note saved!")

    st.header("Saved Notes")
    notes_result = asyncio.run(call_mcp_tool("list_notes"))
    if notes_result and "notes" in notes_result:
        for note in notes_result["notes"]:
            st.write(f"- {note}")

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your CSV/TSV data"):
    st.session_state.chat_history.append(
        {"role": "user", "content": prompt, "timestamp": time.time()}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        if st.session_state.agent_instance:
            response = asyncio.run(
                st.session_state.agent_instance.arun(
                    prompt, st.session_state.chat_history
                )
            )
            full_response = response.get("output", "")
        message_placeholder.markdown(full_response)
    st.session_state.chat_history.append(
        {"role": "assistant", "content": full_response, "timestamp": time.time()}
    )

    # Save chat history to ChromaDB
    chat_history_collection.add(
        ids=[str(uuid.uuid4()) for _ in range(2)],
        documents=[
            json.dumps(st.session_state.chat_history[-2]),
            json.dumps(st.session_state.chat_history[-1]),
        ],
    )
