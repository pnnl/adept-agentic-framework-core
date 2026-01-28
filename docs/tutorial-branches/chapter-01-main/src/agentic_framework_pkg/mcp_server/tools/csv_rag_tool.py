from fastmcp import FastMCP, Context
from ..state_manager import (
    get_session_context,
    update_session_context,
    # add_embeddings_batch,
    # query_embeddings,
    # delete_embeddings # Import if needed for cleanup later
)
from ...core.llm_agnostic_layer import LLMAgnosticClient, LLMServiceError
import pandas as pd
import json
import uuid
import os
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
import base64

import openpyxl  # For .xlsx
from docx import Document as DocxDocument  # For .docx
import fitz  # PyMuPDF for .pdf

# Use the centralized logger # Removed TextPart import
from ...logger_config import get_logger

# Import common session helpers
# Import the new VectorStoreManager
from ..vector_store_manager import VectorStoreManager

# Assuming general_tools.py is the source for now, or a future common_utils.py
import openai
from .general_tools import get_stable_session_id, ensure_session_initialized

logger = get_logger(__name__)

# This global instance will be set by the register_tools function.
# In a larger application, consider dependency injection.
_llm_client_instance: LLMAgnosticClient | None = None

# NVIDIA Configuration
NVIDIA_API_KEY_ENV_VAR = "NVIDIA_API_KEY"
NVIDIA_BASE_URL_ENV_VAR = "NVIDIA_API_BASE_URL"
NVIDIA_MULTI_MODAL_MODEL_ENV_VAR = "NVIDIA_MULTI_MODAL_MODEL_NAME"

_nvidia_api_key: Optional[str] = None
_nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"  # Default
_nvidia_model_name: str = "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"  # Default
_nvidia_async_client: Optional[openai.AsyncOpenAI] = None

IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


# cosine_similarity function is not used with ChromaDB, can be removed if not used elsewhere.
# def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
#     if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0: # Avoid division by zero
#         return 0.0
#     return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
TEXT_CHUNK_SIZE = 1000  # Characters per chunk for text documents
TEXT_CHUNK_OVERLAP = 100  # Overlap between chunks


def _read_csv_to_texts(file_path: str) -> List[str]:
    """Reads a CSV file and converts its rows to text strings."""
    df = pd.read_csv(file_path)
    texts = []
    for index, row in df.iterrows():
        text_content = ", ".join(
            f"{col}: {str(val)}" for col, val in row.astype(str).items()
        )
        if text_content.strip():
            texts.append(text_content)
    return texts


def _read_excel_to_texts(file_path: str) -> List[str]:
    """Reads an Excel file (all sheets) and converts its rows to text strings."""
    xls = pd.ExcelFile(file_path)
    texts = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        for index, row in df.iterrows():
            text_content = f"Sheet: {sheet_name}, Row: {index + 2}, " + ", ".join(
                f"{col}: {str(val)}" for col, val in row.astype(str).items()
            )
            if text_content.strip():
                texts.append(text_content)
    return texts


def _split_text_into_chunks(
    text: str, chunk_size: int, chunk_overlap: int
) -> List[str]:
    """Splits a long text into smaller overlapping chunks."""
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
        if start >= len(text) and end < len(
            text
        ):  # Ensure last part is captured if loop condition makes it skip
            chunks.append(text[start:])
            break
    return [chunk for chunk in chunks if chunk.strip()]


def _read_docx_to_texts(file_path: str) -> List[str]:
    """Reads a DOCX file and extracts its text content, then splits into chunks."""
    doc = DocxDocument(file_path)
    full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    return _split_text_into_chunks(full_text, TEXT_CHUNK_SIZE, TEXT_CHUNK_OVERLAP)


