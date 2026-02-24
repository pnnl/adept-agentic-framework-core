import os
import asyncio
from typing import List, Dict, Any, Optional, Union, TypedDict, Annotated, Sequence
import operator
import json

# Langchain imports
# Note: Chapter 03 uses LangGraph's create_react_agent instead of legacy AgentExecutor
# from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.callbacks.base import (
    BaseCallbackHandler,
    AsyncCallbackHandler,
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
    get_mcp_web_search_api_tool_langchain,  # Preferred web search tool using API service
    get_mcp_web_search_scraping_tool_langchain,  # Backup web search tool using scraping
    get_mcp_blastp_biopython_tool_langchain,  # Import Biopython BLASTP tool
    get_mcp_blastn_biopython_tool_langchain,  # Import Biopython BLASTN tool
    get_mcp_search_pubchem_by_query_tool_langchain,  # Import PubChem search tool factory
    get_mcp_search_pubchem_by_name_tool_langchain,  # Import PubChem search tool factory
    get_mcp_get_pubchem_compound_properties_tool_langchain,  # Import PubChem properties tool factory
    get_mcp_list_uploaded_files_tool_langchain,  # Import new tool for listing files
    get_mcp_alphafold_prediction_tool_langchain,  # Import AlphaFold prediction tool
    get_mcp_query_stored_alphafold_tool_langchain,  # Import AlphaFold RAG query tool
    get_mcp_run_nextflow_blast_tool_langchain,  # Import HPC Nextflow BLAST tool
    get_mcp_run_video_transcription_tool_langchain,  # Import HPC Video Transcription tool
    get_mcp_execute_code_tool_langchain,  # Import Sandbox Code Execution tool
    get_mcp_gitxray_scan_tool_langchain,  # Import HPC GitXRay Scan tool
    get_mcp_test_hpc_connection_tool_langchain,  # Import HPC SSH connection test tool
    get_mcp_submit_slurm_job_tool_langchain,  # Import HPC Slurm job submission tool
    get_mcp_check_slurm_job_status_tool_langchain,  # Import HPC Slurm job status tool
    get_mcp_create_multi_agent_session_tool_langchain,  # Multi-agent tool
    get_mcp_generate_plan_for_multi_agent_task_tool_langchain,  # Multi-agent tool
    get_mcp_execute_approved_plan_tool_langchain,  # Multi-agent tool
    get_mcp_update_pending_plan_tool_langchain,  # Multi-agent tool
    get_mcp_terminate_multi_agent_session_tool_langchain,  # Multi-agent tool
    get_mcp_list_active_multi_agent_sessions_tool_langchain,  # Multi-agent tool
)

# LangGraph imports
from langgraph.prebuilt import create_react_agent  # Use create_react_agent
# ToolMessage is still useful for understanding message types if needed, but not directly for graph construction here
# TypedDict, Annotated, Sequence, operator might be removed if AgentState class is removed/simplified

from ..logger_config import get_logger  # Use centralized logger
from ..core.llm_agnostic_layer import LLMAgnosticClient  # Import the agnostic client

# Configure logging
logger = get_logger(__name__)
LANGCHAIN_LLM_MODEL = os.getenv(
    "LANGCHAIN_LLM_MODEL", "gpt-3.5-turbo"
)  # Or "gpt-4" etc.


# Define the state for LangGraph
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # If you need to pass other specific data through the graph, add it here.
    # For example: mcp_session_id if it needs to be explicitly in the state
    # mcp_session_id: Optional[str] # create_react_agent handles state internally; mcp_session_id is in prompt and tool wrappers
    # The default AgentState for create_react_agent includes 'is_last_step' and 'remaining_steps'
    # We can let create_react_agent use its default state by not passing state_schema,
    # or align this definition if we choose to pass it. For simplicity, let's remove this custom AgentState for now.


# This is a conceptual setup. A real agent would need more robust memory, error handling, etc.


