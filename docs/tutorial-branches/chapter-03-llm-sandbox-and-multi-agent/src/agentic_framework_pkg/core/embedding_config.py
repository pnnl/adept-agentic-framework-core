"""Embedding model configuration for Chapter 03.

Supports the same priority order as the rest of the framework:
  1. Internal/local OpenAI-compatible provider  (INTERNAL_LLM_*)
  2. Azure OpenAI                               (EMBEDDING_AZURE_* or AZURE_*)
  3. OpenAI (direct)                            (default fallback)

This intentionally limits the provider list to packages already declared in
pyproject.toml (langchain-openai, langchain-core).  If you need Ollama or
Google Vertex AI embeddings, add the relevant optional deps and extend this file.
"""

import os
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings
from langchain_core.embeddings import Embeddings
from ..logger_config import get_logger

logger = get_logger(__name__)


def get_embedding_model() -> Embeddings:
    """Returns the embeddings instance to use, selected from environment config."""

    # 1. Internal / local OpenAI-compatible provider
    internal_key = os.getenv("INTERNAL_LLM_API_KEY")
    internal_base = os.getenv("INTERNAL_LLM_BASE_URL")
    internal_model = os.getenv("INTERNAL_LLM_EMBEDDING_MODEL")

    if internal_key and internal_base and internal_model:
        logger.info(
            f"Using internal LLM provider for embeddings: {internal_base} "
            f"with model {internal_model}"
        )
        return OpenAIEmbeddings(
            model=internal_model,
            api_key=internal_key,
            base_url=internal_base,
        )

    model_name = os.getenv("EMBEDDING_DEFAULT_MODEL", "text-embedding-3-small")
    logger.info(f"Attempting to load embedding model: {model_name}")

    # 2. Azure OpenAI
    azure_base = os.getenv("EMBEDDING_AZURE_API_BASE") or os.getenv("AZURE_API_BASE")
    azure_version = os.getenv("EMBEDDING_AZURE_API_VERSION") or os.getenv(
        "AZURE_API_VERSION"
    )
    azure_key = os.getenv("EMBEDDING_AZURE_API_KEY") or os.getenv("AZURE_API_KEY")

    if azure_base and azure_version and azure_key:
        azure_deployment = (
            model_name.split("/")[1] if model_name.startswith("azure/") else model_name
        )
        logger.info(
            f"Loading AzureOpenAIEmbeddings: deployment={azure_deployment}, "
            f"endpoint={azure_base}"
        )
        return AzureOpenAIEmbeddings(
            azure_deployment=azure_deployment,
            azure_endpoint=azure_base,
            api_version=azure_version,
            api_key=azure_key,
        )

    # 3. Default: OpenAI direct
    logger.info(f"Loading OpenAIEmbeddings: model={model_name}")
    return OpenAIEmbeddings(model=model_name)