def _read_pdf_to_texts(file_path: str) -> List[str]:
    """Reads a PDF file, extracts text page by page, and splits into chunks."""
    texts = []
    try:
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
            pages_with_text = 0

            logger.debug(
                f"PDF '{file_path}' has {total_pages} pages. Starting text extraction..."
            )

            for page_num, page in enumerate(doc):
                # Try multiple extraction methods for better compatibility
                page_text = page.get_text("text")  # Explicit "text" mode

                # If standard extraction returns nothing, try "blocks" method
                if not page_text.strip():
                    blocks = page.get_text("blocks")
                    page_text = "\n".join(
                        [
                            block[4]
                            for block in blocks
                            if len(block) > 4 and isinstance(block[4], str)
                        ]
                    )

                if page_text.strip():
                    pages_with_text += 1
                    chunks = _split_text_into_chunks(
                        page_text, TEXT_CHUNK_SIZE, TEXT_CHUNK_OVERLAP
                    )
                    texts.extend(chunks)
                    logger.debug(
                        f"Page {page_num + 1}: Extracted {len(page_text)} characters -> {len(chunks)} chunks"
                    )
                else:
                    logger.debug(f"Page {page_num + 1}: No text extracted")

            logger.info(
                f"PDF '{file_path}': Extracted text from {pages_with_text}/{total_pages} pages, total {len(texts)} chunks"
            )

            if pages_with_text == 0 and total_pages > 0:
                logger.warning(
                    f"PDF '{file_path}' has {total_pages} pages but no extractable text. This might be a scanned/image-based PDF that requires OCR, or the PDF might use non-standard text encoding."
                )
            elif pages_with_text < total_pages:
                logger.info(
                    f"PDF '{file_path}': {total_pages - pages_with_text} pages had no extractable text."
                )

    except Exception as e:
        logger.error(f"Error reading PDF file {file_path}: {e}", exc_info=True)
        raise  # Re-raise to be caught by the caller

    return texts


# Placeholder for other readers - you would implement these similarly:


def _read_txt_to_texts(file_path: str) -> List[str]:
    """Reads a plain text file and splits its content into chunks."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()
    return _split_text_into_chunks(full_text, TEXT_CHUNK_SIZE, TEXT_CHUNK_OVERLAP)


def _read_latex_to_texts(file_path: str) -> List[str]:
    """Reads a LaTeX (.tex) file and splits its raw content into chunks.
    Note: This is a basic reader and will include LaTeX commands. More sophisticated parsing may be needed for cleaner text."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()
    # A very basic attempt to remove some common inline math and simple commands - can be expanded
    # full_text = re.sub(r'\\[a-zA-Z]+(\{[^}]*\})?|[$].*?[$]', '', full_text)
    return _split_text_into_chunks(full_text, TEXT_CHUNK_SIZE, TEXT_CHUNK_OVERLAP)


# def _read_pptx_to_texts(file_path: str) -> List[str]:
#     from pptx import Presentation
#     prs = Presentation(file_path)
#     full_text = ""
#     for slide in prs.slides:
#         for shape in slide.shapes:
#             if hasattr(shape, "text"):
#                 full_text += shape.text + "\n"
#     return _split_text_into_chunks(full_text, TEXT_CHUNK_SIZE, TEXT_CHUNK_OVERLAP)

# def _read_odt_to_texts(file_path: str) -> List[str]:
#     from odf.opendocument import load as load_odf
#     from odf import text as odf_text, teletype as odf_teletype
#     doc = load_odf(file_path)
#     texts = []
#     for element in doc.getElementsByType(odf_text.P):
#         texts.append(odf_teletype.extractText(element))
#     full_text = "\n".join(texts)
#     return _split_text_into_chunks(full_text, TEXT_CHUNK_SIZE, TEXT_CHUNK_OVERLAP)


