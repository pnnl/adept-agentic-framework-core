from langchain.tools import BaseTool
from pydantic import (
    Field,
    BaseModel,
)  # For describing tool inputs if not using default string
from typing import Type, Optional, Any, Dict, TypeVar, List
import asyncio
from fastmcp import Client as MCPClient
import os
import json
from dotenv import load_dotenv
from pathlib import Path

from ..logger_config import get_logger  # Use centralized logger

logger = get_logger(__name__)

# Load environment variables from .env file at the root of the codebase
root_dir = Path(
    __file__
).parent.parent.parent.parent  # Navigate to root from current file
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path)

# --- MCP Server URL Configuration for Langchain Tools ---

# Default MCP Server URL (for most tools, e.g., running on port 8080)
# For local development, set DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN=http://localhost:8080/mcp in your .env
# For Docker, it defaults to the service name 'mcp_server'.
DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN = os.getenv(
    "DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN", "http://mcp_server:8080/mcp"
)
logger.info(
    f"Langchain Tools: Default MCP Server URL set to: {DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN}"
)

# HPC MCP Server URL (for HPC-specific tools, e.g., running on port 8081)
# For local development, set HPC_MCP_SERVER_URL_FOR_LANGCHAIN=http://localhost:8081/mcp in your .env
# For Docker, it defaults to the service name 'hpc-mcp-server'.
HPC_MCP_SERVER_URL_FOR_LANGCHAIN = os.getenv(
    "HPC_MCP_SERVER_URL_FOR_LANGCHAIN", "http://hpc_mcp_server:8081/mcp"
)
logger.info(
    f"Langchain Tools: HPC MCP Server URL set to: {HPC_MCP_SERVER_URL_FOR_LANGCHAIN}"
)

# Sandbox MCP Server URL (for code execution, e.g., running on port 8082)
SANDBOX_MCP_SERVER_URL_FOR_LANGCHAIN = os.getenv(
    "SANDBOX_MCP_SERVER_URL_FOR_LANGCHAIN", "http://sandbox_mcp_server:8082/mcp"
)
logger.info(
    f"Langchain Tools: Sandbox MCP Server URL set to: {SANDBOX_MCP_SERVER_URL_FOR_LANGCHAIN}"
)


T = TypeVar("T", bound=BaseModel)


