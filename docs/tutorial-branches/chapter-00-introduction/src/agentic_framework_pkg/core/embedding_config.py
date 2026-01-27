import os
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_core.embeddings import Embeddings
from .logger_config import get_logger

logger = get_logger(__name__)


def get_embedding_model() -> Embeddings:
    """Returns the llm instance to be used for embedding."""

    # Check for internal LLM provider first
    internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
    internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
    internal_llm_embedding_model = os.getenv("INTERNAL_LLM_EMBEDDING_MODEL")

    if internal_llm_api_key and internal_llm_base_url and internal_llm_embedding_model:
        logger.info(
            f"Using internal LLM provider for embeddings: {internal_llm_base_url} with model {internal_llm_embedding_model}"
        )
        return OpenAIEmbeddings(
            model=internal_llm_embedding_model,
            api_key=internal_llm_api_key,
            base_url=internal_llm_base_url,
        )

    model_name = os.getenv("EMBEDDING_DEFAULT_MODEL", "ollama/nomic-embed-text")
    logger.info(f"Attempting to load embedding model: {model_name}")

    if (
        model_name.startswith("azure/")
        or (
            os.getenv("EMBEDDING_AZURE_API_BASE")
            and os.getenv("EMBEDDING_AZURE_API_VERSION")
        )
        or (os.getenv("AZURE_API_BASE") and os.getenv("AZURE_API_VERSION"))
    ):
        # Prioritize embedding-specific Azure config, then general Azure config
        azure_base_url = os.getenv("EMBEDDING_AZURE_API_BASE") or os.getenv(
            "AZURE_API_BASE"
        )
        azure_api_version = os.getenv("EMBEDDING_AZURE_API_VERSION") or os.getenv(
            "AZURE_API_VERSION"
        )
        azure_api_key = os.getenv("EMBEDDING_AZURE_API_KEY") or os.getenv(
            "AZURE_API_KEY"
        )
        azure_deployment = (
            model_name.split("/")[1] if model_name.startswith("azure/") else model_name
        )

        if not azure_base_url or not azure_api_version or not azure_api_key:
            logger.warning(
                "Azure OpenAI Embeddings requested but EMBEDDING_AZURE_API_BASE/VERSION/KEY or AZURE_API_BASE/VERSION/KEY are not fully set. Falling back to OpenAIEmbeddings if applicable."
            )
            # Fall through to OpenAIEmbeddings if Azure config is incomplete
            logger.info(f"Loading OpenAIEmbeddings: model={model_name}")
            return OpenAIEmbeddings(model=model_name)

        # Check if the base URL already contains the deployment path
        if "/deployments/" in azure_base_url.lower():
            logger.info(
                f"Loading AzureOpenAIEmbeddings with full endpoint: {azure_base_url}"
            )
            return AzureOpenAIEmbeddings(
                azure_endpoint=azure_base_url,
                api_version=azure_api_version,
                api_key=azure_api_key,
            )
        else:
            logger.info(
                f"Loading AzureOpenAIEmbeddings: deployment={azure_deployment}, azure_endpoint={azure_base_url}, api_version={azure_api_version}"
            )
            return AzureOpenAIEmbeddings(
                azure_deployment=azure_deployment,
                azure_endpoint=azure_base_url,
                api_version=azure_api_version,
                api_key=azure_api_key,
            )

    elif model_name.startswith("ollama/"):
        ollama_model = model_name.split("/")[1]
        ollama_base_url = os.getenv("OLLAMA_API_BASE_URL")
        logger.info(
            f"Loading OllamaEmbeddings: model={ollama_model}, base_url={ollama_base_url}"
        )
        return OllamaEmbeddings(model=ollama_model, base_url=ollama_base_url)
    elif model_name.startswith("google/"):
        google_model = model_name.split("/")[1]
        google_project_id = os.getenv("GOOGLE_PROJECT_ID")
        google_location = os.getenv("GOOGLE_LOCATION")
        logger.info(
            f"Loading VertexAIEmbeddings: model={google_model}, project={google_project_id}, location={google_location}"
        )
        return VertexAIEmbeddings(
            model_name=google_model, project=google_project_id, location=google_location
        )
    else:
        logger.info(f"Loading OpenAIEmbeddings: model={model_name}")
        return OpenAIEmbeddings(model=model_name)