async def _extract_text_from_image_content_with_nvidia(
    image_bytes: bytes,
    image_mime_type: str,  # e.g., "image/png", "image/jpeg"
    prompt_text: str,
) -> str:
    """
    Sends image data and a prompt to the configured NVIDIA multi-modal model
    and returns the extracted text.
    """
    if not _nvidia_async_client:
        logger.error("NVIDIA client not initialized. Cannot process image content.")
        raise LLMServiceError("NVIDIA client not initialized.")

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_mime_type};base64,{base64_image}"
                    },
                },
            ],
        }
    ]

    try:
        logger.debug(
            f"Sending request to NVIDIA model {_nvidia_model_name} for image analysis. Prompt: {prompt_text[:50]}..."
        )
        completion = await _nvidia_async_client.chat.completions.create(
            model=_nvidia_model_name,
            messages=messages,
            temperature=0.2,  # Lower temp for more factual extraction
            top_p=0.7,
            max_tokens=2048,  # Increased for potentially long text from pages
            stream=False,
        )
        if (
            completion.choices
            and completion.choices[0].message
            and completion.choices[0].message.content
        ):
            extracted_text = completion.choices[0].message.content
            logger.debug(
                f"NVIDIA model returned content of length {len(extracted_text)} for prompt '{prompt_text[:50]}...'."
            )
            return extracted_text
        else:
            logger.warning(
                f"NVIDIA model returned no content or unexpected response structure for prompt '{prompt_text[:50]}...'."
            )
            return ""
    except Exception as e:
        # Catching general exception from openai client (APIConnectionError, RateLimitError, APIStatusError, etc.)
        logger.error(
            f"NVIDIA API call failed for prompt '{prompt_text[:50]}...': {type(e).__name__} - {e}",
            exc_info=True,
        )
        raise LLMServiceError(f"NVIDIA API call failed: {type(e).__name__} - {e}")


