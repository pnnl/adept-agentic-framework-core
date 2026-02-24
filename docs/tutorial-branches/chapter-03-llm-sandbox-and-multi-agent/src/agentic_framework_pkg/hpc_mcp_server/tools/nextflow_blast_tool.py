from fastmcp import FastMCP, Context
from ...logger_config import get_logger  # Assuming reuse of central logger for now
import asyncio
import subprocess
import tempfile
import os
import shutil
from typing import Dict, Any, Optional, List
import uuid

logger = get_logger(__name__)

# Define the path to your Nextflow script. This should be relative to where the script runs,
# or an absolute path within the container.
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
NEXTFLOW_SCRIPT_PATH = os.getenv("NEXTFLOW_BLAST_SCRIPT_PATH", "./blast_pipeline.nf")
if not os.path.exists(NEXTFLOW_SCRIPT_PATH):
    # If it's not absolute, make it relative to the current directory
    NEXTFLOW_SCRIPT_PATH = os.path.join(CURR_DIR, NEXTFLOW_SCRIPT_PATH)


async def _ensure_session_hpc_nextflow(ctx: Context) -> str:
    """Ensures session is initialized for Nextflow tools, if needed for state."""
    # For now, let's assume session is not strictly needed for this stateless tool
    # or handled by individual tools if they become stateful.
    logger.debug(f"HPC Nextflow tool called with context: {ctx.request_id}")
    return ctx.request_id or f"hpc_nextflow_session_{uuid.uuid4()}"


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def run_nextflow_blast_pipeline(
        ctx: Context,
        sequence: str,
        database_name: str,
        blast_program: str = "blastp",  # e.g., blastp, blastn
        output_format: str = "6",  # e.g., 6 for tabular, 5 for XML
        mcp_session_id: Optional[str] = None,  # For potential future state or logging
    ) -> Dict[str, Any]:
        """
        Runs a LOCAL Nextflow pipeline to perform a BLAST search in THIS container.

        NOTE: This runs Nextflow LOCALLY in the HPC MCP server container, NOT on a remote HPC cluster.
        For submitting jobs to a REMOTE HPC cluster via SSH, use the HPC SSH tools instead.

        The Nextflow script (e.g., blast_pipeline.nf) must be available in the environment.

        Args:
            ctx: FastMCP Context.
            sequence: The query sequence in FASTA format (as a string).
            database_name: Name of the BLAST database (must be pre-formatted and accessible by BLAST).
            blast_program: The BLAST program to use (e.g., 'blastp', 'blastn').
            output_format: BLAST output format code (e.g., '6' for tabular, '5' for XML).
            mcp_session_id: Optional session ID.
        Returns:
            A dictionary with the BLAST results or an error message.
        """
        session_id_for_log = await _ensure_session_hpc_nextflow(ctx)
        await ctx.info(
            f"Session {session_id_for_log}: Received Nextflow BLAST request. Program: {blast_program}, DB: {database_name}"
        )

        # Create a temporary directory for Nextflow to work in and store inputs/outputs
        with tempfile.TemporaryDirectory(prefix="nextflow_blast_") as temp_work_dir:
            query_file_path = os.path.join(temp_work_dir, "query.fasta")
            results_dir_path = os.path.join(temp_work_dir, "results")
            os.makedirs(results_dir_path, exist_ok=True)

            # Write the sequence to the temporary query file
            with open(query_file_path, "w") as f:
                f.write(sequence)

            # Construct the Nextflow command
            # Ensure NEXTFLOW_SCRIPT_PATH points to your .nf file
            # The Nextflow script should be designed to accept these parameters
            nextflow_command = [
                "nextflow",
                "run",
                NEXTFLOW_SCRIPT_PATH,
                "--query_file",
                query_file_path,
                "--db_name",
                database_name,
                "--blast_program",
                blast_program,
                "--outdir",
                results_dir_path,
                "--output_format",
                output_format,  # Pass output format to Nextflow script
                "-profile",
                "standard",  # Or 'docker', 'conda', etc., depending on your Nextflow setup
                "-work-dir",
                os.path.join(temp_work_dir, "work"),  # Specify Nextflow work directory
                # "-Dnextflow.verbose=true" # Add this for increased Nextflow verbosity
            ]

            await ctx.info(f"Executing Nextflow command: {' '.join(nextflow_command)}")
            logger.info(f"Executing Nextflow: {' '.join(nextflow_command)}")

            try:
                # Run Nextflow command
                process = await asyncio.create_subprocess_exec(
                    *nextflow_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    await ctx.info("Nextflow pipeline completed successfully.")
                    # Assuming the Nextflow pipeline writes results to a known file, e.g., results/blast_results.txt
                    result_file_path = os.path.join(
                        results_dir_path, "blast_results.txt"
                    )  # Adjust if Nextflow script names it differently
                    if os.path.exists(result_file_path):
                        with open(result_file_path, "r") as rf:
                            blast_output = rf.read()
                        return {
                            "status": "success",
                            "output": blast_output,
                            "log_stdout": stdout.decode(errors="ignore"),
                            "log_stderr": stderr.decode(errors="ignore"),
                        }
                    else:
                        return {
                            "status": "error",
                            "message": "Nextflow completed, but result file not found.",
                            "log_stdout": stdout.decode(errors="ignore"),
                            "log_stderr": stderr.decode(errors="ignore"),
                        }
                else:
                    await ctx.error(
                        f"Nextflow pipeline execution failed. Return code: {process.returncode}"
                    )
                    logger.error(f"Nextflow stderr: {stderr.decode(errors='ignore')}")
                    return {
                        "status": "error",
                        "message": "Nextflow pipeline execution failed.",
                        "details": stderr.decode(errors="ignore"),
                        "log_stdout": stdout.decode(errors="ignore"),
                    }
            except Exception as e:
                logger.error(f"Error running Nextflow pipeline: {e}", exc_info=True)
                await ctx.error(f"Failed to execute Nextflow pipeline: {e}")
                return {
                    "status": "error",
                    "message": f"An unexpected error occurred: {e}",
                }

    logger.info("HPC Nextflow BLAST tool registered.")
