import os
import asyncio
from typing import List, Dict, Any, Optional, Union
import json

# Langchain imports
from langchain_openai import (
    ChatOpenAI,
    AzureChatOpenAI,
)  # Example, can be swapped with other LiteLLM compatible models

# Import for langchain 1.x
try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
except ImportError:
    # For langchain 1.2.x+, these are in langchain-classic
    try:
        from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
    except ImportError:
        raise ImportError(
            "Could not import AgentExecutor and create_openai_tools_agent. "
            "Please install langchain-classic: pip install langchain-classic"
        )
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks.base import (
    BaseCallbackHandler,
)  # Import for type hinting callbacks
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    BaseMessage,
    ToolMessage,
)
from .mcp_langchain_tools import (
    get_mcp_query_csv_tool_langchain,
    get_mcp_perform_calculation_tool_langchain,
    get_mcp_store_note_tool_langchain,
    get_mcp_retrieve_notes_tool_langchain,
    get_mcp_query_uniprot_tool_langchain,
    get_mcp_web_search_tool_langchain,
    get_mcp_blastp_biopython_tool_langchain,  # Import Biopython BLASTP tool
    get_mcp_blastn_biopython_tool_langchain,  # Import Biopython BLASTN tool
    get_mcp_search_pubchem_by_query_tool_langchain,  # Import PubChem search tool factory
    get_mcp_search_pubchem_by_name_tool_langchain,  # Import PubChem search tool factory
    get_mcp_get_pubchem_compound_properties_tool_langchain,  # Import PubChem properties tool factory
    get_mcp_list_uploaded_files_tool_langchain,  # Import new tool for listing files
    get_mcp_test_hpc_connection_tool_langchain,  # Import HPC connection test tool
    get_mcp_submit_slurm_job_tool_langchain,  # Import HPC job submission tool
    get_mcp_check_slurm_job_status_tool_langchain,  # Import HPC job status tool
)
from ..logger_config import get_logger  # Use centralized logger

# Configure logging
logger = get_logger(__name__)

LANGCHAIN_LLM_MODEL = os.getenv(
    "LANGCHAIN_LLM_MODEL", "gpt-3.5-turbo"
)  # Or "gpt-4" etc.
# This is a conceptual setup. A real agent would need more robust memory, error handling, etc.


