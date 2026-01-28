import streamlit as st
import os
import uuid
import json  # For displaying dict results
import asyncio
from typing import List, Dict, Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Adjust the import path based on your project structure if this file is moved
from agentic_framework_pkg.scientific_workflow.langchain_agent import (
    ScientificWorkflowAgent,
)
from agentic_framework_pkg.logger_config import get_logger

try:
    from fastmcp import Client as MCPClient

    # Langchain callback imports
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.agents import AgentAction, AgentFinish
    from langchain_core.outputs import LLMResult
except ImportError:
    st.error("FastMCP client library not found. Please ensure 'fastmcp' is installed.")
    st.stop()

logger = get_logger(__name__)

# --- Configuration ---
st.set_page_config(page_title="Agentic Framework UI", layout="wide")

# MCP Server URL - read from environment with fallback to localhost
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
logger.info(f"Streamlit App: Effective MCP_SERVER_URL is {MCP_SERVER_URL}")

# Determine Shared Upload Directory:
# Defaults to "./data/uploaded_files" for consistency with chapter-00
SHARED_UPLOAD_DIR = os.getenv("SHARED_UPLOAD_DIR", "./data/uploaded_files")
logger.info(f"Streamlit App: Effective SHARED_UPLOAD_DIR is {SHARED_UPLOAD_DIR}")
os.makedirs(SHARED_UPLOAD_DIR, exist_ok=True)

# --- Session State Initialization ---
if "mcp_session_id" not in st.session_state:
    # Debugging: Check environment variables are loaded
    logger.info(f"Checking env vars in Streamlit app:")
    logger.info(f"AZURE_API_KEY: {'Set' if os.getenv('AZURE_API_KEY') else 'Not Set'}")
    logger.info(
        f"AZURE_API_BASE: {'Set' if os.getenv('AZURE_API_BASE') else 'Not Set'}"
    )
    logger.info(
        f"AZURE_API_VERSION: {'Set' if os.getenv('AZURE_API_VERSION') else 'Not Set'}"
    )
    logger.info(
        f"LANGCHAIN_LLM_MODEL: {'Set' if os.getenv('LANGCHAIN_LLM_MODEL') else 'Not Set'}"
    )
    logger.info(
        f"OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not Set'}"
    )
    logger.info(f"MCP_SERVER_URL (used by Streamlit): {MCP_SERVER_URL}")
    st.session_state.mcp_session_id = str(uuid.uuid4())
    logger.info(
        f"New Streamlit session started. MCP Session ID: {st.session_state.mcp_session_id}"
    )

if "chat_history" not in st.session_state:
    st.session_state.chat_history: List[
        Dict[str, str]
    ] = []  # Stores {"role": "user/assistant", "content": "..."}

if "agent_thoughts" not in st.session_state:
    st.session_state.agent_thoughts: List[str] = []

if "agent_instance" not in st.session_state:
    try:
        st.session_state.agent_instance = ScientificWorkflowAgent(
            mcp_session_id=st.session_state.mcp_session_id
        )
        logger.info(
            f"ScientificWorkflowAgent initialized for session {st.session_state.mcp_session_id}"
        )
    except ValueError as e:
        st.error(f"Failed to initialize agent: {e}")
        logger.error(
            f"Agent initialization error for session {st.session_state.mcp_session_id}: {e}",
            exc_info=True,
        )
        st.session_state.agent_instance = None
    except Exception as e:
        st.error(f"An unexpected error occurred during agent initialization: {e}")
        logger.error(
            f"Unexpected agent initialization error for session {st.session_state.mcp_session_id}: {e}",
            exc_info=True,
        )
        st.session_state.agent_instance = None


