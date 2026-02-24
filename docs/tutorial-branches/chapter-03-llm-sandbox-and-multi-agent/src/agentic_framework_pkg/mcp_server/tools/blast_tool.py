# DEPRECATED: This tool has been replaced by the blastq_tool.py module.
from fastmcp import FastMCP, Context
from ..state_manager import (
    create_session_if_not_exists,
)  # Assuming session logic might be needed later
from ...logger_config import get_logger
import httpx
import json
import asyncio  # For async sleep and polling
import uuid  # Needed if session ID generation is kept local
import logging  # For type hinting
import time  # For polling delay
import re  # For parsing RID from BLAST response
from typing import Dict, Any, Optional, List

# Use the centralized logger
logger = get_logger(__name__)


# Helper for session ID - consider making this a common utility
# (Copied from uniprot_tool.py for now, ideally refactor into a common module)
async def ensure_session_initialized_blast(ctx: Context):
    """Helper to ensure the session exists in the database."""
    session_id = get_stable_session_id_blast(ctx)
    client_id = ctx.client_id if hasattr(ctx, "client_id") else None
    await create_session_if_not_exists(session_id, client_id)
    return session_id


def get_stable_session_id_blast(ctx: Context) -> str:
    if hasattr(ctx, "session_id") and ctx.session_id:
        return ctx.session_id
    if ctx.request_id:
        return ctx.request_id
    logger.warning(
        "BLAST Tool: Could not determine a stable session ID. Generating a new one."
    )
    return str(uuid.uuid4())


