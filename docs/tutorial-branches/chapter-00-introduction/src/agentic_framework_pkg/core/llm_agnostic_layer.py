import litellm
import os
from typing import List, Dict, Any, AsyncGenerator, Optional
from dotenv import load_dotenv

from .logger_config import get_logger

load_dotenv()

logger = get_logger(__name__)


class LLMServiceError(Exception):
    pass


class LLMAgnosticClient:
    DEFAULT_MODEL_ENV_VARS = {
        "streamlit": "STREAMLIT_DEFAULT_MODEL",
        "generic": "DEFAULT_LLM_MODEL",
    }

    def __init__(self):
        self.default_models = {
            purpose: os.getenv(env_var_name)
            for purpose, env_var_name in self.DEFAULT_MODEL_ENV_VARS.items()
        }

        # Check for internal LLM provider configuration
        self.internal_llm_config = {
            "api_key": os.getenv("INTERNAL_LLM_API_KEY"),
            "base_url": os.getenv("INTERNAL_LLM_BASE_URL"),
            "model": os.getenv("INTERNAL_LLM_MODEL"),
            "embedding_model": os.getenv("INTERNAL_LLM_EMBEDDING_MODEL"),
        }
        self.use_internal_llm = all(
            [
                self.internal_llm_config["api_key"],
                self.internal_llm_config["base_url"],
                self.internal_llm_config["model"],
            ]
        )

        if self.use_internal_llm:
            logger.info(
                f"Internal LLM provider configured: {self.internal_llm_config['base_url']}"
            )

    async def agenerate_response(
        self,
        messages: List[Dict[str, str]],
        llm_purpose: str,
        model: str | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any | AsyncGenerator[Any, None]:
        # Determine the final model to use
        final_model = model
        use_internal_for_this_request = False

        if final_model is None:
            # Check if using internal LLM provider
            if self.use_internal_llm:
                final_model = self.internal_llm_config["model"]
                use_internal_for_this_request = True
                logger.info(f"Using internal LLM model: {final_model}")
            else:
                final_model = self.default_models.get(
                    llm_purpose
                ) or self.default_models.get("generic")
        else:
            # Model was explicitly specified - respect it
            # But still use internal LLM if the specified model matches the internal model name
            if (
                self.use_internal_llm
                and final_model == self.internal_llm_config["model"]
            ):
                use_internal_for_this_request = True

        if final_model is None:
            raise ValueError(
                f"No model specified and no default model found for purpose '{llm_purpose}' or generic default."
            )

        # Configure API base and key for internal LLM provider
        if use_internal_for_this_request:
            # For internal LLM with OpenAI-compatible format, use "openai/" prefix
            # to ensure LiteLLM treats it as an OpenAI-compatible endpoint
            if not final_model.startswith("openai/"):
                final_model = f"openai/{final_model}"

            kwargs["api_key"] = self.internal_llm_config["api_key"]
            kwargs["api_base"] = self.internal_llm_config["base_url"]
            logger.debug(
                f"Internal LLM request - model: {final_model}, base_url: {kwargs['api_base']}"
            )
        elif final_model.startswith("ollama/"):
            kwargs["api_base"] = os.getenv("OLLAMA_API_BASE_URL") or os.getenv(
                "OLLAMA_API_BASE"
            )

        try:
            return await litellm.acompletion(
                model=final_model, messages=messages, stream=stream, **kwargs
            )
        except Exception as e:
            logger.error(
                f"LiteLLM completion error for model {final_model}: {e}", exc_info=True
            )
            raise LLMServiceError(
                f"LiteLLM completion error for model {final_model}: {e}"
            ) from e