class ScientificWorkflowAgent:
    def __init__(self, mcp_session_id: Optional[str] = None):
        self.mcp_session_id = mcp_session_id  # Crucial for stateful MCP tool calls

        self.llm: Optional[Union[ChatOpenAI, AzureChatOpenAI]] = None
        self.llm_model_name = os.getenv(
            "LANGCHAIN_LLM_MODEL"
        )  # User-specified model or Azure deployment

        # Fetch LLM configuration from environment variables
        internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
        internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
        internal_llm_model = os.getenv("INTERNAL_LLM_MODEL")

        azure_api_base = os.getenv("AZURE_API_BASE", None)
        azure_api_key = os.getenv("AZURE_API_KEY", None)
        azure_api_version = os.getenv("AZURE_API_VERSION", None)

        openai_api_key = os.getenv("OPENAI_API_KEY", None)

        initialized_llm = False

        # Check for internal LLM provider FIRST (highest priority)
        if internal_llm_api_key and internal_llm_base_url and internal_llm_model:
            logger.info(
                f"Using internal LLM provider: {internal_llm_base_url} with model {internal_llm_model}"
            )

            # Reasoning models need higher max_tokens for internal reasoning + response
            max_tokens = (
                4000
                if "o4-mini" in internal_llm_model or "o3-mini" in internal_llm_model
                else 1000
            )

            try:
                self.llm = ChatOpenAI(
                    model=internal_llm_model,
                    api_key=internal_llm_api_key,
                    base_url=internal_llm_base_url,
                    max_tokens=max_tokens,
                )
                logger.info("Internal LLM provider initialized successfully.")
                initialized_llm = True
            except Exception as e:
                logger.error(
                    f"Failed to initialize internal LLM provider: {e}", exc_info=True
                )
                # Don't raise here, allow fallback to cloud providers

        # Try Azure OpenAI if internal LLM not configured or failed
        if (
            not initialized_llm
            and azure_api_base
            and azure_api_key
            and azure_api_version
        ):
            if not self.llm_model_name:
                logger.warning(
                    "Azure OpenAI environment variables (AZURE_API_BASE, AZURE_API_KEY, AZURE_API_VERSION) are set, "
                    "but LANGCHAIN_LLM_MODEL (which should be the Azure deployment name) is missing. Skipping Azure OpenAI."
                )
            else:
                logger.info(
                    f"Attempting to initialize AzureChatOpenAI with deployment: {self.llm_model_name} and API version: {azure_api_version}"
                )
                logger.info(
                    f"Using Azure API base: {azure_api_base} and key len: {len(azure_api_key)}"
                )
                try:
                    self.llm = AzureChatOpenAI(
                        azure_deployment=self.llm_model_name,
                        openai_api_version=azure_api_version,
                        azure_endpoint=azure_api_base,
                        api_key=azure_api_key,
                        # temperature=0, # Removed as o3-mini might not support it
                    )
                    logger.info("AzureChatOpenAI initialized successfully.")
                    initialized_llm = True
                except Exception as e:
                    logger.error(
                        f"Failed to initialize AzureChatOpenAI: {e}", exc_info=True
                    )
                    # Don't raise here, allow fallback to standard OpenAI if configured

        # If Azure not configured or failed, try standard OpenAI
        if not initialized_llm and openai_api_key:
            current_model_to_use = (
                self.llm_model_name if self.llm_model_name else "gpt-3.5-turbo"
            )
            logger.info(
                f"Attempting to initialize ChatOpenAI with model: {current_model_to_use}"
            )
            try:
                self.llm = ChatOpenAI(
                    model=current_model_to_use,  # Use 'model' parameter for ChatOpenAI
                    openai_api_key=openai_api_key,
                    temperature=0,  # Standard OpenAI models generally support temperature
                )
                logger.info("ChatOpenAI initialized successfully.")
                initialized_llm = True
            except Exception as e:
                logger.error(f"Failed to initialize ChatOpenAI: {e}", exc_info=True)
                # Don't raise here yet, final check below

        if not initialized_llm:
            error_msg = (
                "LLM configuration is missing or incomplete. Please set environment variables for either Azure OpenAI "
                "(AZURE_API_BASE, AZURE_API_KEY, AZURE_API_VERSION, and LANGCHAIN_LLM_MODEL for Azure deployment name) "
                "or standard OpenAI (OPENAI_API_KEY, and optionally LANGCHAIN_LLM_MODEL)."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        agent_session_id = (
            self.mcp_session_id
        )  # The agent's session ID for tool fallbacks

        self.tools = [
            get_mcp_query_csv_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_perform_calculation_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_store_note_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_retrieve_notes_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_query_uniprot_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_web_search_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_blastp_biopython_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Use Biopython version
            get_mcp_blastn_biopython_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Use Biopython version
            # get_mcp_search_pubchem_by_query_tool_langchain(mcp_session_id=agent_session_id), # Add PubChem search tool
            get_mcp_search_pubchem_by_name_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add PubChem search tool
            get_mcp_get_pubchem_compound_properties_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add PubChem properties tool
            get_mcp_list_uploaded_files_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add tool to list uploaded files
            get_mcp_test_hpc_connection_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add HPC connection test tool
            get_mcp_submit_slurm_job_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add HPC job submission tool
            get_mcp_check_slurm_job_status_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add HPC job status tool
            # Add more wrapped MCP tools here
        ]

        # Define the prompt for the agent
        # The system message guides the LLM on its role, how to use tools,
        # and specifically how to include the mcp_session_id in tool calls.
        # Construct the example JSON string with properly escaped braces for the prompt template
        example_session_id_for_json_example = (
            self.mcp_session_id or "YOUR_CURRENT_SESSION_ID"
        )
        # This will result in a string like: {{ "note_text": "my important note", "mcp_session_id": "actual_id_or_placeholder" }}
        # which Langchain will render as a literal JSON example for the LLM.
        example_json_str_for_prompt = f'{{{{ "note_text": "my important note", "mcp_session_id": "{example_session_id_for_json_example}" }}}}'

        system_prompt_message = (
            "You are a helpful scientific workflow assistant. "
            "You have access to several tools to help answer user queries and perform tasks. "
            "These tools allow you to perform calculations, manage notes, search the web, query UniProt, "
            "search PubChem for chemical compounds (SearchPubChemByName), retrieve detailed compound properties by CID (GetPubChemCompoundProperties), "
            # "search PubChem for chemical compounds using generic query terms (SearchPubChemQueryInput) if the other PubChem tools fail; "
            "perform protein (PerformProteinBlastSearchBiopython) and nucleotide (PerformNucleotideBlastSearchBiopython) sequence searches using Biopython; "
            "retrieve information from uploaded documents (CSVs, PDFs, DOCX, images, TXT, TEX) once they are processed and have a file_id (QueryProcessedDocumentData), and list previously uploaded and processed files (ListUploadedFiles). "
            "If there are processed files avaiable, you can use the QueryProcessedCSVData tool to query processed files. "
            "When you use a tool that requires a session context (like storing notes or querying user-specific CSV data), "
            "you MUST include the 'mcp_session_id' in the tool's input parameters. "
            "The current MCP session ID is: {mcp_session_id_for_prompt}. "
            f"For example, if you use the 'StoreNoteInSession' tool, your input should be a JSON like: {example_json_str_for_prompt}. "
            "Always provide the `mcp_session_id` when the tool's description or input schema indicates it is needed for session context."
        )

        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt_message),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(
                    variable_name="agent_scratchpad"
                ),  # For agent's intermediate steps
            ]
        )

        self.agent = create_openai_tools_agent(self.llm, self.tools, prompt_template)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,  # For debugging
            handle_parsing_errors=True,  # Gracefully handle LLM output parsing errors
        )

    async def arun(
        self,
        user_input: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
    ) -> Dict[str, Any]:
        """
        Runs the agent with the given user input and optional chat history.
        The mcp_session_id is passed implicitly via the agent's initialization or needs to be part of the input.
        """
        current_chat_history: List[BaseMessage] = []
        if chat_history:
            for msg in chat_history:
                if msg.get("role") == "user":
                    current_chat_history.append(
                        HumanMessage(content=msg.get("content", ""))
                    )
                elif msg.get("role") == "assistant":
                    current_chat_history.append(
                        AIMessage(content=msg.get("content", ""))
                    )

        # The `mcp_session_id_for_prompt` is used to format the system message.
        # The actual `mcp_session_id` is expected by the tools' Pydantic models.
        # The system prompt instructs the LLM to include `mcp_session_id: self.mcp_session_id`
        # in the JSON it generates for tool calls.
        agent_input_dict = {
            "input": user_input,
            "chat_history": current_chat_history,
            "mcp_session_id_for_prompt": self.mcp_session_id
            or "N/A (no active session provided to agent)",
        }

        # If tools expect mcp_session_id directly in their input dict (as per Pydantic models),
        # the LLM needs to be prompted to include it. The system message above tries to do this.
        # The `MCPToolWrapper` will then extract it if present in `tool_input`.

        logger.info(
            f"Running Langchain agent for session {self.mcp_session_id} with input: {user_input}"
        )
        try:
            # Pass callbacks to agent_executor.ainvoke
            response = await self.agent_executor.ainvoke(
                agent_input_dict,
                config={
                    "callbacks": callbacks
                },  # This is the standard way to pass callbacks
            )
            return response
        except Exception as e:
            logger.error(
                f"Error running Langchain agent for session {self.mcp_session_id}: {e}",
                exc_info=True,
            )
            # If you have a callback handler for errors, it might have already logged this.
            if callbacks:
                for cb in callbacks:
                    if hasattr(cb, "on_chain_error"):
                        cb.on_chain_error(
                            e
                        )  # Manually call if not automatically handled by executor for all errors
            return {"output": f"An error occurred: {e}"}

        # # Note: Old-style without callback
        # try:
        #     response = await self.agent_executor.ainvoke(agent_input_dict)
        #     return response
        # except Exception as e:
        #     logger.error(f"Error running Langchain agent for session {self.mcp_session_id}: {e}", exc_info=True)
        #     return {"output": f"An error occurred: {e}"}