# --- Custom Langchain Callback Handler for Streamlit ---
class StreamlitThoughtsCallbackHandler(BaseCallbackHandler):
    """A callback handler that writes agent thoughts to Streamlit session state."""

    def _ensure_agent_thoughts_initialized(self):
        if "agent_thoughts" not in st.session_state:
            st.session_state.agent_thoughts = []

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        self._ensure_agent_thoughts_initialized()
        st.session_state.agent_thoughts.append("🧠 LLM thinking...")

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        thought = f"🛠️ Action: {action.tool}\n"
        thought += f"   Input: {action.tool_input}\n"
        # thought += f"   Log: {action.log.strip()}" # log often contains the thought process
        # Extracting the thought process if it's in action.log
        if action.log:
            log_lines = action.log.split("\n")
            thought_lines = [
                line
                for line in log_lines
                if not line.startswith("Invoking") and not line.startswith("Action:")
            ]
            if thought_lines:
                self._ensure_agent_thoughts_initialized()
                # Evaluate the expression part separately to avoid f-string parsing issues
                thought_content = "\n".join(thought_lines).strip()
                st.session_state.agent_thoughts.append(
                    f"""🤔 Thought:\n```\n{thought_content}\n```"""
                )
        self._ensure_agent_thoughts_initialized()
        st.session_state.agent_thoughts.append(thought)

    def on_tool_end(self, output: str, name: str, **kwargs: Any) -> None:
        self._ensure_agent_thoughts_initialized()
        # Evaluate the expression part separately
        tool_output_content = output[:500]  # Truncate long outputs
        st.session_state.agent_thoughts.append(
            f"""✅ Tool Output ({name}):\n```\n{tool_output_content}\n```\n---"""
        )

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        self._ensure_agent_thoughts_initialized()
        # Evaluate the expression part separately
        final_answer_content = finish.return_values.get("output", "")
        st.session_state.agent_thoughts.append(
            f"""🏁 Agent Finished.\nFinal Answer:\n```\n{final_answer_content}\n```"""
        )

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        self._ensure_agent_thoughts_initialized()
        st.session_state.agent_thoughts.append(f"❌ Error: {error}")

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self._ensure_agent_thoughts_initialized()
        st.session_state.agent_thoughts.append(f"❌ Tool Error: {error}")


# --- UI Rendering ---
st.title("🔬 Agentic Scientific Workflow Assistant")
st.caption(
    f"MCP Session ID: {st.session_state.mcp_session_id} | Server: {MCP_SERVER_URL}"
)

# Main layout (now a single column as thoughts are in sidebar)
# chat_col, thoughts_col = st.columns([4, 1]) # Removed columns

with st.container():  # Use a container for the main chat area
    # Display chat messages
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# User input
user_query = st.chat_input("Ask the agent...")


async def get_agent_response(
    query: str,
    agent: ScientificWorkflowAgent,
    history: List[Dict[str, str]],
    callbacks: List[BaseCallbackHandler],
) -> str:
    """Helper async function to run the agent."""
    if agent is None:
        return "Agent not initialized. Please check server logs."
    try:
        # Assuming agent.arun is modified to accept and use callbacks
        response_dict = await agent.arun(
            user_input=query, chat_history=history, callbacks=callbacks
        )
        return response_dict.get("output", "Agent did not provide a standard output.")
    except Exception as e:
        logger.error(
            f"Error during agent execution for session {st.session_state.mcp_session_id}: {e}",
            exc_info=True,
        )
        return f"An error occurred while processing your request: {e}"


if user_query and st.session_state.agent_instance:
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Clear previous thoughts and prepare callback
    st.session_state.agent_thoughts = []
    # thoughts_container.markdown("_Agent is starting..._") # Initial message - now handled in sidebar
    streamlit_callback = StreamlitThoughtsCallbackHandler()

    # Get agent response
    with st.spinner("Agent is thinking... (see thoughts in the sidebar)"):
        try:
            agent_response_content = asyncio.run(
                get_agent_response(
                    user_query,
                    st.session_state.agent_instance,
                    st.session_state.chat_history[:-1],
                    [streamlit_callback],
                )
            )
        except RuntimeError as e:
            if "cannot be called when another loop is running" in str(e):
                logger.warning("Asyncio loop conflict detected.")
                agent_response_content = "Error: Could not run asynchronous agent due to event loop conflict."
            else:
                raise e

    # Add agent response to chat history
    st.session_state.chat_history.append(
        {"role": "assistant", "content": agent_response_content}
    )
    with st.chat_message("assistant"):
        st.markdown(agent_response_content)

elif user_query and not st.session_state.agent_instance:
    st.error(
        "Agent is not available. Please check the application logs or try refreshing."
    )


