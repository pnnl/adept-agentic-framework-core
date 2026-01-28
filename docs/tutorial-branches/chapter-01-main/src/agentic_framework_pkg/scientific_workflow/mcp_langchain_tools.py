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

# Determine MCP Server URL for Langchain tools.
# Priority:
# 1. MCP_SERVER_URL_FOR_LANGCHAIN (explicit override)
# 2. MCP_SERVER_URL_LANGCHAIN_LOCAL (if defined, for local dev)
# 3. MCP_SERVER_URL_LANGCHAIN_LOCAL_DEFAULT (default for local)
# If running in Docker and need to connect to 'mcp_server' service,
# set MCP_SERVER_URL_FOR_LANGCHAIN=http://mcp_server:8080/mcp in the Langchain agent's environment.

MCP_SERVER_URL_LANGCHAIN_LOCAL_DEFAULT = "http://localhost:8080/mcp"
MCP_SERVER_URL_FOR_LANGCHAIN = os.getenv(
    "MCP_SERVER_URL_FOR_LANGCHAIN",
    os.getenv("MCP_SERVER_URL_LANGCHAIN_LOCAL", MCP_SERVER_URL_LANGCHAIN_LOCAL_DEFAULT),
)

T = TypeVar("T", bound=BaseModel)


class MCPToolWrapper(BaseTool):
    """
    A Langchain BaseTool wrapper for calling tools on a remote MCP server.
    """

    mcp_client_url: str = Field(default_factory=lambda: MCP_SERVER_URL_FOR_LANGCHAIN)
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