# Example usage (conceptual, would be called from Streamlit or other interface)
async def run_example_langchain_workflow(query: str, session_id: str):
    logger.info(
        f"Starting Langchain workflow for query: '{query}' with session_id: {session_id}"
    )
    agent_instance = ScientificWorkflowAgent(mcp_session_id=session_id)

    # Example: Store a note first, then retrieve it.
    # This requires the LLM to understand the sequence and use the tools correctly.
    # For a direct test, you might invoke tools sequentially.

    # For a conversational agent, you'd maintain chat_history.
    # Here's a single invocation:
    response = await agent_instance.arun(query)
    logger.info(f"Langchain agent response: {response.get('output')}")
    return response.get("output", "No output from agent.")


if __name__ == "__main__":
    # This is a simple test, requires MCP server to be running.
    # And OPENAI_API_KEY to be set.
    # Example:
    # python -m agentic_framework_pkg.scientific_workflow.langchain_agent_setup
    async def test_run():
        test_session_id = "langchain_test_session_001"
        # First, ensure this session exists on MCP server (e.g. by calling a simple tool like get_current_datetime)
        # For a real test, you'd use the Streamlit app to upload a CSV first to get a file_id.
        # query_for_agent = "Store this note for me: 'Langchain test successful'. Then, retrieve all my notes."
        # query_for_agent = "What is 100 divided by 5, then add 3 to the result?"
        # To test CSV RAG, you'd need a file_id from a registered CSV.
        # query_for_agent = '{"user_query": "What is the average price?", "file_id": "your_file_id_here"}' # This is tool input, not agent query
        query_for_agent = "I have a CSV file with file_id 'some-fake-file-id-for-test'. Can you tell me what is in it regarding 'sales'?"
        # The agent should then use the QueryProcessedCSVData tool.

        output = await run_example_langchain_workflow(query_for_agent, test_session_id)
        print("Final Agent Output:", output)

    # asyncio.run(test_run()) # Commented out to prevent auto-run without setup