# --- Sidebar for advanced options or info (optional) ---
with st.sidebar:
    st.header("About")
    st.markdown(
        "This is a Streamlit UI for the Agentic Framework. "
        "It interacts with an MCP server and a Langchain-based scientific workflow agent."
    )
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.session_state.agent_thoughts = []  # Also clear thoughts
        logger.info(
            f"Chat history cleared for session {st.session_state.mcp_session_id}"
        )
        st.rerun()

    # # Agent Thoughts section moved to sidebar
    # with st.expander("Agent Thoughts 🧠", expanded=True):
    #     # This placeholder will be updated by the callback handler
    #     thoughts_container = st.empty()
    #     if st.session_state.agent_thoughts:
    #         thoughts_container.markdown("\n\n".join(st.session_state.agent_thoughts), unsafe_allow_html=True)
    #     thoughts_container.markdown("_Agent thoughts will appear here..._") # Initial message/placeholder

    st.header("Environment Info (for debugging)")
    st.text(f"Effective MCP Server URL: {MCP_SERVER_URL}")
    langchain_llm = os.getenv("LANGCHAIN_LLM_MODEL", "gpt-3.5-turbo (default)")
    st.text(f"Langchain LLM: {langchain_llm}")

    # Note: To test document uploads, you would add st.file_uploader and then
    # call the 'register_uploaded_csv' MCP tool. The file_id returned
    # would then be used in queries to 'query_csv_data' via the agent.
    # This example focuses on the chat interaction with the pre-configured agent.

    # --- document RAG Tool Testing Section ---
    with st.expander("document RAG Tool Test"):
        supported_types = [
            "csv",
            "xlsx",
            "docx",
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "gif",
            "webp",
            "txt",
            "tex",
        ]
        uploaded_csv_file = st.file_uploader(
            f"Upload Document for RAG ({', '.join(supported_types)})",
            type=supported_types,
            key="doc_uploader_main_app",
        )

        if uploaded_csv_file is not None:
            st.write(
                f"Uploaded: {uploaded_csv_file.name} (Size: {uploaded_csv_file.size} bytes)"
            )
            if st.button(
                "Process Uploaded document for RAG", key="process_csv_button_main_app"
            ):
                original_filename = uploaded_csv_file.name
                safe_chars = set(
                    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
                )
                sanitized_base_filename = "".join(
                    c if c in safe_chars else "_"
                    for c in os.path.splitext(original_filename)[0]
                )  # Fixed splitext
                file_extension = os.path.splitext(original_filename)[1]
                unique_filename_part = str(uuid.uuid4())[:8]
                final_sanitized_filename = f"{sanitized_base_filename}_{st.session_state.mcp_session_id[:8]}_{unique_filename_part}{file_extension}"

                secure_shared_file_path = os.path.join(
                    SHARED_UPLOAD_DIR, final_sanitized_filename
                )

                try:
                    with open(secure_shared_file_path, "wb") as f:
                        f.write(uploaded_csv_file.getvalue())
                    st.info(
                        f"File saved to shared volume at internal path: {secure_shared_file_path} (original: {original_filename})"
                    )

                    async def register_csv_async_rag():
                        try:
                            # Instantiate MCPClient without session_id in constructor
                            async with MCPClient(MCP_SERVER_URL) as client:
                                registration_params = {
                                    "file_path_on_server": secure_shared_file_path,
                                    "original_filename": original_filename,
                                    # "mcp_session_id" is now handled by the client's context
                                    "mcp_session_id": st.session_state.mcp_session_id,
                                }
                                st.info(
                                    f"Calling 'process_uploaded_file' with params: {registration_params}"
                                )
                                logger.info(
                                    f"Using client {client}: Calling 'process_uploaded_file' with params: {registration_params} for session {st.session_state.mcp_session_id}"
                                )
                                # Use a spinner to indicate processing
                                with st.spinner(
                                    "Processing document on server... This may take a while for large files or many embeddings."
                                ):
                                    result = await client.call_tool(
                                        "process_uploaded_file", registration_params
                                    )

                                # Process the result, expecting a list with a TextContent object containing JSON
                                if isinstance(result, list) and len(result) > 0:
                                    first_content_item = result[0]
                                    if hasattr(
                                        first_content_item, "text"
                                    ) and isinstance(first_content_item.text, str):
                                        try:
                                            parsed_data = json.loads(
                                                first_content_item.text
                                            )
                                            st.subheader(
                                                "document Registration Result (Parsed):"
                                            )
                                            st.json(
                                                parsed_data
                                            )  # Display the parsed JSON

                                            if (
                                                isinstance(parsed_data, dict)
                                                and "file_id" in parsed_data
                                            ):
                                                st.session_state.current_rag_file_id = (
                                                    parsed_data["file_id"]
                                                )
                                                st.success(
                                                    f"document '{original_filename}' registered with file_id: {parsed_data['file_id']}"
                                                )
                                            elif (
                                                isinstance(parsed_data, dict)
                                                and "error" in parsed_data
                                            ):
                                                st.error(
                                                    f"document Registration failed: {parsed_data['error']}"
                                                )
                                            else:
                                                st.warning(
                                                    f"Parsed JSON from tool response does not contain 'file_id' or 'error': {parsed_data}"
                                                )
                                        except json.JSONDecodeError:
                                            st.error(
                                                f"Failed to parse JSON from tool response text: {first_content_item.text}"
                                            )
                                            st.subheader(
                                                "document Registration Result (Raw):"
                                            )
                                            st.json(result)  # Show raw if parsing fails
                                    else:
                                        st.error(
                                            f"Tool response content is not as expected (e.g., not TextContent or missing 'text' attribute): {result}"
                                        )
                                        st.subheader(
                                            "document Registration Result (Raw):"
                                        )
                                        st.json(result)
                                else:
                                    st.error(
                                        f"Failed to get file_id from registration or unexpected response structure (empty list or not a list): {result}"
                                    )
                                    st.subheader("document Registration Result (Raw):")
                                    st.json(result)
                        except Exception as e:
                            st.error(f"Error during 'process_uploaded_file' call: {e}")
                            logger.error(
                                "Error registering document via MCP", exc_info=True
                            )

                    asyncio.run(register_csv_async_rag())

                except Exception as e:
                    st.error(f"Error saving uploaded file to shared volume: {e}")
                    logger.error("Error saving uploaded file", exc_info=True)

        st.markdown(
            "Once a document is processed, you can ask the agent to query it using its `file_id`."
        )
        st.text_input(
            "Current RAG File ID (if processed)",
            value=st.session_state.get("current_rag_file_id", "N/A"),
            disabled=True,
            key="current_rag_file_id_display",
        )

    with st.expander("List Uploaded Files (Direct Tool Call)"):
        if st.button(
            "Show Uploaded Files for this Session", key="list_files_button_main_app"
        ):

            async def list_files_async():
                try:
                    async with MCPClient(MCP_SERVER_URL) as client:
                        tool_params = {
                            "mcp_session_id": st.session_state.mcp_session_id
                        }
                        st.info(
                            f"Calling 'list_uploaded_files' with params: {tool_params}"
                        )
                        with st.spinner("Fetching list of uploaded files..."):
                            result = await client.call_tool(
                                "list_uploaded_files", tool_params
                            )

                        if isinstance(result, list) and len(result) > 0:
                            first_content_item = result[0]
                            if hasattr(first_content_item, "text") and isinstance(
                                first_content_item.text, str
                            ):
                                try:
                                    parsed_data = json.loads(first_content_item.text)
                                    st.subheader("Uploaded Files:")
                                    if parsed_data.get("uploaded_files"):
                                        for f_info in parsed_data["uploaded_files"]:
                                            st.markdown(
                                                f"- **Filename:** {f_info.get('original_filename', 'N/A')}\n  - **File ID:** `{f_info.get('file_id', 'N/A')}`"
                                            )
                                    else:
                                        st.markdown(
                                            parsed_data.get(
                                                "message",
                                                "No files found or message not provided.",
                                            )
                                        )
                                except json.JSONDecodeError:
                                    st.error(
                                        f"Failed to parse JSON from 'list_uploaded_files' tool response: {first_content_item.text}"
                                    )
                                    st.json(result)  # Show raw if parsing fails
                            else:
                                st.error(
                                    f"'list_uploaded_files' tool response content is not as expected: {result}"
                                )
                                st.json(result)
                        else:
                            st.error(
                                f"Unexpected response structure from 'list_uploaded_files': {result}"
                            )
                            st.json(result)
                except Exception as e:
                    st.error(f"Error calling 'list_uploaded_files': {e}")
                    logger.error("Error listing uploaded files via MCP", exc_info=True)

            asyncio.run(list_files_async())

logger.debug(
    f"Streamlit app script execution finished for session {st.session_state.mcp_session_id}."
)