class MCPToolWrapper(BaseTool):
    """
    A Langchain BaseTool wrapper for calling tools on a remote MCP server.
    """

    mcp_client_url: str  # Explicitly set by factory functions
    actual_tool_name: str
    # 'name' and 'description' for Langchain are set at instantiation. # This comment is outdated
    # args_schema: Optional] = None # For structured input using Pydantic
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for stateful operations."
    )
    args_schema: Optional[Type[T]] = (
        None  # Pydantic model for structured input, if needed
    )

    # This method is called by Langchain if the tool is synchronous
    def _run(self, **kwargs: Any) -> str:
        try:
            # The input from Langchain (when args_schema is used) comes as kwargs
            # Using nest_asyncio if running in a sync context that needs to call async
            # This is often needed if Langchain's agent executor is sync.
            # import nest_asyncio
            # nest_asyncio.apply()
            logger.info(
                f"Running MCPToolWrapper _run for {self.actual_tool_name} with kwargs: {kwargs}"
            )
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we might be in an async context already or need nest_asyncio
                # For simplicity, let's assume we can create a new task or use nest_asyncio
                # This part can be tricky depending on Langchain's execution model.
                # A common pattern is to use asyncio.run_coroutine_threadsafe if in a different thread.
                # For now, direct asyncio.run for simplicity, assuming it's okay in the Langchain context.
                # This might fail if an event loop is already running in the current thread.
                # A more robust solution for sync Langchain agents calling async tools:
                # However, if Langchain itself is running an async agent, _arun will be called.
                # Let's assume Langchain handles this or we are in an async context.
                # If _run is called from a sync context, this will error if loop is running.
                # A common workaround:
                try:
                    logger.debug(
                        f"Loop is running: Calling MCP tool '{self.actual_tool_name}' in sync context with params: {kwargs}"
                    )
                    return asyncio.run(self._arun(**kwargs))
                except RuntimeError as e:
                    if "cannot be called when another loop is running" in str(
                        e
                    ) or "Event loop is closed" in str(e):
                        logger.warning(
                            "Asyncio loop issue in _run, trying nest_asyncio or new loop."
                        )
                        import nest_asyncio

                        nest_asyncio.apply()
                        return asyncio.run(self._arun(**kwargs))
                    raise e
            logger.debug(
                f"Calling MCP tool '{self.actual_tool_name}' with params: {kwargs}"
            )
            return asyncio.run(self._arun(**kwargs))
        except Exception as e:
            logger.error(
                f"Error in MCPToolWrapper _run for {self.actual_tool_name}: {e}",
                exc_info=True,
            )
            return f"Error executing tool {self.actual_tool_name}: {e}"

    # This method is called by Langchain if the tool is asynchronous
    async def _arun(self, **kwargs: Any) -> str:
        # When args_schema is used, Langchain passes parsed arguments as kwargs.
        logger.info(
            f"Running MCPToolWrapper _arun for {self.actual_tool_name} with kwargs: {kwargs}"
        )
        params = kwargs

        # These are the args from Langchain, based on the tool's args_schema.
        # The mcp_session_id should be included here by the LLM if the schema defines it.
        params_for_tool_call = params.copy()

        # Check if mcp_session_id was provided by the LLM (as per args_schema).
        # If not, and if the wrapper has a default mcp_session_id, use that.
        # Otherwise, the tool will be called without an explicit mcp_session_id in its params,
        # which might be fine for some tools or lead to issues for stateful ones.
        if (
            "mcp_session_id" not in params_for_tool_call
            or params_for_tool_call.get("mcp_session_id") is None
        ):
            logger.info(
                f"mcp_session_id not provided by LLM for tool '{self.actual_tool_name}'. Checking wrapper's default."
            )
            if (
                self.mcp_session_id
            ):  # Fallback to wrapper's own session_id if LLM didn't provide
                params_for_tool_call["mcp_session_id"] = self.mcp_session_id
                logger.debug(
                    f"LLM did not provide mcp_session_id for tool '{self.actual_tool_name}'. "
                    f"Using wrapper's default: {self.mcp_session_id}"
                )
            else:
                # This warning is important. If it appears, the LLM isn't providing the session_id
                # despite the prompt and schema, and no default is set on the wrapper.
                logger.warning(
                    f"MCP Session ID not provided by LLM and no default in wrapper for tool '{self.actual_tool_name}'. "
                    f"Tool may operate in a new/default session or fail if it strictly requires one. "
                    f"Params received from LLM: {kwargs}"
                )
        else:
            logger.debug(
                f"MCP Session ID '{params_for_tool_call.get('mcp_session_id')}' provided by LLM for tool '{self.actual_tool_name}'."
            )

        logger.debug(
            f"MCPToolWrapper _arun for {self.actual_tool_name}: "
            f"raw_kwargs_from_langchain={kwargs}, "
            f"final_params_for_tool_call={params_for_tool_call}"
        )
        try:
            logger.debug(
                f"Connecting to MCP server at {self.mcp_client_url} for tool {self.actual_tool_name} using URL: {self.mcp_client_url}"
            )
            # Initialize MCPClient WITHOUT session_id in constructor
            async with MCPClient(self.mcp_client_url) as client:
                logger.debug(
                    f"Calling MCP tool '{self.actual_tool_name}' on server with params: {params_for_tool_call}"
                )
                result_content_list = await client.call_tool(
                    self.actual_tool_name, params_for_tool_call
                )

                # Process result: FastMCP's call_tool returns List[ContentPart]
                if isinstance(result_content_list, list) and result_content_list:
                    first_content_part = result_content_list[0]
                    if hasattr(first_content_part, "text"):  # Handles TextContent
                        # Langchain tools expect string outputs.
                        # If the tool returns a JSON string, it will be in first_content_part.text.
                        return first_content_part.text
                    else:
                        # If not TextContent, or list is empty but not None, convert to string.
                        return str(result_content_list)
                elif result_content_list is None:  # Tool might return None
                    return ""

                return str(
                    result_content_list
                )  # Fallback for other types or empty list
        except ConnectionRefusedError:
            logger.error(
                f"MCP Server connection refused at {self.mcp_client_url} for tool {self.actual_tool_name}.",
                exc_info=True,
            )
            return f"Error: Could not connect to MCP server to run tool {self.actual_tool_name}."
        except Exception as e:
            logger.error(
                f"Exception calling MCP tool {self.actual_tool_name}: {e}",
                exc_info=True,
            )
            return f"Error during MCP tool {self.actual_tool_name} execution: {e}"


# --- Define Pydantic models for structured tool inputs (recommended) ---
class QueryCSVToolInput(BaseModel):
    user_query: str = Field(description="The natural language query for the CSV data.")
    file_id: str = Field(
        description="The file_id of the CSV registered via 'register_uploaded_csv'."
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for stateful context."
    )  # Agent needs to manage this
    top_k: int = Field(
        3, description="Number of top relevant chunks to retrieve for RAG."
    )