async def process_uploaded_file(
    file_path_on_server: str,
    original_filename: str,
    ctx: Context,
    mcp_session_id: str = None,
) -> Dict[str, Any]:
    """
    Processes an uploaded file (CSV, XLSX, DOCX) from a shared server path,
    generates embeddings for its content, and stores them for RAG.
    and stores them for RAG. Returns a file_id for querying.
    The file_path_on_server must be accessible by the MCP server (e.g., via a shared Docker volume).
    """
    logger.info(
        f"Received request to process file: {original_filename} at path: {file_path_on_server}"
    )
    if not _llm_client_instance:
        await ctx.error(
            "LLM client not initialized for CSV RAG tool."
        )  # Removed TextPart wrapper
        return {"error": "Internal server error: LLM client not available."}

    logger.debug(f"Processing file: {original_filename} at path: {file_path_on_server}")
    session_id = await ensure_session_initialized(ctx)  # Use common helper
    await ctx.info(
        f"Session {session_id}: Processing '{original_filename}' from path: {file_path_on_server}"
    )

    logger.debug(f"Ensuring session {session_id} is initialized for file processing")
    if not os.path.exists(file_path_on_server):
        await ctx.error(f"File not found at server path: {file_path_on_server}")
        return {"error": f"File not found on server: {original_filename}"}

    file_extension = Path(original_filename).suffix.lower()
    texts_to_embed: List[str] = []
    nvidia_processing_attempted = False
    nvidia_processing_successful = False

    try:
        if file_extension == ".csv":
            texts_to_embed = _read_csv_to_texts(file_path_on_server)
        elif file_extension == ".xlsx":
            texts_to_embed = _read_excel_to_texts(file_path_on_server)
        elif file_extension == ".pdf" and _nvidia_async_client:
            nvidia_processing_attempted = True
            all_pdf_text_from_nvidia = ""
            num_pages_processed_successfully = 0
            try:
                pdf_doc = fitz.open(file_path_on_server)
                for page_num in range(len(pdf_doc)):
                    page = pdf_doc.load_page(page_num)
                    # Render page to PNG image bytes
                    pix = page.get_pixmap(dpi=150)  # Use a reasonable DPI
                    img_bytes = pix.tobytes("png")
                    prompt = "Extract all text content from this document page."
                    try:
                        page_text = await _extract_text_from_image_content_with_nvidia(
                            img_bytes, "image/png", prompt
                        )
                        all_pdf_text_from_nvidia += page_text + "\n"
                        num_pages_processed_successfully += 1
                    except LLMServiceError as e:  # Catch errors from NVIDIA call
                        logger.warning(
                            f"NVIDIA model failed to process page {page_num + 1} of PDF '{original_filename}': {e}"
                        )
                    except (
                        Exception
                    ) as e:  # Catch other unexpected errors during page processing
                        logger.error(
                            f"Unexpected error processing page {page_num + 1} of PDF '{original_filename}' with NVIDIA: {e}",
                            exc_info=True,
                        )

                if num_pages_processed_successfully > 0:
                    texts_to_embed = _split_text_into_chunks(
                        all_pdf_text_from_nvidia, TEXT_CHUNK_SIZE, TEXT_CHUNK_OVERLAP
                    )
                    nvidia_processing_successful = True
                    logger.info(
                        f"Successfully processed {num_pages_processed_successfully}/{len(pdf_doc)} pages of PDF '{original_filename}' using NVIDIA model."
                    )
                else:  # NVIDIA failed for all pages or PDF was empty
                    logger.warning(
                        f"NVIDIA processing yielded no text for PDF '{original_filename}'."
                    )

            except Exception as e:  # Catch errors opening PDF or during loop
                logger.error(
                    f"Error during NVIDIA-based PDF processing for '{original_filename}': {e}",
                    exc_info=True,
                )

            if (
                not nvidia_processing_successful
            ):  # Fallback if NVIDIA processing failed or yielded no text
                logger.info(
                    f"Falling back to standard PyMuPDF text extraction for PDF '{original_filename}'."
                )
                texts_to_embed = _read_pdf_to_texts(file_path_on_server)

        elif (
            file_extension == ".pdf"
        ):  # Standard PDF processing if NVIDIA client not available
            texts_to_embed = _read_pdf_to_texts(file_path_on_server)
        elif file_extension in IMAGE_MIME_TYPES and _nvidia_async_client:
            nvidia_processing_attempted = True
            try:
                with open(file_path_on_server, "rb") as f:
                    img_bytes = f.read()
                mime_type = IMAGE_MIME_TYPES[file_extension]
                prompt = (
                    "Describe this image and extract all text content visible in it."
                )
                extracted_text = await _extract_text_from_image_content_with_nvidia(
                    img_bytes, mime_type, prompt
                )
                texts_to_embed = _split_text_into_chunks(
                    extracted_text, TEXT_CHUNK_SIZE, TEXT_CHUNK_OVERLAP
                )
                nvidia_processing_successful = True
                logger.info(
                    f"Successfully processed image '{original_filename}' using NVIDIA model."
                )
            except LLMServiceError as e:
                logger.error(
                    f"NVIDIA model failed to process image '{original_filename}': {e}. No text extracted."
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error processing image '{original_filename}' with NVIDIA: {e}",
                    exc_info=True,
                )

        elif file_extension == ".docx":
            texts_to_embed = _read_docx_to_texts(file_path_on_server)
        elif file_extension == ".txt":
            texts_to_embed = _read_txt_to_texts(file_path_on_server)
        elif file_extension == ".tex":
            texts_to_embed = _read_latex_to_texts(file_path_on_server)
        else:
            await ctx.warning(f"Unsupported file type: {original_filename}")
            return {
                "error": f"Unsupported file type: {file_extension}. Supported types: .csv, .xlsx, .docx, .pdf, .txt, .tex, {', '.join(IMAGE_MIME_TYPES.keys())}"
            }
    except Exception as e:  # Catch exceptions from the reading functions
        logger.error(
            f"Failed to read/process file {original_filename}: {e}", exc_info=True
        )
        await ctx.error(f"Failed to read or process file '{original_filename}': {e}")
        return {"error": f"Failed to read or process file: {e}"}

    if not texts_to_embed:
        logger.info(f"No text content extracted from {original_filename}.")

        # Provide specific guidance based on file type
        if file_extension == ".pdf":
            error_msg = f"No text content could be extracted from {original_filename}. "
            if nvidia_processing_attempted and not nvidia_processing_successful:
                error_msg += "This PDF may be scanned/image-based. NVIDIA OCR processing failed. Try converting it to a text-based PDF or use a different OCR tool."
            else:
                error_msg += "This PDF appears to be scanned/image-based (no extractable text layer). To process it, you need OCR capabilities. Consider: 1) Converting the PDF to a text-based format, 2) Using a PDF with embedded text, or 3) Configuring NVIDIA API credentials for OCR processing."
        else:
            error_msg = f"No text content could be extracted from {original_filename}. File might be empty or not parsable."

        await ctx.info(error_msg)
        return {"error": error_msg}

    logger.debug(
        f"File {original_filename} read successfully, extracted {len(texts_to_embed)} text segments for embedding."
    )
    file_id = str(uuid.uuid4())
    total_segments = len(texts_to_embed)
    processed_segments = 0
    # For FastMCP, ctx.report_progress is not standard. Use ctx.info or similar.

    # Batch texts for embedding to be more efficient
    vsm = VectorStoreManager()  # Get the singleton instance of VectorStoreManager

    # Collection name for ChromaDB, unique per file and session
    # This file_id is generated for this specific processing instance.
    collection_name = f"{session_id}_{file_id}"

    current_batch_texts: List[str] = []
    # original_indices for tabular data might need adjustment if mixing with chunked text.
    # For now, metadata will just store segment index.

    logger.debug(
        f"Processing {total_segments} text segments from {original_filename} for embedding"
    )
    processing_method = (
        "NVIDIA"
        if nvidia_processing_attempted and nvidia_processing_successful
        else "standard"
    )
    await ctx.info(
        f"Session {session_id}: Starting embedding for '{original_filename}' "
        f"({total_segments} text segments, processed via {processing_method} method)."
    )

    for i, text_segment in enumerate(texts_to_embed):
        current_batch_texts.append(text_segment)

        # Embed in batches of 50 or if it's the last segment
        if len(current_batch_texts) >= 50 or (
            i == total_segments - 1 and current_batch_texts
        ):
            try:
                # Let LLMAgnosticClient use its default embedding model
                logger.debug(
                    f"Embedding chunk for {original_filename}: {len(current_batch_texts)} segments"
                )
                chunk_embeddings = await _llm_client_instance.acreate_embedding(
                    input_texts=current_batch_texts
                )

                # Prepare data for VectorStoreManager.add_documents
                ids_for_vsm = []
                docs_for_vsm = []
                embeddings_for_vsm = []
                metadatas_for_vsm = []

                for batch_idx, emb_vector in enumerate(chunk_embeddings):
                    doc_id = str(uuid.uuid4())
                    ids_for_vsm.append(doc_id)
                    docs_for_vsm.append(current_batch_texts[batch_idx])
                    embeddings_for_vsm.append(emb_vector)
                    metadatas_for_vsm.append(
                        {
                            "file_id": file_id,
                            "session_id": session_id,
                            "segment_index": processed_segments
                            + batch_idx,  # Overall segment index
                            "original_filename": original_filename,
                        }
                    )
                # Use VectorStoreManager to add documents
                vsm.add_documents(
                    collection_name=collection_name,
                    documents=docs_for_vsm,
                    embeddings=embeddings_for_vsm,
                    metadatas=metadatas_for_vsm,
                    ids=ids_for_vsm,
                )
                logger.debug(
                    f"Successfully embedded {len(current_batch_texts)} segments for {original_filename}."
                )
                # Update processed segments count
                processed_segments += len(current_batch_texts)
                await ctx.info(
                    f"Session {session_id}: Embedded {processed_segments}/{total_segments} segments for '{original_filename}'."
                )
            except LLMServiceError as e:
                logger.error(
                    f"Failed to embed chunk for {original_filename}: {e}", exc_info=True
                )
                await ctx.error(
                    f"Failed to embed a chunk of segments for '{original_filename}': {e}. Skipping chunk."
                )
            except Exception as e:  # Catch any other unexpected error during embedding
                logger.error(
                    f"Unexpected error embedding chunk for {original_filename}: {e}",
                    exc_info=True,
                )
                await ctx.warning(
                    f"Unexpected error embedding a chunk for '{original_filename}': {e}. Skipping chunk."
                )
            finally:
                current_batch_texts = []

    logger.info(
        f"Total segments processed for {original_filename}: {processed_segments} out of {total_segments}"
    )

    logger.info(
        f"Successfully stored embeddings for {original_filename} with file_id: {file_id}"
    )
    session_context = await get_session_context(session_id)
    uploaded_files_info = session_context.get("uploaded_csv_files", {})
    uploaded_files_info[file_id] = {
        "original_filename": original_filename,
        "segment_count": processed_segments,  # Store actual processed segments
        "collection_name": collection_name,  # Store the ChromaDB collection name
        "status": "indexed",
    }
    session_context["uploaded_csv_files"] = uploaded_files_info
    await update_session_context(session_id, session_context)

    logger.debug(
        f"Updated session context for session {session_id} with file_id: {file_id} (processed via {processing_method})"
    )

    try:
        os.remove(file_path_on_server)  # Clean up the file from shared volume
        await ctx.info(
            f"Removed temporary file from shared volume: {file_path_on_server}"
        )
    except OSError as e:
        logger.warning(
            f"Could not remove file {file_path_on_server} from shared volume: {e}"
        )

    logger.info(
        f"File {original_filename} processed and indexed successfully with file_id: {file_id}"
    )
    await ctx.info(
        f"Session {session_id}: Successfully processed and indexed '{original_filename}' "
        f"(using {processing_method} method) as file_id: {file_id}"
    )
    # Return collection_name as well, might be useful for direct VSM queries if needed
    return {
        "file_id": file_id,
        "original_filename": original_filename,
        "collection_name": collection_name,
        "message": "File processed and indexed.",
    }