def register_tools(mcp: FastMCP):

    @mcp.tool()
    async def perform_blastp_search(
        sequence: str,
        ctx: Context,
        database: str = "nr",
        expect: float = 10.0,
        hitlist_size: int = 10,
        mcp_session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Performs a protein sequence homology search (BLASTP) against a specified database
        using the NCBI BLAST web service.

        Args:
            sequence (str): The protein sequence to search with (FASTA format or raw sequence).
            database (str): The BLAST database to search against. Available NCBI protein databases:
                - 'nr' (non-redundant protein sequences, default - most comprehensive)
                - 'swissprot' (curated, manually annotated UniProt/Swiss-Prot - high quality)
                - 'pdb' (Protein Data Bank - experimentally determined structures)
                - 'refseq_protein' (NCBI Reference Sequence proteins)
                - 'refseq_select_prot' (Select representative RefSeq proteins)
                - 'env_nr' (environmental protein sequences)
                - 'pataa' (Patent protein sequences)
                Defaults to 'nr'. Any NCBI protein database name is supported.
            expect (float): The expectation value (E-value) threshold. Defaults to 10.0.
            hitlist_size (int): The maximum number of hits to return. Defaults to 10.
            ctx (Context): The FastMCP context object.
            mcp_session_id (str, optional): The MCP session ID.

        Returns:
            Dict[str, Any]: A dictionary containing the search results or an error message.
        """
        session_id = await ensure_session_initialized_blast(ctx)
        await ctx.info(
            f"Session {session_id}: Submitting BLASTP search for sequence (first 20 chars: {sequence[:20]}...) against {database}"
        )

        blast_url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"

        # 1. Submit the BLAST request
        submit_params = {
            "CMD": "Put",
            "PROGRAM": "blastp",
            "DATABASE": database,
            "QUERY": sequence,
            "EXPECT": expect,
            "HITLIST_SIZE": hitlist_size,
            "FORMAT_OBJECT": "Alignment",  # Request results in Alignment format
            "FORMAT_TYPE": "JSON2",  # Request JSON output (JSON2 is often more structured)
            "ALIGNMENT_VIEW": "Pairwise",  # Include pairwise alignments in JSON2
        }

        rid: Optional[str] = None
        try:
            async with httpx.AsyncClient(
                timeout=60.0
            ) as client:  # Increased timeout for submission
                submit_response = await client.post(blast_url, data=submit_params)
                submit_response.raise_for_status()

                # Parse the response to get the Request ID (RID) and RTOE (Estimated time)
                # NCBI's response is often HTML/text even for Put, need to parse it
                # Example: "RID = ABCDEFG\n  RTOE = 10\n..."
                response_text = submit_response.text
                rid_match = next(re.finditer(r"RID = ([A-Z0-9]+)", response_text), None)
                rtoe_match = next(re.finditer(r"RTOE = ([0-9]+)", response_text), None)

                if not rid_match:
                    await ctx.error("Failed to get RID from BLAST submission.")
                    logger.error(
                        f"BLAST submission response missing RID: {response_text[:500]}"
                    )
                    return {
                        "error": "Failed to submit BLAST request.",
                        "details": "Could not retrieve Request ID.",
                    }

                rid = rid_match.group(1)
                rtoe = (
                    int(rtoe_match.group(1)) if rtoe_match else 10
                )  # Default RTOE if not found

                await ctx.info(
                    f"BLAST request submitted successfully. RID: {rid}, Estimated time: {rtoe}s"
                )
                logger.info(f"BLAST submission successful. RID: {rid}, RTOE: {rtoe}")

        except httpx.HTTPStatusError as e:
            error_message = f"BLAST submission failed with status {e.response.status_code}. Response: {e.response.text[:200]}"
            logger.error(error_message, exc_info=True)
            await ctx.error(f"BLAST submission error: {e.response.status_code}")
            return {
                "error": "Failed to submit BLAST request.",
                "details": error_message,
            }
        except httpx.RequestError as e:
            error_message = f"Request to NCBI BLAST failed during submission: {e}"
            logger.error(error_message, exc_info=True)
            await ctx.error("BLAST submission request failed.")
            return {
                "error": "Failed to connect to NCBI BLAST for submission.",
                "details": str(e),
            }
        except Exception as e:
            error_message = f"An unexpected error occurred during BLAST submission: {e}"
            logger.error(error_message, exc_info=True)
            await ctx.error("BLAST submission failed.")
            return {
                "error": "An unexpected error occurred during BLAST submission.",
                "details": str(e),
            }

        # 2. Poll for results
        await ctx.info(f"Polling BLAST results for RID: {rid}. Estimated time: {rtoe}s")
        logger.info(f"Polling BLAST results for RID: {rid}")

        # Poll status
        status_params = {"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"}
        results_params = {
            "CMD": "Get",
            "RID": rid,
            "FORMAT_TYPE": "JSON2",
            "FORMAT_OBJECT": "Alignment",
        }

        max_poll_time = rtoe * 2 + 60  # Wait up to 2x RTOE + 60s, adjust as needed
        poll_interval = 5  # seconds
        start_time = time.time()

        while time.time() - start_time < max_poll_time:
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    status_response = await client.get(blast_url, params=status_params)
                    status_response.raise_for_status()
                    status_text = status_response.text

                    if "Status=READY" in status_text:
                        logger.info(f"BLAST results for RID {rid} are READY.")
                        break  # Results are ready
                    elif (
                        "Status=FAILED" in status_text
                        or "There are no results for this query" in status_text
                    ):
                        await ctx.error(
                            f"BLAST search failed or found no results for RID: {rid}."
                        )
                        logger.error(
                            f"BLAST search failed or no results for RID {rid}. Status text: {status_text[:500]}"
                        )
                        return {
                            "query": sequence[:20] + "...",
                            "database": database,
                            "results": [],
                            "message": "BLAST search failed or found no results.",
                        }
                    elif "Status=UNKNOWN" in status_text:
                        await ctx.error(f"BLAST search status UNKNOWN for RID: {rid}.")
                        logger.error(
                            f"BLAST search status UNKNOWN for RID {rid}. Status text: {status_text[:500]}"
                        )
                        return {
                            "error": "BLAST search status unknown.",
                            "details": f"RID: {rid}",
                        }

                await asyncio.sleep(poll_interval)  # Wait before polling again
                await ctx.info(f"Polling BLAST results for RID: {rid}...")

            except Exception as e:
                logger.error(
                    f"Error polling BLAST status for RID {rid}: {e}", exc_info=True
                )
                await ctx.warning(f"Error polling BLAST status: {e}. Will retry.")
                await asyncio.sleep(poll_interval)  # Wait on error too

        if "Status=READY" not in status_text:
            await ctx.error(
                f"BLAST results for RID {rid} did not become ready within timeout."
            )
            logger.error(f"BLAST polling timed out for RID {rid}.")
            return {"error": "BLAST search timed out.", "details": f"RID: {rid}"}

        # 3. Retrieve the results
        await ctx.info(f"Retrieving BLAST results for RID: {rid}")
        try:
            async with httpx.AsyncClient(
                timeout=60.0
            ) as client:  # Increased timeout for results retrieval
                results_response = await client.get(blast_url, params=results_params)
                results_response.raise_for_status()

                response_content_type = results_response.headers.get(
                    "Content-Type", "N/A"
                )
                logger.info(
                    f"BLAST results response Content-Type for RID {rid}: {response_content_type}"
                )

                # Read raw bytes and attempt decoding, falling back to latin-1
                response_bytes = await results_response.aread()
                response_text_content = (
                    ""  # Initialize for the final json.JSONDecodeError catch block
                )
                try:
                    response_text_content = response_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    logger.warning(
                        f"UTF-8 decoding failed for BLAST results (RID: {rid}). Attempting latin-1."
                    )
                    response_text_content = response_bytes.decode(
                        "latin-1", errors="replace"
                    )

                # Attempt to extract the main JSON object if there's leading/trailing garbage
                try:
                    # Find the first '{' and the last '}'
                    first_brace = response_text_content.find("{")
                    last_brace = response_text_content.rfind("}")

                    if (
                        first_brace != -1
                        and last_brace != -1
                        and last_brace > first_brace
                    ):
                        json_payload_str = response_text_content[
                            first_brace : last_brace + 1
                        ]
                        try:
                            blast_data = json.loads(json_payload_str)
                            logger.debug(
                                f"Successfully parsed extracted JSON payload for RID {rid}."
                            )
                        except json.JSONDecodeError as e_inner:
                            logger.warning(
                                f"Failed to parse extracted JSON substring for RID {rid}: '{json_payload_str[:200]}...'. Error: {e_inner}. Will attempt to parse original content."
                            )
                            blast_data = json.loads(response_text_content)  # Fallback
                    else:
                        logger.debug(
                            f"Could not find clear {{...}} structure for RID {rid}, attempting to parse original content."
                        )
                        blast_data = json.loads(response_text_content)
                except json.JSONDecodeError:
                    raise  # Re-raise to be caught by the outer handler that logs full response_text_content

                # The structure is roughly: {'Report': {'Program': 'blastp', 'Version': ..., 'Parameters': {...}, 'Search': {'query_len': ..., 'db': ..., 'hits': [...]}}}
                hits = blast_data.get("Report", {}).get("Search", {}).get("hits", [])

                if not hits:
                    await ctx.info(f"BLAST search for RID {rid} returned no hits.")
                    return {
                        "query": sequence[:20] + "...",
                        "database": database,
                        "results": [],
                        "message": "BLAST search completed, but found no hits.",
                    }

                # Truncate hits to key information
                truncated_hits = []
                for hit in hits:
                    # Each hit can have multiple definitions and hsps (high-scoring segment pairs)
                    accession = hit.get("accession")
                    title = hit.get("description", [{}])[0].get(
                        "title", "N/A"
                    )  # Get title from first description

                    # Summarize HSPs - take the best one (usually first)
                    hsps = hit.get("hsps", [])
                    hsp_summary = None
                    if hsps:
                        best_hsp = hsps[0]  # Assuming first HSP is the best
                        hsp_summary = {
                            "bit_score": best_hsp.get("bit_score"),
                            "score": best_hsp.get("score"),
                            "evalue": best_hsp.get("evalue"),
                            "identity_percent": (
                                best_hsp.get("identity", 0)
                                / best_hsp.get("align_len", 1)
                            )
                            * 100
                            if best_hsp.get("align_len", 1) > 0
                            else 0,
                            "query_from": best_hsp.get("query_from"),
                            "query_to": best_hsp.get("query_to"),
                            "hit_from": best_hsp.get("hit_from"),
                            "hit_to": best_hsp.get("hit_to"),
                            "align_len": best_hsp.get("align_len"),
                        }

                    truncated_hits.append(
                        {
                            "accession": accession,
                            "title": title,
                            "hsp_summary": hsp_summary,
                            # Optionally include full hsps or other hit details if needed
                        }
                    )

                await ctx.info(
                    f"Successfully retrieved {len(truncated_hits)} BLAST hits for RID {rid}"
                )
                return {
                    "query": sequence[:20] + "...",
                    "database": database,
                    "results": truncated_hits,
                }

        except httpx.HTTPStatusError as e:
            error_message = f"BLAST results retrieval failed with status {e.response.status_code}. Response: {e.response.text[:200]}"
            logger.error(error_message, exc_info=True)
            await ctx.error(f"BLAST results retrieval error: {e.response.status_code}")
            return {
                "error": "Failed to retrieve BLAST results.",
                "details": error_message,
            }
        except httpx.RequestError as e:
            error_message = (
                f"Request to NCBI BLAST failed during results retrieval: {e}"
            )
            logger.error(error_message, exc_info=True)
            await ctx.error("BLAST results retrieval request failed.")
            return {
                "error": "Failed to connect to NCBI BLAST for results.",
                "details": str(e),
            }
        except json.JSONDecodeError as e:
            error_message = f"Failed to parse JSON response from NCBI BLAST for RID {rid}. Content (first 500 chars): '{response_text_content[:500]}'. Error: {e}"
            logger.error(
                error_message, exc_info=False
            )  # exc_info=False as we are logging the content
            await ctx.error("BLAST results parsing error.")
            return {
                "error": "Invalid response format from NCBI BLAST.",
                "details": str(e),
            }
        except Exception as e:
            error_message = (
                f"An unexpected error occurred during BLAST results retrieval: {e}"
            )
            logger.error(error_message, exc_info=True)
            await ctx.error("BLAST results retrieval failed.")
            return {
                "error": "An unexpected error occurred during BLAST results retrieval.",
                "details": str(e),
            }

    @mcp.tool()
    async def perform_blastn_search(
        sequence: str,
        ctx: Context,
        database: str = "nt",
        expect: float = 10.0,
        hitlist_size: int = 10,
        mcp_session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Performs a nucleotide sequence homology search (BLASTN) against a specified database
        using the NCBI BLAST web service.

        Args:
            sequence (str): The nucleotide sequence to search with (FASTA format or raw sequence).
            database (str): The BLAST database to search against (e.g., 'nt', 'refseq_rna', 'human_genomic'). Defaults to 'nt'.
            expect (float): The expectation value (E-value) threshold. Defaults to 10.0.
            hitlist_size (int): The maximum number of hits to return. Defaults to 10.
            ctx (Context): The FastMCP context object.
            mcp_session_id (str, optional): The MCP session ID.

        Returns:
            Dict[str, Any]: A dictionary containing the search results or an error message.
        """
        session_id = await ensure_session_initialized_blast(
            ctx
        )  # Reusing the same session logic
        await ctx.info(
            f"Session {session_id}: Submitting BLASTN search for sequence (first 20 chars: {sequence[:20]}...) against {database}"
        )

        blast_url = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"

        # 1. Submit the BLAST request
        submit_params = {
            "CMD": "Put",
            "PROGRAM": "blastn",  # Changed to blastn
            "DATABASE": database,
            "QUERY": sequence,
            "EXPECT": expect,
            "HITLIST_SIZE": hitlist_size,
            "FORMAT_OBJECT": "Alignment",
            "FORMAT_TYPE": "JSON2",
            "ALIGNMENT_VIEW": "Pairwise",
        }

        rid: Optional[str] = None
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                submit_response = await client.post(blast_url, data=submit_params)
                submit_response.raise_for_status()

                response_text = submit_response.text
                rid_match = next(re.finditer(r"RID = ([A-Z0-9]+)", response_text), None)
                rtoe_match = next(re.finditer(r"RTOE = ([0-9]+)", response_text), None)

                if not rid_match:
                    await ctx.error("Failed to get RID from BLASTN submission.")
                    logger.error(
                        f"BLASTN submission response missing RID: {response_text[:500]}"
                    )
                    return {
                        "error": "Failed to submit BLASTN request.",
                        "details": "Could not retrieve Request ID.",
                    }

                rid = rid_match.group(1)
                rtoe = int(rtoe_match.group(1)) if rtoe_match else 10

                await ctx.info(
                    f"BLASTN request submitted successfully. RID: {rid}, Estimated time: {rtoe}s"
                )
                logger.info(f"BLASTN submission successful. RID: {rid}, RTOE: {rtoe}")

        except httpx.HTTPStatusError as e:
            error_message = f"BLASTN submission failed with status {e.response.status_code}. Response: {e.response.text[:200]}"
            logger.error(error_message, exc_info=True)
            await ctx.error(f"BLASTN submission error: {e.response.status_code}")
            return {
                "error": "Failed to submit BLASTN request.",
                "details": error_message,
            }
        except Exception as e:  # Catch other errors like httpx.RequestError
            error_message = (
                f"An unexpected error occurred during BLASTN submission: {e}"
            )
            logger.error(error_message, exc_info=True)
            await ctx.error("BLASTN submission failed.")
            return {
                "error": "An unexpected error occurred during BLASTN submission.",
                "details": str(e),
            }

        # 2. Poll for results
        await ctx.info(
            f"Polling BLASTN results for RID: {rid}. Estimated time: {rtoe}s"
        )
        status_params = {"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"}
        results_params = {
            "CMD": "Get",
            "RID": rid,
            "FORMAT_TYPE": "JSON2",
            "FORMAT_OBJECT": "Alignment",
        }
        max_poll_time = rtoe * 2 + 60
        poll_interval = 5
        start_time = time.time()
        status_text = ""  # Initialize status_text

        while time.time() - start_time < max_poll_time:
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    status_response = await client.get(blast_url, params=status_params)
                    status_response.raise_for_status()
                    status_text = status_response.text
                    if "Status=READY" in status_text:
                        break
                    elif (
                        "Status=FAILED" in status_text
                        or "There are no results for this query" in status_text
                    ):
                        await ctx.error(
                            f"BLASTN search failed or found no results for RID: {rid}."
                        )
                        return {
                            "query": sequence[:20] + "...",
                            "database": database,
                            "results": [],
                            "message": "BLASTN search failed or found no results.",
                        }
                    elif "Status=UNKNOWN" in status_text:
                        await ctx.error(f"BLASTN search status UNKNOWN for RID: {rid}.")
                        return {
                            "error": "BLASTN search status unknown.",
                            "details": f"RID: {rid}",
                        }
                await asyncio.sleep(poll_interval)
                await ctx.info(f"Polling BLASTN results for RID: {rid}...")
            except Exception as e:
                logger.warning(
                    f"Error polling BLASTN status for RID {rid}: {e}. Will retry."
                )
                await asyncio.sleep(poll_interval)

        if "Status=READY" not in status_text:
            await ctx.error(
                f"BLASTN results for RID {rid} did not become ready within timeout."
            )
            return {"error": "BLASTN search timed out.", "details": f"RID: {rid}"}

        # 3. Retrieve the results
        await ctx.info(f"Retrieving BLASTN results for RID: {rid}")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                results_response = await client.get(blast_url, params=results_params)
                results_response.raise_for_status()

                response_content_type = results_response.headers.get(
                    "Content-Type", "N/A"
                )
                logger.info(
                    f"BLASTN results response Content-Type for RID {rid}: {response_content_type}"
                )

                # Read raw bytes and attempt decoding, falling back to latin-1
                response_bytes = await results_response.aread()
                response_text_content = (
                    ""  # Initialize for the final json.JSONDecodeError catch block
                )
                try:
                    response_text_content = response_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    logger.warning(
                        f"UTF-8 decoding failed for BLASTN results (RID: {rid}). Attempting latin-1."
                    )
                    response_text_content = response_bytes.decode(
                        "latin-1", errors="replace"
                    )

                # Attempt to extract the main JSON object if there's leading/trailing garbage
                try:
                    first_brace = response_text_content.find("{")
                    last_brace = response_text_content.rfind("}")

                    if (
                        first_brace != -1
                        and last_brace != -1
                        and last_brace > first_brace
                    ):
                        json_payload_str = response_text_content[
                            first_brace : last_brace + 1
                        ]
                        try:
                            blast_data = json.loads(json_payload_str)
                            logger.debug(
                                f"Successfully parsed extracted JSON payload for BLASTN RID {rid}."
                            )
                        except json.JSONDecodeError as e_inner:
                            logger.warning(
                                f"Failed to parse extracted JSON substring for BLASTN RID {rid}: '{json_payload_str[:200]}...'. Error: {e_inner}. Will attempt to parse original content."
                            )
                            blast_data = json.loads(response_text_content)  # Fallback
                    else:
                        logger.debug(
                            f"Could not find clear {{...}} structure for BLASTN RID {rid}, attempting to parse original content."
                        )
                        blast_data = json.loads(response_text_content)
                except json.JSONDecodeError:
                    raise  # Re-raise to be caught by the outer handler

                hits = blast_data.get("Report", {}).get("Search", {}).get("hits", [])
                if not hits:
                    return {
                        "query": sequence[:20] + "...",
                        "database": database,
                        "results": [],
                        "message": "BLASTN search completed, but found no hits.",
                    }
                truncated_hits = []
                for hit in hits:
                    accession = hit.get("accession")
                    title = hit.get("description", [{}])[0].get("title", "N/A")
                    hsps = hit.get("hsps", [])
                    hsp_summary = None
                    if hsps:
                        best_hsp = hsps[0]
                        hsp_summary = {
                            "bit_score": best_hsp.get("bit_score"),
                            "score": best_hsp.get("score"),
                            "evalue": best_hsp.get("evalue"),
                            "identity_percent": (
                                best_hsp.get("identity", 0)
                                / best_hsp.get("align_len", 1)
                            )
                            * 100
                            if best_hsp.get("align_len", 1) > 0
                            else 0,
                            "query_from": best_hsp.get("query_from"),
                            "query_to": best_hsp.get("query_to"),
                            "hit_from": best_hsp.get("hit_from"),
                            "hit_to": best_hsp.get("hit_to"),
                            "align_len": best_hsp.get("align_len"),
                        }
                    truncated_hits.append(
                        {
                            "accession": accession,
                            "title": title,
                            "hsp_summary": hsp_summary,
                        }
                    )
                return {
                    "query": sequence[:20] + "...",
                    "database": database,
                    "results": truncated_hits,
                }
        except json.JSONDecodeError as e:
            error_message = f"Failed to parse JSON response from NCBI BLASTN for RID {rid}. Content (first 500 chars): '{response_text_content[:500]}'. Error: {e}"
            logger.error(
                error_message, exc_info=False
            )  # exc_info=False as we are logging the content
            await ctx.error("BLASTN results parsing error.")
            return {
                "error": "Invalid response format from NCBI BLASTN.",
                "details": str(e),
            }
        except Exception as e:  # Catch all other errors during results retrieval
            error_message = f"An unexpected error occurred during BLASTN results retrieval for RID {rid}: {e}"
            logger.error(error_message, exc_info=True)
            await ctx.error("BLASTN results retrieval failed.")
            return {
                "error": "An unexpected error occurred during BLASTN results retrieval.",
                "details": str(e),
            }

    logger.info("BLAST MCP tool registered.")