class ScientificWorkflowAgent:
    def __init__(self, mcp_session_id: Optional[str] = None):
        self.mcp_session_id = mcp_session_id  # Crucial for stateful MCP tool calls
        self.llm_agnostic_client = LLMAgnosticClient()

        # Use LLMAgnosticClient to get the Langchain-compatible LLM instance
        # NOTE: Internal LLM support is handled automatically in get_langchain_chat_model()
        # If INTERNAL_LLM_API_KEY, INTERNAL_LLM_BASE_URL, and INTERNAL_LLM_MODEL are set,
        # the internal LLM will be used with highest priority over cloud providers.
        try:
            self.llm = self.llm_agnostic_client.get_langchain_chat_model(
                llm_purpose="agent_main",  # Define a purpose for the agent's main LLM
                model_name=os.getenv(
                    "LANGCHAIN_LLM_MODEL"
                ),  # Agent uses this env var for its model
                # temperature=0, # Agent desires deterministic output. LLMAgnosticClient will handle if unsupported.
            )
            logger.info(
                f"ScientificWorkflowAgent's LLM initialized via LLMAgnosticClient: {type(self.llm).__name__}"
            )
        except ValueError as e:
            logger.error(
                f"Failed to initialize LLM for ScientificWorkflowAgent: {e}",
                exc_info=True,
            )
            # Depending on desired behavior, either raise e or set self.llm to None and handle downstream
            raise  # Re-raise for now, as agent cannot function without an LLM

        agent_session_id = (
            self.mcp_session_id
        )  # The agent's session ID for tool fallbacks

        self.tools = [
            get_mcp_query_csv_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_perform_calculation_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_store_note_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_retrieve_notes_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_query_uniprot_tool_langchain(mcp_session_id=agent_session_id),
            get_mcp_web_search_api_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Preferred web search
            get_mcp_web_search_scraping_tool_langchain(mcp_session_id=agent_session_id),
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
            get_mcp_alphafold_prediction_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add AlphaFold tool
            get_mcp_query_stored_alphafold_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add AlphaFold RAG query tool
            get_mcp_run_nextflow_blast_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add HPC Nextflow BLAST tool
            get_mcp_run_video_transcription_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add HPC Video Transcription tool
            get_mcp_execute_code_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add Sandbox Code Execution tool
            get_mcp_gitxray_scan_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add HPC GitXRay Scan tool
            get_mcp_test_hpc_connection_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add HPC SSH connection test tool
            get_mcp_submit_slurm_job_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add HPC Slurm job submission tool
            get_mcp_check_slurm_job_status_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Add HPC Slurm job status tool
            get_mcp_create_multi_agent_session_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Multi-agent tool
            get_mcp_generate_plan_for_multi_agent_task_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Multi-agent tool
            get_mcp_execute_approved_plan_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Multi-agent tool
            get_mcp_update_pending_plan_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Multi-agent tool
            get_mcp_terminate_multi_agent_session_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Multi-agent tool
            get_mcp_list_active_multi_agent_sessions_tool_langchain(
                mcp_session_id=agent_session_id
            ),  # Multi-agent tool
            # Add more wrapped MCP tools here
        ]

        # Define the prompt for the agent
        # The system message guides the LLM on its role, how to use tools,
        # and specifically how to include the mcp_session_id in tool calls.
        # Construct the example JSON string with properly escaped braces for the prompt template
        # This will result in a string like: {{ "note_text": "my important note", "mcp_session_id": "actual_id_or_placeholder" }}
        # which Langchain will render as a literal JSON example for the LLM.
        note_session_id_for_prompt = self.mcp_session_id or "YOUR_CURRENT_SESSION_ID"
        self.example_json_str_for_prompt = f'{{{{ "note_text": "my important note", "mcp_session_id": "{note_session_id_for_prompt}" }}}}'

        self.system_prompt_template_str = (
            "You are a helpful scientific workflow assistant. "
            "You have access to several tools to help answer user queries and perform tasks. "  # Ensure this list is up-to-date
            "These tools allow you to perform calculations, manage notes, "
            "perform a web search using a robust API (use PerformWebSearchAPI for this) or by scraping a website (use PerformWebSearchScraping as a fallback), query UniProt (QueryUniProt), "
            "search PubChem for chemical compounds (SearchPubChemByName), retrieve detailed compound properties by CID (GetPubChemCompoundProperties), "
            "fetch protein structure predictions from AlphaFold EBI (GetAlphaFoldPrediction), "
            "search your local cache of previously fetched AlphaFold predictions (SearchStoredAlphaFoldPredictions), "
            "perform protein (PerformProteinBlastSearchBiopython) and nucleotide (PerformNucleotideBlastSearchBiopython) sequence searches using Biopython (NCBI web service); "  # semicolon added
            "run a BLAST search pipeline on a dedicated HPC server (RunNextflowBlastPipelineHPC) for potentially larger or custom database searches; "  # semicolon added
            "and transcribe and summarize videos (RunVideoTranscriptionPipelineHPC) using a video URL or an absolute server-accessible file path (e.g., /app/data/uploaded_files/my_video.mp4). This tool also indexes the transcript, making it queryable via its returned file_id using QueryProcessedDocumentData. "
            "retrieve information from uploaded documents (CSVs, PDFs, DOCX, images, TXT, TEX) once they are processed and have a file_id (QueryProcessedDocumentData), list previously uploaded and processed files (ListUploadedFiles), "
            "execute arbitrary code in a secure sandbox (ExecuteCode) for languages like python, javascript, or shell. For Python, you can generate plots by setting the 'generate_plot' parameter to True. This can create static images (e.g., with matplotlib) or interactive HTML plots (e.g., with plotly). For Python plotting, ensure you explicitly create a figure object (e.g., 'fig, ax = plt.subplots()') and avoid calling 'plt.show()'. The figure object should be the last expression in your code block for it to be captured. Streamlit renders these figures using 'st.pyplot(fig)'. You can also specify a custom Docker image with the 'sandbox_image' parameter; "
            "scan public GitHub repositories for secrets (ScanGithubRepositoryForSecrets); "
            "and connect to remote HPC clusters via SSH: test SSH connections (TestHPCConnection), submit Slurm batch jobs (SubmitSlurmJob), and check job status (CheckSlurmJobStatus). These HPC SSH tools connect to REMOTE clusters via SSH, not the local Nextflow container. "
            "You can also create and manage a team of expert AI agents (multi-agent team) for complex tasks. This is a complete lifecycle process. You can list all active sessions using 'ListActiveMultiAgentSessions' to see which teams are available. "
            "First, use 'CreateMultiAgentSession' to build a team with specific roles (e.g., chemist, data scientist). You will get a session ID back. "
            "Second, use 'GeneratePlanForMultiAgentTask' with that session ID to create a plan for the team's supervisor. When this tool returns a plan, you MUST display the entire plan to the user and ask for their approval before proceeding. "
            "Third, if the user provides an edited version of the plan, you must use the 'UpdatePendingPlan' tool to save the changes. If the user simply approves the plan (e.g., by saying 'yes' or 'looks good'), you MUST NOT generate the plan again. Instead, you must immediately call the 'ExecuteApprovedPlan' tool to start the execution. "
            "Fourth, once the user approves the plan (either the original or the edited version), you must call 'ExecuteApprovedPlan' with the same session ID to run the plan and get the final report. "
            "Finally, after the task is complete and the user is satisfied, you should use 'TerminateMultiAgentSession' to clean up the session resources. "
            "If there are processed files avaiable, you can use the QueryProcessedCSVData tool to query processed files. "
            "When you use a tool that requires a session context (like storing notes or querying user-specific CSV data), "
            "you MUST include the 'mcp_session_id' in the tool's input parameters. "
            "The current MCP session ID for your operations is: {mcp_session_id_for_prompt}. "
            f"For example, if you use the 'StoreNoteInSession' tool, your input should be a JSON like: {self.example_json_str_for_prompt}. "
            "Always provide the `mcp_session_id` when the tool's description or input schema indicates it is needed for session context."
        )

        # Format the system prompt string with the actual session ID or placeholder
        self.formatted_system_prompt = self.system_prompt_template_str.format(
            mcp_session_id_for_prompt=self.mcp_session_id
            or "N/A (no active session provided to agent)",
            # example_json_str_for_prompt is already formatted if needed here, but it's part of the template string
        )

        # LangGraph setup using create_react_agent
        # The `create_react_agent` function handles the creation of the agent,
        # tool node, and the graph logic (looping between agent and tools).
        self.graph = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=SystemMessage(
                content=self.formatted_system_prompt
            ),  # Pass the system prompt as a SystemMessage
            # state_schema=AgentState, # Can be omitted to use create_react_agent's default AgentState
            # checkpointer=None, # Add if you need persistence
            debug=True,  # Enable LangGraph debug logging
        )
        logger.info("LangGraph workflow compiled using create_react_agent.")

    # Manual graph node methods (_call_model_node_lg, _call_tool_node_lg, _should_continue_node_lg) are no longer needed.

    # --- Main Agent Execution Method ---
    async def arun(
        self,
        user_input: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        callbacks: Optional[
            List[Union[BaseCallbackHandler, AsyncCallbackHandler]]
        ] = None,
        recursion_limit: int = 25,
    ) -> Dict[str, Any]:
        """
        Runs the agent with the given user input and optional chat history.
        Uses the LangGraph engine compiled by create_react_agent.

        Args:
            recursion_limit (int): The maximum number of steps the agent can take.
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

        # `create_react_agent` graph expects input with a "messages" key.
        # It manages its own state, including 'remaining_steps'.
        initial_messages_for_graph = current_chat_history + [
            HumanMessage(content=user_input)
        ]
        graph_input = {"messages": initial_messages_for_graph}

        # Pass callbacks and recursion limit to the graph invocation
        langchain_config = {"callbacks": callbacks, "recursion_limit": recursion_limit}

        logger.info(
            f"Running create_react_agent graph for session {self.mcp_session_id} with input: {user_input}"
        )
        try:
            # `create_react_agent` returns the final state of the graph.
            final_state_result = await self.graph.ainvoke(
                graph_input, config=langchain_config
            )

            if final_state_result and final_state_result.get("messages"):
                last_message_in_graph = final_state_result["messages"][-1]
                output_content = last_message_in_graph.content

                # Check the last tool message for plot URLs, regardless of which tool was called
                last_tool_message = next(
                    (
                        msg
                        for msg in reversed(final_state_result.get("messages", []))
                        if isinstance(msg, ToolMessage)
                    ),
                    None,
                )
                if last_tool_message:
                    try:
                        tool_output = json.loads(last_tool_message.content)
                        if isinstance(tool_output, dict) and tool_output.get("plots"):
                            plot_urls = [
                                p.get("plot_url")
                                for p in tool_output.get("plots", [])
                                if p.get("plot_url")
                            ]
                            if plot_urls:
                                markdown_images = "\n".join(
                                    [f"![Generated Plot]({url})" for url in plot_urls]
                                )
                                output_content = (
                                    f"{markdown_images}\n\n{output_content}"
                                )
                                logger.info(
                                    f"Agent formatted plot URLs from tool '{last_tool_message.name}' into Markdown."
                                )
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(
                            f"Could not parse tool output from '{last_tool_message.name}' as JSON: {last_tool_message.content}"
                        )

                # If the last message is an AIMessage with tool_calls, it might mean an error or unexpected end.
                if (
                    isinstance(last_message_in_graph, AIMessage)
                    and last_message_in_graph.tool_calls
                ):
                    logger.warning(
                        f"LangGraph (create_react_agent) ended with AIMessage with tool_calls: {last_message_in_graph.tool_calls}"
                    )
                    output_content = f"Agent decided to call tools but ended: {last_message_in_graph.content} (Tools: {last_message_in_graph.tool_calls})"
                return {
                    "output": output_content,
                    "full_graph_state": final_state_result,
                }
            else:
                logger.error(
                    f"LangGraph (create_react_agent) execution for session {self.mcp_session_id} resulted in empty or malformed state."
                )
                return {
                    "output": "LangGraph execution finished with no clear output.",
                    "full_graph_state": final_state_result,
                }
        except Exception as e:
            logger.error(
                f"Error running LangGraph (create_react_agent) for session {self.mcp_session_id}: {e}",
                exc_info=True,
            )
            # Propagate error to callbacks if any
            if callbacks:
                for cb_item in callbacks:
                    if cb_item and hasattr(cb_item, "on_chain_error"):
                        try:
                            await cb_item.on_chain_error(
                                e
                            ) if asyncio.iscoroutinefunction(
                                cb_item.on_chain_error
                            ) else cb_item.on_chain_error(e)
                        except Exception as cb_err:
                            logger.error(f"Error in callback on_chain_error: {cb_err}")
            return {"output": f"An error occurred during LangGraph execution: {e}"}


# Example usage (conceptual, would be called from Streamlit or other interface)
async def run_example_langchain_workflow(query: str, session_id: str):
    logger.info(
        f"Starting Langchain workflow for query: '{query}' with session_id: {session_id}"
    )
    agent_instance = ScientificWorkflowAgent(mcp_session_id=session_id)

    # Example: Store a note first, then retrieve it.
    # This requires the LLM to understand the sequence and use the tools correctly.
    # For a direct test, you might invoke tools sequentially.

    # The agent now always uses the LangGraph compiled by create_react_agent.
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
        # query_for_agent = "What is UniProt ID P05067? Then, what is its AlphaFold prediction? Finally, search for stored predictions related to 'cancer'."

        query_for_agent = "I have a CSV file with file_id 'some-fake-file-id-for-test'. Can you tell me what is in it regarding 'sales'?"
        # The agent should then use the QueryProcessedCSVData tool.

        output = await run_example_langchain_workflow(query_for_agent, test_session_id)
        print("Final Agent Output:", output)

    # asyncio.run(test_run()) # Commented out to prevent auto-run without setup