class PerformCalculationInput(BaseModel):
    expression: str = Field(description="The mathematical expression to evaluate.")
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class StoreNoteInput(BaseModel):
    note_text: str = Field(description="The text of the note to store.")
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class RetrieveNotesInput(BaseModel):
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class QueryUniProtInput(BaseModel):
    accession_id: str = Field(description="The UniProt accession ID (e.g., P05067).")
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class WebSearchAPIInput(BaseModel):
    query: str = Field(description="The search query for the web search.")
    num_results: int = Field(5, description="Number of search results to return.")
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class WebSearchScrapingInput(BaseModel):
    query: str = Field(description="The search query for the web search.")
    num_results: int = Field(5, description="Number of search results to return.")
    timeout: int = Field(
        20, description="Timeout in seconds for the scraping operation."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


# class PerformBlastpSearchInput(BaseModel):
#     sequence: str = Field(description="The protein sequence to search with (FASTA format or raw sequence).")
#     database: str = Field("nr", description="The BLAST database to search against (e.g., 'nr', 'swissprot', 'pdb'). Defaults to 'nr'.")
#     expect: float = Field(10.0, description="The expectation value (E-value) threshold. Defaults to 10.0.")
#     hitlist_size: int = Field(10, description="The maximum number of hits to return. Defaults to 10.")
#     mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")

# class PerformBlastnSearchInput(BaseModel):
#     sequence: str = Field(description="The nucleotide sequence to search with (FASTA format or raw sequence).")
#     database: str = Field("nt", description="The BLAST database to search against (e.g., 'nt', 'refseq_rna'). Defaults to 'nt'.")
#     expect: float = Field(10.0, description="The expectation value (E-value) threshold. Defaults to 10.0.")
#     hitlist_size: int = Field(10, description="The maximum number of hits to return. Defaults to 10.")
#     mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


# --- Pydantic models for Biopython-based BLAST tools (can be same as above if params match) ---
class PerformBlastpSearchBiopythonInput(BaseModel):
    sequence: str = Field(
        description="The protein sequence to search with (FASTA format or raw sequence)."
    )
    database: str = Field(
        "nr",
        description="The BLAST database to search against. Available NCBI protein databases: 'nr' (non-redundant, default, most comprehensive), 'swissprot' (curated UniProt/Swiss-Prot, high-quality manual annotations), 'pdb' (Protein Data Bank with experimentally determined structures), 'refseq_protein' (NCBI Reference Sequence proteins), 'refseq_select_prot' (representative RefSeq proteins), 'env_nr' (environmental sequences), 'pataa' (patents). For curated, high-quality protein annotations, use 'swissprot'. Any NCBI protein database name is supported.",
    )
    expect: float = Field(
        10.0, description="The expectation value (E-value) threshold. Defaults to 10.0."
    )
    hitlist_size: int = Field(
        10, description="The maximum number of hits to return. Defaults to 10."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class PerformBlastnSearchBiopythonInput(BaseModel):
    sequence: str = Field(
        description="The nucleotide sequence to search with (FASTA format or raw sequence)."
    )
    database: str = Field(
        "nt",
        description="The BLAST database to search against (e.g., 'nt', 'refseq_rna'). Defaults to 'nt'.",
    )
    expect: float = Field(
        10.0, description="The expectation value (E-value) threshold. Defaults to 10.0."
    )
    hitlist_size: int = Field(
        10, description="The maximum number of hits to return. Defaults to 10."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


# --- Pydantic models for PubChem tools (matching pubchem_tool.py parameters) ---
class SearchPubChemQueryInput(BaseModel):
    query: str = Field(
        description="The compound name, identifier (e.g., CID, SMILES), or general search query for PubChem."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")
    max_results: int = Field(
        5, description="Maximum number of results to return. Defaults to 5."
    )


class SearchPubChemByNameInput(BaseModel):
    chemical_name: str = Field(
        description="The compound name, identifier (e.g., CID, SMILES), or search query for PubChem."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")
    max_results: int = Field(
        5, description="Maximum number of results to return. Defaults to 5."
    )


class GetPubChemCompoundPropertiesInput(BaseModel):
    cid: int = Field(
        description="The PubChem Compound ID (CID) for which to retrieve properties."
    )
    properties: Optional[List[str]] = Field(
        None,
        description="A list of specific properties to retrieve (e.g., ['molecular_formula', 'iupac_name']). If None, a default set is returned.",
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class ListUploadedFilesInput(BaseModel):
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for context."
    )


# --- Pydantic models for AlphaFold tools ---
class GetAlphaFoldPredictionInput(BaseModel):
    uniprot_accession: str = Field(
        description="The UniProt accession ID for which to fetch the AlphaFold prediction (e.g., P05067)."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class QueryStoredAlphaFoldPredictionsInput(BaseModel):
    query_text: str = Field(
        description="A natural language query to search stored AlphaFold prediction summaries."
    )
    top_k: int = Field(
        3, description="Maximum number of relevant stored predictions to return."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


# --- Pydantic model for Nextflow BLAST tool ---
class RunNextflowBlastInput(BaseModel):
    sequence: str = Field(
        description="The query sequence in FASTA format (as a string)."
    )
    database_name: str = Field(
        description="Name of the BLAST database (must be pre-formatted and accessible by BLAST)."
    )
    blast_program: str = Field(
        "blastp", description="The BLAST program to use (e.g., 'blastp', 'blastn')."
    )
    output_format: str = Field(
        "6",
        description="BLAST output format code (e.g., '6' for tabular, '5' for XML).",
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID (optional for this tool)."
    )


# --- Pydantic model for Video Transcription tool ---
class RunVideoTranscriptionInput(BaseModel):
    video_input_path_or_url: str = Field(
        description="URL of the video or an absolute path to a video file accessible by the HPC server (e.g., /app/data/uploaded_files/my_video.mp4)."
    )
    whisper_model_size: str = Field(
        "base",
        description="Size of the Whisper model to use for transcription (e.g., tiny, base, small, medium, large).",
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID (optional)."
    )


# --- Pydantic model for Sandbox tool ---
class ExecuteCodeInput(BaseModel):
    code: str = Field(
        description="A string of code to be executed in the sandbox. The last line should be an expression for the result for Python/JavaScript."
    )
    language: str = Field(
        "python",
        description="The programming language of the code. Supported: 'python', 'javascript', 'shell'. Defaults to 'python'.",
    )
    generate_plot: bool = Field(
        False,
        description="Set to True to enable plot generation for Python code using libraries like matplotlib or plotly. The plot will be returned as an image or interactive HTML.",
    )
    sandbox_image: Optional[str] = Field(
        None,
        description="Optional. The full URI of a custom Docker image to use for the sandbox (e.g., 'ubuntu:latest', 'ghcr.io/user/my-sandbox:tag'). If provided, this overrides the 'language' parameter for image selection.",
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID (optional for this tool)."
    )


# --- Pydantic model for GitXRay tool ---
class ScanGithubRepoInput(BaseModel):
    repo_url: str = Field(
        description="The full URL of the public GitHub repository to scan for secrets (e.g., 'https://github.com/user/repo')."
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID (optional for this tool)."
    )


# --- Pydantic models for HPC SSH tools ---
class TestHPCConnectionInput(BaseModel):
    hpc_host: Optional[str] = Field(
        None, description="HPC hostname (defaults to HPC_HOST env var)."
    )
    hpc_user: Optional[str] = Field(
        None, description="SSH username (defaults to HPC_USER env var)."
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID (optional for this tool)."
    )


class SubmitSlurmJobInput(BaseModel):
    script_path: str = Field(
        description="Path to batch script on REMOTE HPC (e.g., /home/user/jobs/hello.sh)."
    )
    job_name: Optional[str] = Field(
        None, description="Optional job name (overrides script's #SBATCH --job-name)."
    )
    hpc_host: Optional[str] = Field(
        None, description="HPC hostname (defaults to HPC_HOST env var)."
    )
    hpc_user: Optional[str] = Field(
        None, description="SSH username (defaults to HPC_USER env var)."
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID (optional for this tool)."
    )


class CheckSlurmJobStatusInput(BaseModel):
    job_id: str = Field(description="Slurm job ID (returned by submit_slurm_job).")
    hpc_host: Optional[str] = Field(
        None, description="HPC hostname (defaults to HPC_HOST env var)."
    )
    hpc_user: Optional[str] = Field(
        None, description="SSH username (defaults to HPC_USER env var)."
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID (optional for this tool)."
    )


# --- Pydantic models for Multi-Agent tools ---
class CreateMultiAgentSessionInput(BaseModel):
    roles: List[str] = Field(
        description="A list of expert roles for the worker agents, e.g., ['chemist', 'data scientist']."
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for context."
    )


class GeneratePlanForMultiAgentTaskInput(BaseModel):
    multi_agent_session_id: str = Field(
        description="The ID of the multi-agent session, returned by CreateMultiAgentSession."
    )
    task: str = Field(description="The high-level task for which to generate a plan.")
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for context."
    )


class ExecuteApprovedPlanInput(BaseModel):
    multi_agent_session_id: str = Field(
        description="The ID of the multi-agent session which has a pending plan."
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for context."
    )


class UpdatePendingPlanInput(BaseModel):
    multi_agent_session_id: str = Field(
        description="The ID of the multi-agent session which has a pending plan."
    )
    edited_plan: str = Field(
        description="The full, user-edited version of the plan to be executed."
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for context."
    )


class TerminateMultiAgentSessionInput(BaseModel):
    multi_agent_session_id: str = Field(
        description="The ID of the multi-agent session to terminate."
    )
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for context."
    )


class ListActiveMultiAgentSessionsInput(BaseModel):
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for context."
    )


# --- Factory functions to create Langchain tool instances ---
def get_mcp_query_csv_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="QueryProcessedDocumentData",  # Renamed for broader scope
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="query_file_content",  # Name on MCP Server
        description="Queries a previously uploaded and processed document (e.g., CSV, PDF, DOCX, image) using its file_id. Use this to get answers from the document's content.",
        args_schema=QueryCSVToolInput,  # Crucial for LLM to know how to structure input
        mcp_session_id=mcp_session_id,
    )


def get_mcp_perform_calculation_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="PerformSimpleCalculation",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="perform_calculation",
        description="Evaluates a simple mathematical expression (e.g., '2 + 2 * 3').",
        args_schema=PerformCalculationInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_store_note_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="StoreNoteInSession",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="store_note_in_session",
        description="Stores a textual note in the current user's session.",
        args_schema=StoreNoteInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_retrieve_notes_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="RetrieveSessionNotes",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="retrieve_session_notes",
        description="Retrieves all notes previously stored in the current user's session.",
        args_schema=RetrieveNotesInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_query_uniprot_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="QueryUniProt",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="query_uniprot_by_accession",  # Name on MCP Server
        description="Queries the UniProt database for protein information using an accession ID.",
        args_schema=QueryUniProtInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_web_search_api_tool_langchain(
    mcp_session_id: Optional[str] = None,
) -> MCPToolWrapper:
    return MCPToolWrapper(
        name="PerformWebSearchAPI",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="perform_web_search_api",
        description="Performs a robust web search using a dedicated search API. Returns a list of results including titles, links, and snippets. This is the preferred and most reliable method for web searches.",
        args_schema=WebSearchAPIInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_web_search_scraping_tool_langchain(
    mcp_session_id: Optional[str] = None,
) -> MCPToolWrapper:
    return MCPToolWrapper(
        name="PerformWebSearchScraping",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="perform_web_search_scraping",
        description="Performs a web search by scraping a search engine's results page. This is less reliable than the API version and should be used as a fallback.",
        args_schema=WebSearchScrapingInput,
        mcp_session_id=mcp_session_id,
    )


# def get_mcp_blastp_tool_langchain(mcp_session_id: Optional[str] = None):
#     return MCPToolWrapper(
#         name="PerformProteinBlastSearch", # Descriptive name for the agent
#         mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
#         actual_tool_name="perform_blastp_search", # Name on MCP Server
#         description="Performs a protein sequence homology search (BLASTP) against a database using the NCBI web service. Requires a protein sequence.",
#         args_schema=PerformBlastpSearchInput, # Use the Pydantic model for input
#         mcp_session_id=mcp_session_id
#     )

# def get_mcp_blastn_tool_langchain(mcp_session_id: Optional[str] = None):
#     return MCPToolWrapper(
#         name="PerformNucleotideBlastSearch", # Descriptive name for the agent
#         mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
#         actual_tool_name="perform_blastn_search", # Name on MCP Server
#         description="Performs a nucleotide sequence homology search (BLASTN) against a database using the NCBI web service. Requires a nucleotide sequence.",
#         args_schema=PerformBlastnSearchInput,
#         mcp_session_id=mcp_session_id
#     )


# --- Factory function for PubChem tool ---
def get_mcp_search_pubchem_by_query_tool_langchain(
    mcp_session_id: Optional[str] = None,
):
    return MCPToolWrapper(
        name="SearchPubChemByQuery",  # Descriptive name for the agent
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="search_pubchem_by_query",  # Correct name on MCP Server from pubchem_tool.py
        description="Searches the PubChem database for chemical compounds by query string and returns matching CIDs and basic info.",
        args_schema=SearchPubChemQueryInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_search_pubchem_by_name_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="SearchPubChemByName",  # Descriptive name for the agent
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="search_pubchem_by_name",  # Correct name on MCP Server from pubchem_tool.py
        description="Searches the PubChem database for chemical compounds by name or identifier and returns matching CIDs and basic info.",
        args_schema=SearchPubChemByNameInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_get_pubchem_compound_properties_tool_langchain(
    mcp_session_id: Optional[str] = None,
):
    return MCPToolWrapper(
        name="GetPubChemCompoundProperties",  # Descriptive name for the agent
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="get_pubchem_compound_properties",  # Correct name on MCP Server from pubchem_tool.py
        description="Retrieves detailed properties (like formula, weight, SMILES, InChI, IUPAC name) for a specific PubChem Compound ID (CID).",
        args_schema=GetPubChemCompoundPropertiesInput,
        mcp_session_id=mcp_session_id,
    )


# --- Factory functions for Biopython-based BLAST tools ---
def get_mcp_blastp_biopython_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="PerformProteinBlastSearchBiopython",  # Descriptive name for the agent
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="perform_blastp_search_biopython",  # Name on MCP Server from blastq_tool.py
        description="Performs a protein sequence homology search (BLASTP) using Biopython against NCBI databases. Available databases: 'nr' (non-redundant, default, most comprehensive), 'swissprot' (curated UniProt/Swiss-Prot with high-quality manual annotations), 'pdb' (Protein Data Bank with experimentally determined structures), 'refseq_protein' (NCBI Reference Sequence proteins), 'refseq_select_prot', 'env_nr', 'pataa'. Specify database parameter to choose. For curated, high-quality protein annotations, use 'swissprot'. Any NCBI protein database name is supported.",
        args_schema=PerformBlastpSearchBiopythonInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_blastn_biopython_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="PerformNucleotideBlastSearchBiopython",  # Descriptive name for the agent
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="perform_blastn_search_biopython",  # Name on MCP Server from blastq_tool.py
        description="Performs a nucleotide sequence homology search (BLASTN) using Biopython against a database via the NCBI web service. Requires a nucleotide sequence.",
        args_schema=PerformBlastnSearchBiopythonInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_list_uploaded_files_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="ListUploadedFiles",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="list_uploaded_files",
        description="Lists all files that have been uploaded and processed in the current session, showing their file_id and original filename. Use this to know what files are available for querying.",
        args_schema=ListUploadedFilesInput,
        mcp_session_id=mcp_session_id,
    )


# --- Factory functions for AlphaFold tools ---
def get_mcp_alphafold_prediction_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="GetAlphaFoldPrediction",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="get_alphafold_prediction_and_store",  # Name on MCP Server
        description="Fetches a protein structure prediction from AlphaFold EBI using a UniProt accession ID. Stores a summary for future RAG queries and returns the prediction data.",
        args_schema=GetAlphaFoldPredictionInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_query_stored_alphafold_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="SearchStoredAlphaFoldPredictions",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="query_stored_alphafold_predictions",  # Name on MCP Server
        description="Searches previously fetched and stored AlphaFold prediction summaries based on a natural language query. Returns information about relevant stored predictions.",
        args_schema=QueryStoredAlphaFoldPredictionsInput,
        mcp_session_id=mcp_session_id,
    )


# --- Factory function for HPC Nextflow BLAST tool ---
def get_mcp_run_nextflow_blast_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="RunNextflowBlastPipelineHPC",  # Name for Langchain agent
        mcp_client_url=HPC_MCP_SERVER_URL_FOR_LANGCHAIN,  # Target HPC server
        actual_tool_name="run_nextflow_blast_pipeline",  # Actual tool name on HPC MCP Server
        description="Runs a Nextflow pipeline on the HPC server to perform a BLAST search. "
        "Provide the sequence, database name, BLAST program (e.g., blastp, blastn), and output format.",
        args_schema=RunNextflowBlastInput,
        mcp_session_id=mcp_session_id,  # mcp_session_id is optional for this specific HPC tool
    )


# --- Factory function for HPC Video Transcription tool ---
def get_mcp_run_video_transcription_tool_langchain(
    mcp_session_id: Optional[str] = None,
):
    return MCPToolWrapper(
        name="RunVideoTranscriptionPipelineHPC",
        mcp_client_url=HPC_MCP_SERVER_URL_FOR_LANGCHAIN,  # Target HPC server
        actual_tool_name="run_video_transcription_pipeline",
        description="Runs a pipeline on the HPC server to download/process a video, transcribe its audio using Whisper, "
        "and summarize the transcript. The transcript is also indexed for RAG. "
        "Input must be a video URL or an absolute server-accessible file path (e.g., from a shared volume like /app/data/uploaded_files/video.mp4). Returns a summary and a file_id for the indexed transcript.",
        args_schema=RunVideoTranscriptionInput,
        mcp_session_id=mcp_session_id,
    )


# --- Factory function for Sandbox Code Execution tool ---
def get_mcp_execute_code_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="ExecuteCode",
        mcp_client_url=SANDBOX_MCP_SERVER_URL_FOR_LANGCHAIN,  # Target Sandbox server
        actual_tool_name="execute_code",  # Actual tool name on Sandbox MCP Server
        description="Executes a snippet of code in a secure, isolated sandbox environment and returns the output. It can also capture and return plots (e.g., from matplotlib) and interactive HTML visualizations (e.g., from plotly) generated by Python code if 'generate_plot' is set to True. Supported languages: 'python', 'javascript', 'shell'. You can also specify a custom Docker image with the 'sandbox_image' parameter. Useful for calculations, data manipulation, and visualization. The sandbox has no network access.",
        args_schema=ExecuteCodeInput,
        mcp_session_id=mcp_session_id,
    )


# --- Factory function for HPC GitXRay Scan tool ---
def get_mcp_gitxray_scan_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="ScanGithubRepositoryForSecrets",
        mcp_client_url=HPC_MCP_SERVER_URL_FOR_LANGCHAIN,  # Target HPC server
        actual_tool_name="scan_github_repository_with_gitxray",
        description="Scans a public GitHub repository for secrets and other sensitive data using GitXRay. This is a powerful security tool. Provide the full repository URL.",
        args_schema=ScanGithubRepoInput,
        mcp_session_id=mcp_session_id,
    )