async def query_file_content(
    user_query: str,
    file_id: str,
    ctx: Context,
    top_k: int = 3,
    mcp_session_id: str = None,
) -> str:
    """
    Queries the indexed file content using RAG. Requires a 'file_id' obtained from
    'process_uploaded_file' and a 'user_query'.

    Note that 'mcp_session_id' is optional and can be used to specify a session ID.
    Returns the LLM-generated answer as a string.
    """
    logger.info(
        f"Received query for file content: file_id={file_id}, query='{user_query}'"
    )
    if not _llm_client_instance:
        await ctx.error("LLM client not initialized for RAG tool.")
        return "Error: Internal server error - LLM client not available."  # Return plain string for error message

    session_id = await ensure_session_initialized(ctx)  # Use common helper
    await ctx.info(
        f"Session {session_id}: Querying file (file_id: {file_id}) with query: '{user_query}'"
    )

    session_context = await get_session_context(session_id)
    uploaded_file_info = session_context.get("uploaded_csv_files", {}).get(file_id)
    if not uploaded_file_info:
        await ctx.error(
            f"Invalid or unknown file_id: {file_id} for this session."
        )  # Removed TextPart wrapper
        return (
            f"Error: File ID {file_id} not found or not associated with this session."
        )

    collection_name = uploaded_file_info.get("collection_name")
    if not collection_name:
        return f"Error: Collection name not found for file_id {file_id}. The file might not have been processed correctly with the new vector store."

    await ctx.info(
        f"Session {session_id}: Generating query embedding for: '{user_query}'"
    )
    try:
        # Let LLMAgnosticClient use its default embedding model
        query_embedding_list = await _llm_client_instance.acreate_embedding(
            input_texts=[user_query]
        )
        if not query_embedding_list:
            logger.error(
                f"Embedding service returned no embedding for query: {user_query}"
            )
            await ctx.error("Failed to get embedding for the user query.")
            return "Error: Could not process query due to embedding failure (empty result)."
        query_vector = query_embedding_list[0]  # This is List[float]
    except LLMServiceError as e:
        logger.error(f"Failed to embed user query '{user_query}': {e}", exc_info=True)
        await ctx.error(f"Failed to embed user query: {e}")
        return f"Error: Could not process query due to embedding failure: {e}."

    await ctx.info(
        f"Session {session_id}: Searching relevant chunks for file_id {file_id}"
    )
    relevant_chunks_texts: List[str] = []

    vsm = VectorStoreManager()

    try:
        # Query using VectorStoreManager
        chroma_results = vsm.query_collection(
            collection_name=collection_name,
            query_embeddings=[query_vector],  # Corrected keyword argument
            n_results=top_k,
            # include=["documents"] # We only need the document text for the context
        )
        if (
            chroma_results
            and chroma_results.get("documents")
            and chroma_results["documents"][0]
        ):
            relevant_chunks_texts = chroma_results["documents"][0]
        else:
            logger.info(
                f"No relevant chunks found in ChromaDB for file_id {file_id}, session {session_id} and query."
            )
    except Exception as e:
        logger.error(
            f"Error querying ChromaDB for file_id {file_id}, session {session_id}: {e}",
            exc_info=True,
        )
        await ctx.error(
            f"Error retrieving data from vector store for collection '{collection_name}': {e}"
        )
        return f"Error: Could not retrieve relevant data: {e}."

    if not relevant_chunks_texts:
        await ctx.info(
            "No relevant chunks found for the query after similarity search."
        )
        return "Could not find sufficiently relevant information in the indexed file to answer your query."

    await ctx.info(
        f"Session {session_id}: Constructing prompt for LLM with {len(relevant_chunks_texts)} chunks."
    )

    context_str = "\n\n".join(relevant_chunks_texts)
    original_filename_for_prompt = session_context["uploaded_csv_files"][file_id].get(
        "original_filename", "the document"
    )
    system_prompt = (
        "You are a helpful AI assistant. Based on the following context from a processed file, "
        "answer the user's query. If the context does not contain the answer, "
        "say that you cannot find the answer in the provided data."
    )
    user_prompt_content = (
        f"Context from processed file:\n{context_str}\n\nUser Query: {user_query}"
    )

    prompt_messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_content},
    ]

    await ctx.info(f"Session {session_id}: Generating answer with LLM.")
    try:
        llm_response = await _llm_client_instance.agenerate_response(
            llm_purpose="rag",  # Let LLMAgnosticClient use its default RAG model
            messages=prompt_messages,
            stream=False,  # Get full response for RAG,
            # Consider adding temperature or other params if needed
        )
        answer = (
            llm_response.choices[0].message.content
            if llm_response.choices and llm_response.choices[0].message
            else "LLM did not provide an answer."
        )
    except LLMServiceError as e:
        logger.error(f"LLM failed to generate RAG answer: {e}", exc_info=True)
        await ctx.error(f"LLM failed to generate answer: {e}")
        return f"Error: LLM failed to generate an answer: {e}."

    await ctx.info(
        f"Session {session_id}: Successfully generated RAG answer for file_id: {file_id}"
    )
    return str(answer)