class WebSearchInput(BaseModel):
    query: str = Field(description="The search query for the web search.")
    num_results: int = Field(5, description="Number of search results to return.")
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class PerformBlastpSearchInput(BaseModel):
    sequence: str = Field(
        description="The protein sequence to search with (FASTA format or raw sequence)."
    )
    database: str = Field(
        "nr",
        description="The BLAST database to search against (e.g., 'nr', 'swissprot', 'pdb'). Defaults to 'nr'.",
    )
    expect: float = Field(
        10.0, description="The expectation value (E-value) threshold. Defaults to 10.0."
    )
    hitlist_size: int = Field(
        10, description="The maximum number of hits to return. Defaults to 10."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class PerformBlastnSearchInput(BaseModel):
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


# --- Pydantic models for Biopython-based BLAST tools (can be same as above if params match) ---
class PerformBlastpSearchBiopythonInput(BaseModel):
    sequence: str = Field(
        description="The protein sequence to search with (FASTA format or raw sequence)."
    )
    database: str = Field(
        "nr",
        description="The BLAST database to search against (e.g., 'nr', 'swissprot', 'pdb'). Defaults to 'nr'.",
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


class TestHPCConnectionInput(BaseModel):
    hpc_host: Optional[str] = Field(
        None, description="HPC hostname (defaults to HPC_HOST env var if not provided)."
    )
    hpc_user: Optional[str] = Field(
        None, description="SSH username (defaults to HPC_USER env var if not provided)."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class SubmitSlurmJobInput(BaseModel):
    script_path: str = Field(
        description="Path to batch script on REMOTE HPC (e.g., /home/user/jobs/hello.sh)."
    )
    job_name: Optional[str] = Field(
        None, description="Optional job name (overrides script's #SBATCH --job-name)."
    )
    hpc_host: Optional[str] = Field(
        None, description="HPC hostname (defaults to HPC_HOST env var if not provided)."
    )
    hpc_user: Optional[str] = Field(
        None, description="SSH username (defaults to HPC_USER env var if not provided)."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class CheckSlurmJobStatusInput(BaseModel):
    job_id: str = Field(description="Slurm job ID (returned by submit_slurm_job).")
    hpc_host: Optional[str] = Field(
        None, description="HPC hostname (defaults to HPC_HOST env var if not provided)."
    )
    hpc_user: Optional[str] = Field(
        None, description="SSH username (defaults to HPC_USER env var if not provided)."
    )
    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")


class ListUploadedFilesInput(BaseModel):
    mcp_session_id: Optional[str] = Field(
        None, description="The MCP session ID for context."
    )


# --- Factory functions to create Langchain tool instances ---
def get_mcp_query_csv_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="QueryProcessedDocumentData",  # Renamed for broader scope
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,  # Use the determined URL
        actual_tool_name="query_file_content",  # Name on MCP Server
        description="Queries a previously uploaded and processed document (e.g., CSV, PDF, DOCX, image) using its file_id. Use this to get answers from the document's content.",
        args_schema=QueryCSVToolInput,  # Crucial for LLM to know how to structure input
        mcp_session_id=mcp_session_id,
    )


def get_mcp_perform_calculation_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="PerformSimpleCalculation",
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,  # Use the determined URL
        actual_tool_name="perform_calculation",
        description="Evaluates a simple mathematical expression (e.g., '2 + 2 * 3').",
        args_schema=PerformCalculationInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_store_note_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="StoreNoteInSession",
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,  # Use the determined URL
        actual_tool_name="store_note_in_session",
        description="Stores a textual note in the current user's session.",
        args_schema=StoreNoteInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_retrieve_notes_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="RetrieveSessionNotes",
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,  # Use the determined URL
        actual_tool_name="retrieve_session_notes",
        description="Retrieves all notes previously stored in the current user's session.",
        args_schema=RetrieveNotesInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_query_uniprot_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="QueryUniProt",
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,  # Use the determined URL
        actual_tool_name="query_uniprot_by_accession",  # Name on MCP Server
        description="Queries the UniProt database for protein information using an accession ID.",
        args_schema=QueryUniProtInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_web_search_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="PerformWebSearch",
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,  # Use the determined URL
        actual_tool_name="perform_web_search",
        description="Performs a web search using a search engine (e.g., Google) and returns a list of results including titles, links, and snippets.",
        args_schema=WebSearchInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_blastp_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="PerformProteinBlastSearch",  # Descriptive name for the agent
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,  # Use the determined URL
        actual_tool_name="perform_blastp_search",  # Name on MCP Server
        description="Performs a protein sequence homology search (BLASTP) against a database using the NCBI web service. Requires a protein sequence.",
        args_schema=PerformBlastpSearchInput,  # Use the Pydantic model for input
        mcp_session_id=mcp_session_id,
    )


def get_mcp_blastn_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="PerformNucleotideBlastSearch",  # Descriptive name for the agent
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="perform_blastn_search",  # Name on MCP Server
        description="Performs a nucleotide sequence homology search (BLASTN) against a database using the NCBI web service. Requires a nucleotide sequence.",
        args_schema=PerformBlastnSearchInput,
        mcp_session_id=mcp_session_id,
    )


# --- Factory function for PubChem tool ---
def get_mcp_search_pubchem_by_query_tool_langchain(
    mcp_session_id: Optional[str] = None,
):
    return MCPToolWrapper(
        name="SearchPubChemByQuery",  # Descriptive name for the agent
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="search_pubchem_by_query",  # Correct name on MCP Server from pubchem_tool.py
        description="Searches the PubChem database for chemical compounds by query string and returns matching CIDs and basic info.",
        args_schema=SearchPubChemQueryInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_search_pubchem_by_name_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="SearchPubChemByName",  # Descriptive name for the agent
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
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
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="get_pubchem_compound_properties",  # Correct name on MCP Server from pubchem_tool.py
        description="Retrieves detailed properties (like formula, weight, SMILES, InChI, IUPAC name) for a specific PubChem Compound ID (CID).",
        args_schema=GetPubChemCompoundPropertiesInput,
        mcp_session_id=mcp_session_id,
    )


# --- Factory functions for Biopython-based BLAST tools ---
def get_mcp_blastp_biopython_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="PerformProteinBlastSearchBiopython",  # Descriptive name for the agent
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="perform_blastp_search_biopython",  # Name on MCP Server from blastq_tool.py
        description="Performs a protein sequence homology search (BLASTP) using Biopython against a database via the NCBI web service. Requires a protein sequence.",
        args_schema=PerformBlastpSearchBiopythonInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_blastn_biopython_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="PerformNucleotideBlastSearchBiopython",  # Descriptive name for the agent
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="perform_blastn_search_biopython",  # Name on MCP Server from blastq_tool.py
        description="Performs a nucleotide sequence homology search (BLASTN) using Biopython against a database via the NCBI web service. Requires a nucleotide sequence.",
        args_schema=PerformBlastnSearchBiopythonInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_list_uploaded_files_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="ListUploadedFiles",
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="list_uploaded_files",
        description="Lists all files that have been uploaded and processed in the current session, showing their file_id and original filename. Use this to know what files are available for querying.",
        args_schema=ListUploadedFilesInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_test_hpc_connection_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="TestHPCConnection",
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="test_hpc_connection",
        description="Test SSH connection to remote HPC cluster. Verifies SSH authentication and returns hostname, kernel, and uptime. Use this to check if the HPC cluster is reachable.",
        args_schema=TestHPCConnectionInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_submit_slurm_job_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="SubmitSlurmJob",
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="submit_slurm_job",
        description="Submit a Slurm batch job to remote HPC cluster. The script must already exist on the remote HPC filesystem. Returns the job ID.",
        args_schema=SubmitSlurmJobInput,
        mcp_session_id=mcp_session_id,
    )


def get_mcp_check_slurm_job_status_tool_langchain(mcp_session_id: Optional[str] = None):
    return MCPToolWrapper(
        name="CheckSlurmJobStatus",
        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
        actual_tool_name="check_slurm_job_status",
        description="Check status of a Slurm job on remote HPC cluster. Queries the Slurm scheduler for current job state (PENDING, RUNNING, COMPLETED, FAILED, etc.).",
        args_schema=CheckSlurmJobStatusInput,
        mcp_session_id=mcp_session_id,
    )


# Add more Langchain tool wrappers for other MCP tools as needed.