# --- Factory functions for HPC SSH tools ---
def get_mcp_test_hpc_connection_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="TestHPCConnection",
        mcp_client_url=HPC_MCP_SERVER_URL_FOR_LANGCHAIN,  # Target HPC server
        actual_tool_name="test_hpc_connection",
        description="Test SSH connection to a REMOTE HPC cluster via SSH. Use this to verify connectivity to an external HPC cluster that you access via SSH. This establishes an SSH connection and runs basic commands to verify the cluster is reachable. NOTE: This connects to a REMOTE cluster via SSH, not the local Nextflow/BLAST container.",
        args_schema=TestHPCConnectionInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_submit_slurm_job_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="SubmitSlurmJob",
        mcp_client_url=HPC_MCP_SERVER_URL_FOR_LANGCHAIN,  # Target HPC server
        actual_tool_name="submit_slurm_job",
        description="Submit a Slurm batch job to a REMOTE HPC cluster via SSH. Use this tool to submit jobs to an external HPC cluster that you access via SSH. The script must already exist on the remote HPC cluster's filesystem. NOTE: This submits jobs to a REMOTE cluster via SSH, not the local Nextflow container.",
        args_schema=SubmitSlurmJobInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_check_slurm_job_status_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="CheckSlurmJobStatus",
        mcp_client_url=HPC_MCP_SERVER_URL_FOR_LANGCHAIN,  # Target HPC server
        actual_tool_name="check_slurm_job_status",
        description="Check status of a Slurm job on a REMOTE HPC cluster via SSH. Use this tool to monitor jobs on an external HPC cluster that you access via SSH. Queries the Slurm scheduler for current job state. NOTE: This checks jobs on a REMOTE cluster via SSH, not local processes.",
        args_schema=CheckSlurmJobStatusInput,
        mcp_session_id=mcp_session_id,
    )