def _initialize_nvidia_client():
    """Initializes the NVIDIA AsyncOpenAI client from environment variables."""
    global _nvidia_api_key, _nvidia_base_url, _nvidia_model_name, _nvidia_async_client
    _nvidia_api_key = os.getenv(NVIDIA_API_KEY_ENV_VAR)
    _nvidia_base_url = os.getenv(
        NVIDIA_BASE_URL_ENV_VAR, _nvidia_base_url
    )  # Use default if not set
    _nvidia_model_name = os.getenv(
        NVIDIA_MULTI_MODAL_MODEL_ENV_VAR, _nvidia_model_name
    )  # Use default if not set

    if _nvidia_api_key:
        try:
            _nvidia_async_client = openai.AsyncOpenAI(
                base_url=_nvidia_base_url,
                api_key=_nvidia_api_key,
            )
            logger.info(
                f"NVIDIA AsyncOpenAI client initialized for model '{_nvidia_model_name}' at base URL '{_nvidia_base_url}'."
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize NVIDIA AsyncOpenAI client: {e}", exc_info=True
            )
            _nvidia_async_client = None  # Ensure it's None if init fails
    else:
        logger.info(
            f"'{NVIDIA_API_KEY_ENV_VAR}' not set. NVIDIA multi-modal document analysis will be unavailable."
        )


def register_tools(mcp: FastMCP, llm_client: LLMAgnosticClient):
    """Registers the File RAG tools with the FastMCP instance."""
    global _llm_client_instance
    _llm_client_instance = llm_client
    _initialize_nvidia_client()  # Initialize NVIDIA client

    logger.info(
        "File RAG Tool configured to use LLMAgnosticClient defaults for embedding and RAG."
    )
    mcp.tool()(process_uploaded_file)
    mcp.tool()(query_file_content)

    logger.info("File RAG MCP tools registered.")
