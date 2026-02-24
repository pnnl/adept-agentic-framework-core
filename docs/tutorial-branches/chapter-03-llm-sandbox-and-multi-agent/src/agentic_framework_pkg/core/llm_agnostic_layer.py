import litellm
import os
from typing import List, Dict, Any, AsyncGenerator, Optional
import base64  # For NVIDIA image processing
import openai  # For direct Azure OpenAI SDK usage
from openai import (
    AsyncAzureOpenAI,
    APIError as OpenAI_APIError,
    AuthenticationError as OpenAI_AuthenticationError,
    RateLimitError as OpenAI_RateLimitError,
    BadRequestError as OpenAI_BadRequestError,
    NotFoundError as OpenAI_NotFoundError,
    APIConnectionError as OpenAI_APIConnectionError,
    APITimeoutError as OpenAI_APITimeoutError,
)
from langchain_core.language_models.chat_models import BaseChatModel

# Use the centralized logger from logger_config.py
from ..logger_config import get_logger

logger = get_logger(__name__)
litellm.set_verbose = os.getenv("LITELLM_VERBOSE", "False").lower() == "true"

# Turn on LiteLLM's debug mode if the environment variable is set
litellm._turn_on_debug()

# NVIDIA Configuration Constants (using generic names for client setup)
NVIDIA_API_KEY_ENV_VAR = "NVIDIA_API_KEY"  # Expects a general NVIDIA API key
NVIDIA_BASE_URL_ENV_VAR = "NVIDIA_API_BASE_URL"
NVIDIA_MULTI_MODAL_MODEL_ENV_VAR = (
    "NVIDIA_MULTI_MODAL_MODEL_NAME"  # Default vision model
)
DEFAULT_NVIDIA_VISION_MODEL = "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"

# Dictionary to specify parameters that should be omitted for certain model_name values
# when calling Langchain constructors. This helps prevent API errors for unsupported params.
# The key is the model_name (e.g., Azure deployment name, or the value of LANGCHAIN_LLM_MODEL),
# value is a list of param names (e.g., ["temperature"]).
MODEL_SPECIFIC_PARAMS_TO_OMIT: Dict[str, List[str]] = {
    # Example: "my-azure-deployment-name": ["temperature"],
    # "o3-mini": ["temperature", "top_p", "frequency_penalty", "presence_penalty"],
}


class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""

    pass