# --- Factory functions for Multi-Agent tools ---
def get_mcp_create_multi_agent_session_tool_langchain(
    mcp_session_id: Optional[str] = None,
):
    return MCPToolWrapper(
        name="CreateMultiAgentSession",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="create_multi_agent_session",
        description="Creates a new multi-agent session with a supervisor and a team of expert worker agents for a given list of roles. Returns a session ID to be used for running tasks.",
        args_schema=CreateMultiAgentSessionInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_generate_plan_for_multi_agent_task_tool_langchain(
    mcp_session_id: Optional[str] = None,
):
    return MCPToolWrapper(
        name="GeneratePlanForMultiAgentTask",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="generate_plan_for_multi_agent_task",
        description="Generates a plan for a high-level task in a multi-agent session. The plan is returned to the user for approval. After approval, use 'ExecuteApprovedPlan' to run it.",
        args_schema=GeneratePlanForMultiAgentTaskInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_execute_approved_plan_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="ExecuteApprovedPlan",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="execute_approved_plan_in_session",
        description="Executes a plan that was previously generated and approved by the user in a specific multi-agent session.",
        args_schema=ExecuteApprovedPlanInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_update_pending_plan_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="UpdatePendingPlan",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="update_pending_plan_in_session",
        description="Updates a pending plan with a user-edited version before execution. Use this if the user provides modifications to the generated plan.",
        args_schema=UpdatePendingPlanInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_terminate_multi_agent_session_tool_langchain(
    mcp_session_id: Optional[str] = None,
):
    return MCPToolWrapper(
        name="TerminateMultiAgentSession",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="terminate_multi_agent_session",
        description="Terminates an active multi-agent session and cleans up all associated resources. Use this when a multi-agent task is complete or no longer needed.",
        args_schema=TerminateMultiAgentSessionInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_list_active_multi_agent_sessions_tool_langchain(
    mcp_session_id: Optional[str] = None,
):
    return MCPToolWrapper(
        name="ListActiveMultiAgentSessions",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="list_active_multi_agent_sessions",
        description="Lists all currently active multi-agent sessions, showing their session IDs and the roles of the agents within them.",
        args_schema=ListActiveMultiAgentSessionsInput,
        mcp_session_id=mcp_session_id,
    )


# ---------------------------------------------------------------------------
# SQL / Knowledge-Base Tools (Chapter 03 addition – ported from Chapter 00)
# ---------------------------------------------------------------------------


class IngestDataInput(BaseModel):
    file_path: str = Field(
        description=(
            "Absolute server-accessible path to the CSV, TSV, XLS, or XLSX file to "
            "ingest.  The file must be on the shared upload volume."
        )
    )
    table_name: str = Field(
        description=(
            "Logical name for the SQL table (e.g. 'proteins', 'samples').  "
            "Non-alphanumeric characters are stripped automatically."
        )
    )
    mcp_session_id: Optional[str] = Field(None, description="MCP session ID.")


class SQLQueryInput(BaseModel):
    query: str = Field(
        description=(
            "A valid SQLite SELECT statement.  Always call GetSQLSchema first to "
            "discover available table and column names.  Only SELECT is permitted — "
            "INSERT, UPDATE, DELETE, and DDL statements are rejected."
        )
    )
    mcp_session_id: Optional[str] = Field(None, description="MCP session ID.")


class RAGQueryInput(BaseModel):
    query: str = Field(
        description=(
            "A natural language question to search the ingested CSV/table data using "
            "semantic similarity.  Good for exploratory content questions.  For "
            "precise numeric or aggregation queries, use ExecuteSQL instead."
        )
    )
    mcp_session_id: Optional[str] = Field(None, description="MCP session ID.")


class GetSQLSchemaInput(BaseModel):
    mcp_session_id: Optional[str] = Field(None, description="MCP session ID.")


class ListIngestedFilesInput(BaseModel):
    mcp_session_id: Optional[str] = Field(None, description="MCP session ID.")


def get_mcp_ingest_data_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="IngestDataToSQL",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="ingest_data",
        description=(
            "Loads a CSV, TSV, XLS, or XLSX file into a SQLite database table AND "
            "indexes it in ChromaDB for semantic RAG queries.  Call this before using "
            "ExecuteSQL or QueryCSVDataWithRAG.  Returns row count and column list."
        ),
        args_schema=IngestDataInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_sql_schema_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="GetSQLSchema",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="get_sql_schema",
        description=(
            "Returns the schema (table names and column names/types) for all tables "
            "in the SQLite knowledge-base.  Always call this before writing a SQL "
            "query so you know the exact column names."
        ),
        args_schema=GetSQLSchemaInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_sql_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="ExecuteSQL",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="execute_sql",
        description=(
            "Executes a read-only SQL SELECT query against the SQLite knowledge-base "
            "database.  Only SELECT statements are permitted — INSERT, UPDATE, DELETE, "
            "and DDL statements are rejected before execution.  Always call "
            "GetSQLSchema first to discover table and column names.  Returns up to "
            "500 rows as a list of dicts (configurable via SQL_MAX_ROWS env var)."
        ),
        args_schema=SQLQueryInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_rag_query_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="QueryCSVDataWithRAG",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="query_csv_rag",
        description=(
            "Performs a semantic similarity search over previously ingested tabular "
            "data (CSV/Excel files loaded via IngestDataToSQL).  Use this for "
            "open-ended, exploratory questions about data content.  For precise "
            "numeric queries use ExecuteSQL instead."
        ),
        args_schema=RAGQueryInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_list_ingested_files_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="ListIngestedFiles",
        mcp_client_url=DEFAULT_MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="list_files",
        description=(
            "Lists all files that have been ingested into the SQL/RAG knowledge base "
            "via IngestDataToSQL."
        ),
        args_schema=ListIngestedFilesInput,
        mcp_session_id=mcp_session_id,
    )


# Add more Langchain tool wrappers for other MCP tools as needed.