class LLMAgnosticClient:
    """
    A client for interacting with various LLMs in an agnostic manner using LiteLLM.
    """

    OPENAI_COMPLETION_PARAMS = {
        "temperature",
        "max_tokens",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "stop",
        "tools",
        "tool_choice",
        "response_format",
        "seed",
        "logprobs",
        "top_logprobs",
        "user",
    }
    OPENAI_EMBEDDING_PARAMS = {"dimensions", "encoding_format", "user"}

    AZURE_DEPLOYMENT_URL_PART = "/openai/deployments/"

    DEFAULT_MODEL_ENV_VARS = {
        "streamlit": "STREAMLIT_DEFAULT_MODEL",
        "embedding": "EMBEDDING_DEFAULT_MODEL",
        "rag": "RAG_DEFAULT_MODEL",
        "generic": "DEFAULT_LLM_MODEL",  # A general fallback
    }

    def __init__(self):  # Combined __init__
        self.default_models = {
            purpose: os.getenv(env_var_name)
            for purpose, env_var_name in self.DEFAULT_MODEL_ENV_VARS.items()
        }
        # NVIDIA Client Initialization
        self._nvidia_api_key = os.getenv(NVIDIA_API_KEY_ENV_VAR)
        self._nvidia_base_url = os.getenv(
            NVIDIA_BASE_URL_ENV_VAR, "https://integrate.api.nvidia.com/v1"
        )
        self._nvidia_default_vision_model = os.getenv(
            NVIDIA_MULTI_MODAL_MODEL_ENV_VAR, DEFAULT_NVIDIA_VISION_MODEL
        )
        self._nvidia_async_client: Optional[openai.AsyncOpenAI] = None
        self.is_nvidia_client_available = False

        self._initialize_nvidia_client()  # Call initialization method

    def _parse_azure_root_endpoint(self, api_base: str) -> str:
        """Extracts the root Azure endpoint from a potentially deployment-specific URL."""
        if self.AZURE_DEPLOYMENT_URL_PART in api_base:
            return api_base.split(self.AZURE_DEPLOYMENT_URL_PART)[0]
        return api_base  # Assume it's already the root endpoint

    async def _call_azure_sdk_acompletion(
        self,
        model_deployment_name: str,
        api_key: str,
        api_base: str,
        api_version: str,
        messages: List[Dict[str, str]],
        stream: bool,
        **kwargs: Any,
    ) -> Any:
        azure_root_endpoint = self._parse_azure_root_endpoint(api_base)
        logger.debug(
            f"Calling Azure SDK acompletion. Deployment: {model_deployment_name}, Endpoint: {azure_root_endpoint}, Version: {api_version}"
        )
        try:
            client = AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=azure_root_endpoint,
                api_version=api_version,
            )
            sdk_kwargs = {
                k: v for k, v in kwargs.items() if k in self.OPENAI_COMPLETION_PARAMS
            }
            response = await client.chat.completions.create(
                model=model_deployment_name,
                messages=messages,
                stream=stream,
                **sdk_kwargs,
            )
            await client.close()
            return response
        except (
            OpenAI_APIError,
            OpenAI_AuthenticationError,
            OpenAI_RateLimitError,
            OpenAI_BadRequestError,
            OpenAI_NotFoundError,
            OpenAI_APIConnectionError,
            OpenAI_APITimeoutError,
        ) as e:
            logger.error(
                f"Azure SDK acompletion error for deployment {model_deployment_name}: {e}",
                exc_info=True,
            )
            raise LLMServiceError(
                f"Azure SDK error for deployment {model_deployment_name}: {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected Azure SDK acompletion error for deployment {model_deployment_name}: {e}",
                exc_info=True,
            )
            raise LLMServiceError(
                f"Unexpected Azure SDK error for deployment {model_deployment_name}: {e}"
            ) from e

    async def _call_azure_sdk_aembedding(
        self,
        model_deployment_name: str,
        api_key: str,
        api_base: str,
        api_version: str,
        input_texts: List[str],
        **kwargs: Any,
    ) -> List[List[float]]:
        azure_root_endpoint = self._parse_azure_root_endpoint(api_base)
        logger.debug(
            f"Calling Azure SDK aembedding. Deployment: {model_deployment_name}, Endpoint: {azure_root_endpoint}, Version: {api_version}"
        )
        try:
            client = AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=azure_root_endpoint,
                api_version=api_version,
            )
            sdk_kwargs = {
                k: v for k, v in kwargs.items() if k in self.OPENAI_EMBEDDING_PARAMS
            }
            response = await client.embeddings.create(
                model=model_deployment_name, input=input_texts, **sdk_kwargs
            )
            await client.close()
            # Transform OpenAI Embedding object to List[List[float]]
            return [item.embedding for item in response.data]
        except (
            OpenAI_APIError,
            OpenAI_AuthenticationError,
            OpenAI_RateLimitError,
            OpenAI_BadRequestError,
            OpenAI_NotFoundError,
            OpenAI_APIConnectionError,
            OpenAI_APITimeoutError,
        ) as e:
            logger.error(
                f"Azure SDK aembedding error for deployment {model_deployment_name}: {e}",
                exc_info=True,
            )
            raise LLMServiceError(
                f"Azure SDK error for deployment {model_deployment_name}: {e}"
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected Azure SDK aembedding error for deployment {model_deployment_name}: {e}",
                exc_info=True,
            )
            raise LLMServiceError(
                f"Unexpected Azure SDK error for deployment {model_deployment_name}: {e}"
            ) from e

    async def _call_litellm(
        self, method_name: str, model: str, llm_purpose: str, **kwargs: Any
    ) -> Any:
        """
        Private helper to make calls to LiteLLM, centralizing credential and endpoint logic.
        """
        # Pop explicit credentials from kwargs first
        # These will take precedence if provided by the caller directly.
        explicit_api_key = kwargs.pop("api_key", None)
        explicit_api_base = kwargs.pop("api_base", None)
        explicit_api_version = kwargs.pop("api_version", None)  # For Azure

        # ============================================================================
        # PRIORITY 1: Check for internal LLM provider FIRST (before all other providers)
        # ============================================================================
        internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
        internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
        internal_llm_model = os.getenv("INTERNAL_LLM_MODEL")
        internal_llm_embedding_model = os.getenv("INTERNAL_LLM_EMBEDDING_MODEL")

        # If all required internal LLM vars are set, use internal LLM with highest priority
        if internal_llm_api_key and internal_llm_base_url:
            logger.info(
                f"Using internal LLM provider: {internal_llm_base_url} (purpose: {llm_purpose})"
            )

            # Override model for embeddings if embedding model is specified
            if method_name == "aembedding" and internal_llm_embedding_model:
                model = internal_llm_embedding_model
                logger.info(f"Using internal embedding model: {model}")
            elif internal_llm_model:
                model = internal_llm_model
                logger.info(f"Using internal chat model: {model}")

            # LiteLLM requires openai/ prefix for custom base URLs
            if not model.startswith("openai/"):
                model = f"openai/{model}"

            # Call LiteLLM with internal provider config
            try:
                litellm_params = {
                    "model": model,
                    "api_key": internal_llm_api_key,
                    "api_base": internal_llm_base_url,
                }
                litellm_params.update(kwargs)

                log_params = {k: v for k, v in litellm_params.items() if k != "api_key"}
                logger.debug(
                    f"Calling LiteLLM method: {method_name} with internal LLM. Params (key excluded): {log_params}"
                )

                if method_name == "acompletion":
                    return await litellm.acompletion(**litellm_params)
                elif method_name == "aembedding":
                    return await litellm.aembedding(**litellm_params)
                else:
                    raise ValueError(f"Unsupported LiteLLM method: {method_name}")
            except Exception as e:
                logger.error(f"Internal LLM call failed: {e}", exc_info=True)
                raise LLMServiceError(f"Internal LLM error: {e}") from e

        # ============================================================================
        # Continue with existing provider logic (Azure, OpenAI, Ollama, etc.)
        # ============================================================================

        # Helper to get env vars: tries PURPOSE_SPECIFIC_VAR, then GENERIC_VAR
        def get_env_config(base_var_name: str, purpose: str) -> str | None:
            val = os.getenv(f"{purpose.upper()}_{base_var_name}")
            if val:
                return val
            return os.getenv(base_var_name)

        # Fetch purpose-aware environment variables
        azure_env_api_key = get_env_config("AZURE_API_KEY", llm_purpose)
        azure_env_api_base = get_env_config(
            "AZURE_API_BASE", llm_purpose
        )  # Should be like https://YOUR_RESOURCE_NAME.openai.azure.com/
        azure_env_api_version = get_env_config("AZURE_API_VERSION", llm_purpose)

        openai_env_api_key = get_env_config("OPENAI_API_KEY", llm_purpose)
        # openai_env_api_base = get_env_config("OPENAI_API_BASE", llm_purpose) # If needed for OpenAI proxies

        ollama_env_api_base = get_env_config("OLLAMA_API_BASE", llm_purpose)

        # Determine final credentials and endpoint
        final_api_key = explicit_api_key
        final_api_base = explicit_api_base
        final_api_version = explicit_api_version

        config_source_log = (
            f"explicit_kwargs (purpose: {llm_purpose})"  # Base assumption
        )

        # Prioritize Azure if its environment variables are fully set and no explicit conflicting base is given
        if azure_env_api_key and azure_env_api_base and azure_env_api_version:
            logger.debug(
                f"Using Azure environment variables for purpose '{llm_purpose}': api_key, api_base, api_version."
            )
            all_explicit_were_none_for_azure = (
                explicit_api_key is None
                and explicit_api_base is None
                and explicit_api_version is None
            )
            if final_api_key is None:
                final_api_key = azure_env_api_key
            if final_api_base is None:
                final_api_base = azure_env_api_base
            if final_api_version is None:
                final_api_version = azure_env_api_version
            if all_explicit_were_none_for_azure:
                config_source_log = f"azure_env (purpose: {llm_purpose})"

        elif (
            openai_env_api_key and final_api_key is None and final_api_base is None
        ):  # Check final_api_base to ensure Azure or explicit base didn't set it
            logger.debug(
                f"Using OpenAI environment variables for purpose '{llm_purpose}': api_key."
            )
            # Fallback to OpenAI if Azure is not fully configured and no explicit base suggests another provider
            final_api_key = openai_env_api_key
            # if openai_env_api_base and final_api_base is None: final_api_base = openai_env_api_base # If supporting OPENAI_API_BASE
            config_source_log = f"openai_env (purpose: {llm_purpose})"  # This implies no explicit and no Azure took precedence for key/base

        # Handle Ollama if model indicates it and no other base is set
        if model.startswith("ollama/") and final_api_base is None:
            logger.debug(
                f"Using Ollama environment variables for purpose '{llm_purpose}': api_base."
            )
            final_api_base = ollama_env_api_base or "http://localhost:11434"
            # Update config_source_log only if it wasn't set by a higher priority source for the base
            if (
                config_source_log == f"explicit_kwargs (purpose: {llm_purpose})"
                and explicit_api_base is None
                and not (
                    azure_env_api_key
                    and azure_env_api_base
                    and azure_env_api_version
                    and explicit_api_key is None
                    and explicit_api_base is None
                    and explicit_api_version is None
                )
                and not (
                    openai_env_api_key
                    and explicit_api_key is None
                    and explicit_api_base is None
                )
            ):  # Ensure higher priority didn't set base
                config_source_log = f"ollama_default (purpose: {llm_purpose})"

        # Construct parameters for LiteLLM call
        # The 'model' variable here is the one determined by the public calling method (e.g., final_model in acreate_embedding or agenerate_response)

        is_azure_provider = config_source_log.startswith("azure_env") or (
            final_api_base and "azure" in final_api_base.lower()
        )

        # Dispatch to Azure SDK if applicable, otherwise use LiteLLM
        if is_azure_provider and not model.startswith("ollama/"):
            logger.debug(
                f"Using Azure SDK for purpose '{llm_purpose}' with model '{model}' (config source: {config_source_log})."
            )
            if not final_api_key or not final_api_base or not final_api_version:
                raise LLMServiceError(
                    f"Azure provider selected for purpose '{llm_purpose}' but missing one or more required credentials (API Key, Base URL, API Version)."
                )

            if method_name == "acompletion":
                logger.debug(
                    f"Calling Azure SDK acompletion for model '{model}' (purpose: {llm_purpose}). Config source: '{config_source_log}'."
                )
                # Pass all relevant kwargs directly to the SDK call
                return await self._call_azure_sdk_acompletion(
                    model_deployment_name=model,
                    api_key=final_api_key,
                    api_base=final_api_base,
                    api_version=final_api_version,
                    **kwargs,  # Pass messages, stream, and any other completion params via kwargs
                )
            elif method_name == "aembedding":
                logger.debug(
                    f"Calling Azure SDK aembedding for model '{model}' (purpose: {llm_purpose}). Config source: '{config_source_log}'."
                )
                # Pass all relevant kwargs directly to the SDK call
                return await self._call_azure_sdk_aembedding(
                    model_deployment_name=model,
                    api_key=final_api_key,
                    api_base=final_api_base,
                    api_version=final_api_version,
                    input_texts=kwargs.get("input", []),
                    **kwargs,  # Note: acreate_embedding passes 'input_texts', _call_litellm receives it as 'input' via kwargs
                )
            else:
                raise ValueError(f"Unsupported LiteLLM method: {method_name}")
        else:
            # Use LiteLLM for non-Azure providers or Ollama
            logger.debug(
                f"Using LiteLLM for purpose '{llm_purpose}' with model '{model}' (config source: {config_source_log})."
            )
            litellm_params = {
                "model": model,
                "api_key": final_api_key,
                "api_base": final_api_base,
            }
            # Add api_version for Azure if LiteLLM is still handling an Azure case (e.g. if logic changes or for specific non-SDK handled Azure models)
            # This part is now less likely to be hit for Azure main models.
            if (
                final_api_version and is_azure_provider
            ):  # is_azure_provider check is a bit redundant here but safe
                if not (final_api_base and "api-version=" in final_api_base.lower()):
                    litellm_params["api_version"] = final_api_version
                elif final_api_base and "api-version=" in final_api_base.lower():
                    logger.debug(
                        f"api-version found in api_base ('{final_api_base}'), not adding separate api_version from env var '{final_api_version}'."
                    )

            litellm_params.update(kwargs)  # Add all other passed-in kwargs

            log_params = {k: v for k, v in litellm_params.items() if k != "api_key"}
            logger.debug(
                f"Calling LiteLLM method: {method_name} for model '{model}' (purpose: {llm_purpose}). Config source: '{config_source_log}'. Params (key excluded): {log_params}"
            )

            try:
                if method_name == "acompletion":
                    # Pass all relevant kwargs (including messages, stream) via litellm_params
                    return await litellm.acompletion(**litellm_params)
                elif method_name == "aembedding":
                    # LiteLLM's aembedding response needs to be parsed
                    embedding_response = await litellm.aembedding(**litellm_params)
                    return [item.embedding for item in embedding_response.data]
                else:
                    raise ValueError(f"Unsupported LiteLLM method: {method_name}")
            except litellm.exceptions.AuthenticationError as e:
                logger.error(
                    f"LiteLLM AuthenticationError for model {model} (purpose: {llm_purpose}, api_base: {final_api_base}, source: {config_source_log}): {e}",
                    exc_info=True,
                )
                raise LLMServiceError(
                    f"Authentication error for model {model} (purpose: {llm_purpose}): {e}"
                ) from e
            except (
                litellm.exceptions.APIError
            ) as e:  # Includes NotFoundError, RateLimitError etc.
                logger.error(
                    f"LiteLLM API error for model {model} (purpose: {llm_purpose}, api_base: {final_api_base}, source: {config_source_log}): {e}",
                    exc_info=True,
                )
                raise LLMServiceError(
                    f"LLM API error for model {model} (purpose: {llm_purpose}): {e}"
                ) from e
            except Exception as e:
                logger.error(
                    f"Unexpected error during LiteLLM call for model {model} (purpose: {llm_purpose}, api_base: {final_api_base}, source: {config_source_log}): {e}",
                    exc_info=True,
                )
                raise LLMServiceError(
                    f"Unexpected error for model {model} (purpose: {llm_purpose}): {e}"
                ) from e

    async def agenerate_response(
        self,
        messages: List[Dict[str, str]],
        llm_purpose: str,  # e.g., "streamlit", "rag"
        model: str | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any | AsyncGenerator[Any, None]:
        """
        Generates a response from the specified LLM.

        Args:
            messages (list): A list of message objects, typically {"role": "user/assistant/system", "content": "..."}.
            llm_purpose (str): The purpose of the LLM call (e.g., "streamlit", "rag"). Used for config and default model selection.
            model (str, optional): The model identifier. If None, uses default for llm_purpose.
            stream (bool): Whether to stream the response. Defaults to False.
            **kwargs: Additional parameters to pass to the LiteLLM completion call (e.g., temperature, max_tokens).

        Returns:
            The response from the LLM. If streaming, this will be an async iterator.
        Raises:
            LLMServiceError: If an API error occurs.
            ValueError: If no model is specified and no default model can be found.
        """
        final_model = model
        if final_model is None:
            final_model = self.default_models.get(
                llm_purpose
            ) or self.default_models.get("generic")
        if final_model is None:
            raise ValueError(
                f"No model specified and no default model found for purpose '{llm_purpose}' or generic default."
            )

        return await self._call_litellm(
            "acompletion",
            model=final_model,
            llm_purpose=llm_purpose,
            messages=messages,
            stream=stream,
            **kwargs,
        )

    async def acreate_embedding(
        self, input_texts: List[str], model: str | None = None, **kwargs: Any
    ) -> List[List[float]]:
        """
        Generates embeddings for a list of input texts using LiteLLM.
        """
        llm_purpose = "embedding"
        final_model = model
        if final_model is None:
            final_model = self.default_models.get(
                llm_purpose
            ) or self.default_models.get("generic")
        if final_model is None:
            raise ValueError(
                f"No model specified and no default model found for purpose '{llm_purpose}' or generic default."
            )

        embedding_response = await self._call_litellm(
            "aembedding",
            model=final_model,
            llm_purpose=llm_purpose,
            input=input_texts,
            **kwargs,
        )
        return embedding_response  # Already in List[List[float]] format from dispatcher

    def _initialize_nvidia_client(self):
        """Initializes the NVIDIA AsyncOpenAI client if API key is available."""
        if self._nvidia_api_key:
            try:
                self._nvidia_async_client = openai.AsyncOpenAI(
                    base_url=self._nvidia_base_url,
                    api_key=self._nvidia_api_key,
                )
                self.is_nvidia_client_available = True
                logger.info(
                    f"NVIDIA AsyncOpenAI client initialized for vision model '{self._nvidia_default_vision_model}' at base URL '{self._nvidia_base_url}'."
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize NVIDIA AsyncOpenAI client: {e}",
                    exc_info=True,
                )
                self._nvidia_async_client = None
                self.is_nvidia_client_available = False
        else:
            logger.info(
                f"'{NVIDIA_API_KEY_ENV_VAR}' not set. NVIDIA multi-modal capabilities will be unavailable."
            )

    async def aextract_text_from_image_content(
        self,
        image_bytes: bytes,
        image_mime_type: str,  # e.g., "image/png", "image/jpeg"
        prompt_text: str,
        model: Optional[str] = None,  # Specific NVIDIA vision model to use
    ) -> str:
        """
        Sends image data and a prompt to the configured NVIDIA multi-modal model
        and returns the extracted text.
        """
        if not self.is_nvidia_client_available or not self._nvidia_async_client:
            logger.error("NVIDIA client not initialized. Cannot process image content.")
            raise LLMServiceError("NVIDIA client not initialized for image processing.")

        target_model = model or self._nvidia_default_vision_model
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
                f"Sending request to NVIDIA model {target_model} for image analysis. Prompt: {prompt_text[:50]}..."
            )
            completion = await self._nvidia_async_client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=0.2,
                top_p=0.7,
                max_tokens=2048,
                stream=False,
            )
            if (
                completion.choices
                and completion.choices[0].message
                and completion.choices[0].message.content
            ):
                return completion.choices[0].message.content
            logger.warning(
                f"NVIDIA model '{target_model}' returned no content for prompt '{prompt_text[:50]}...'."
            )
            return ""
        except Exception as e:
            logger.error(
                f"NVIDIA API call to model '{target_model}' failed for prompt '{prompt_text[:50]}...': {e}",
                exc_info=True,
            )
            raise LLMServiceError(
                f"NVIDIA API call to model '{target_model}' failed: {e}"
            )

    def get_langchain_chat_model(
        self,
        llm_purpose: str,
        model_name: Optional[str] = None,
        temperature: Optional[float] = 0.0,
        **kwargs: Any,
    ) -> BaseChatModel:
        """
        Returns a Langchain-compatible chat model instance (ChatOpenAI or AzureChatOpenAI)
        based on environment configuration and specified purpose/model.

        Args:
            llm_purpose (str): The purpose of the LLM call (e.g., "agent_main", "rag").
            model_name (str, optional): Specific model/deployment name. If None, uses default for llm_purpose.
            **kwargs: Additional parameters for the Langchain model constructor (e.g., temperature).

        Returns:
            A Langchain BaseChatModel instance.
        Raises:
            ValueError: If LLM configuration is incomplete or no suitable model can be determined.
        """
        # ============================================================================
        # PRIORITY 1: Check for internal LLM provider FIRST (before reading model_name)
        # ============================================================================
        internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
        internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
        internal_llm_model = os.getenv("INTERNAL_LLM_MODEL")

        if internal_llm_api_key and internal_llm_base_url and internal_llm_model:
            logger.info(
                f"get_langchain_chat_model: Using internal LLM for purpose '{llm_purpose}' with model '{internal_llm_model}'"
            )

            # Determine token limit based on model type
            is_reasoning_model = any(
                reasoning_prefix in internal_llm_model.lower()
                for reasoning_prefix in ["o3", "o4"]
            )
            max_tokens = kwargs.pop("max_tokens", 4000 if is_reasoning_model else 1000)

            from langchain_openai import ChatOpenAI

            # O-series reasoning models only support temperature=1, so don't pass temperature parameter
            if is_reasoning_model:
                logger.info(
                    f"Reasoning model detected ({internal_llm_model}). Not setting temperature (O-series models only support temperature=1 by default)."
                )
                return ChatOpenAI(
                    model=internal_llm_model,
                    api_key=internal_llm_api_key,
                    base_url=internal_llm_base_url,
                    max_tokens=max_tokens,
                    # Don't pass temperature for O-series models
                    **kwargs,  # Allow override of other parameters
                )
            else:
                return ChatOpenAI(
                    model=internal_llm_model,
                    api_key=internal_llm_api_key,
                    base_url=internal_llm_base_url,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs,  # Allow override of other parameters
                )

        # ============================================================================
        # Continue with existing provider logic (Azure, OpenAI, Ollama)
        # ============================================================================

        final_model_name = model_name
        if final_model_name is None:
            final_model_name = self.default_models.get(
                llm_purpose
            ) or self.default_models.get("generic")

        if not final_model_name:
            raise ValueError(
                f"No model name specified and no default model found for purpose '{llm_purpose}' or generic default."
            )

        # Prepare constructor_kwargs by copying incoming kwargs.
        # These will be passed to the Langchain model constructors.
        constructor_kwargs = kwargs.copy()

        # Filter out known unsupported parameters for the specific final_model_name
        if final_model_name in MODEL_SPECIFIC_PARAMS_TO_OMIT:
            for param_to_omit in MODEL_SPECIFIC_PARAMS_TO_OMIT[final_model_name]:
                if param_to_omit in constructor_kwargs:
                    logger.warning(
                        f"Omitting parameter '{param_to_omit}' for model '{final_model_name}' as it's listed for omission from Langchain constructor."
                    )
                    del constructor_kwargs[param_to_omit]

        # Helper to get env vars: tries PURPOSE_SPECIFIC_VAR, then GENERIC_VAR
        def get_env_config(base_var_name: str, purpose: str) -> str | None:
            val = os.getenv(f"{purpose.upper()}_{base_var_name}")
            if val:
                return val
            return os.getenv(base_var_name)

        azure_api_key = get_env_config("AZURE_API_KEY", llm_purpose)
        azure_api_base = get_env_config("AZURE_API_BASE", llm_purpose)
        azure_api_version = get_env_config("AZURE_API_VERSION", llm_purpose)

        openai_api_key = get_env_config("OPENAI_API_KEY", llm_purpose)

        # Prioritize Azure if its specific variables are set
        if azure_api_base and azure_api_key and azure_api_version:
            logger.info(
                f"Configuring AzureChatOpenAI for purpose '{llm_purpose}' with deployment: {final_model_name}"
            )
            from langchain_openai import AzureChatOpenAI  # Local import

            azure_root_endpoint = self._parse_azure_root_endpoint(azure_api_base)
            return AzureChatOpenAI(
                azure_deployment=final_model_name,
                openai_api_version=azure_api_version,
                azure_endpoint=azure_root_endpoint,
                api_key=azure_api_key,
                # temperature=temperature,
                **constructor_kwargs,  # Use potentially filtered kwargs
            )
        elif openai_api_key:
            logger.info(
                f"Configuring ChatOpenAI for purpose '{llm_purpose}' with model: {final_model_name}"
            )
            from langchain_openai import ChatOpenAI  # Local import

            return ChatOpenAI(
                model=final_model_name,
                openai_api_key=openai_api_key,
                # temperature=temperature,
                **constructor_kwargs,  # Use potentially filtered kwargs
            )
        else:
            error_msg = (
                f"LLM configuration for Langchain model (purpose: {llm_purpose}, model: {final_model_name}) is missing or incomplete. "
                "Please set environment variables for either Azure OpenAI "
                "(e.g., AZURE_API_BASE, AZURE_API_KEY, AZURE_API_VERSION) "
                "or standard OpenAI (e.g., OPENAI_API_KEY)."
            )
            logger.error(error_msg)
            # Fallback to ChatLiteLLM if direct Azure/OpenAI config is missing
            logger.info(
                f"Attempting to configure ChatLiteLLM as fallback for purpose '{llm_purpose}' with model: {final_model_name}"
            )
            try:
                from langchain_community.chat_models import ChatLiteLLM  # Local import
            except ImportError:
                logger.error(
                    "langchain_community.chat_models.ChatLiteLLM not found. Please install langchain-community."
                )
                raise ValueError(
                    f"{error_msg} Also, ChatLiteLLM (langchain-community) is not available for fallback."
                )

            # For ChatLiteLLM, pass the (potentially filtered) constructor_kwargs.
            # ChatLiteLLM's constructor accepts **kwargs which are passed to litellm.completion.
            # LiteLLM handles its own credential resolution and model-specific parameter adaptation.
            chat_litellm_final_kwargs = constructor_kwargs.copy()
            chat_litellm_final_kwargs["model"] = (
                final_model_name  # Ensure model name is present
            )

            # Log parameters, avoiding direct logging of any API keys if they were in kwargs
            log_display_params = {
                k: v
                for k, v in chat_litellm_final_kwargs.items()
                if "key" not in k.lower()
            }
            logger.debug(f"Instantiating ChatLiteLLM with params: {log_display_params}")
            return ChatLiteLLM(**chat_litellm_final_kwargs)
