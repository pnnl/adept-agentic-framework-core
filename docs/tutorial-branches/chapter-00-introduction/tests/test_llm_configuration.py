"""
Smoke tests for LLM configuration patterns.
Tests both traditional cloud providers and internal LLM provider patterns.
"""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from agentic_framework_pkg.core.llm_agnostic_layer import (
    LLMAgnosticClient,
    LLMServiceError,
)


class TestLLMAgnosticClient:
    """Test suite for LLMAgnosticClient with various provider configurations."""

    def test_initialization_with_defaults(self):
        """Test client initializes with default environment variables."""
        with patch.dict(
            os.environ,
            {"STREAMLIT_DEFAULT_MODEL": "gpt-4", "DEFAULT_LLM_MODEL": "gpt-3.5-turbo"},
            clear=True,
        ):
            client = LLMAgnosticClient()
            assert client.default_models["streamlit"] == "gpt-4"
            assert client.default_models["generic"] == "gpt-3.5-turbo"
            assert not client.use_internal_llm

    def test_initialization_with_internal_llm_provider(self):
        """Test client initializes with internal LLM provider configuration."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-api-key",
                "INTERNAL_LLM_BASE_URL": "https://internal-llm.example.com/v1",
                "INTERNAL_LLM_MODEL": "internal-model-v1",
                "INTERNAL_LLM_EMBEDDING_MODEL": "internal-embedding-v1",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()
            assert client.use_internal_llm is True
            assert client.internal_llm_config["api_key"] == "test-api-key"
            assert (
                client.internal_llm_config["base_url"]
                == "https://internal-llm.example.com/v1"
            )
            assert client.internal_llm_config["model"] == "internal-model-v1"

    def test_initialization_with_partial_internal_llm_config(self):
        """Test client handles partial internal LLM configuration correctly."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-api-key",
                "INTERNAL_LLM_BASE_URL": "https://internal-llm.example.com/v1",
                # Missing INTERNAL_LLM_MODEL
            },
            clear=True,
        ):
            client = LLMAgnosticClient()
            assert client.use_internal_llm is False

    @pytest.mark.asyncio
    async def test_agenerate_response_with_internal_llm(self):
        """Test response generation with internal LLM provider."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-api-key",
                "INTERNAL_LLM_BASE_URL": "https://internal-llm.example.com/v1",
                "INTERNAL_LLM_MODEL": "internal-model-v1",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Test response"))
            ]

            with patch(
                "litellm.acompletion", new=AsyncMock(return_value=mock_response)
            ) as mock_completion:
                messages = [{"role": "user", "content": "Hello"}]
                result = await client.agenerate_response(messages, "generic")

                # Verify litellm was called with correct parameters
                mock_completion.assert_called_once()
                call_args = mock_completion.call_args

                assert call_args[1]["model"] == "openai/internal-model-v1"
                assert call_args[1]["api_key"] == "test-api-key"
                assert call_args[1]["api_base"] == "https://internal-llm.example.com/v1"
                assert call_args[1]["messages"] == messages

    @pytest.mark.asyncio
    async def test_agenerate_response_with_azure(self):
        """Test response generation with Azure OpenAI."""
        with patch.dict(
            os.environ,
            {
                "DEFAULT_LLM_MODEL": "gpt-4",
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Azure response"))
            ]

            with patch(
                "litellm.acompletion", new=AsyncMock(return_value=mock_response)
            ) as mock_completion:
                messages = [{"role": "user", "content": "Hello Azure"}]
                result = await client.agenerate_response(
                    messages, "generic", model="gpt-4"
                )

                mock_completion.assert_called_once()
                call_args = mock_completion.call_args
                assert call_args[1]["model"] == "gpt-4"
                assert call_args[1]["messages"] == messages

    @pytest.mark.asyncio
    async def test_agenerate_response_with_ollama(self):
        """Test response generation with Ollama."""
        with patch.dict(
            os.environ,
            {
                "DEFAULT_LLM_MODEL": "ollama/mistral",
                "OLLAMA_API_BASE_URL": "http://localhost:11434",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Ollama response"))
            ]

            with patch(
                "litellm.acompletion", new=AsyncMock(return_value=mock_response)
            ) as mock_completion:
                messages = [{"role": "user", "content": "Hello Ollama"}]
                result = await client.agenerate_response(messages, "generic")

                mock_completion.assert_called_once()
                call_args = mock_completion.call_args
                assert call_args[1]["model"] == "ollama/mistral"
                assert call_args[1]["api_base"] == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_agenerate_response_with_explicit_model_override(self):
        """Test that explicit model parameter overrides internal LLM."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-api-key",
                "INTERNAL_LLM_BASE_URL": "https://internal-llm.example.com/v1",
                "INTERNAL_LLM_MODEL": "internal-model-v1",
                "DEFAULT_LLM_MODEL": "gpt-4",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Override response"))
            ]

            with patch(
                "litellm.acompletion", new=AsyncMock(return_value=mock_response)
            ) as mock_completion:
                messages = [{"role": "user", "content": "Hello"}]
                # Explicitly specify a different model
                result = await client.agenerate_response(
                    messages, "generic", model="gpt-4-turbo"
                )

                mock_completion.assert_called_once()
                call_args = mock_completion.call_args
                # Should use the explicitly specified model, not internal
                assert call_args[1]["model"] == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_agenerate_response_error_handling(self):
        """Test error handling in response generation."""
        with patch.dict(os.environ, {"DEFAULT_LLM_MODEL": "gpt-4"}, clear=True):
            client = LLMAgnosticClient()

            with patch(
                "litellm.acompletion", new=AsyncMock(side_effect=Exception("API Error"))
            ) as mock_completion:
                messages = [{"role": "user", "content": "Hello"}]

                with pytest.raises(LLMServiceError) as exc_info:
                    await client.agenerate_response(messages, "generic")

                assert "LiteLLM completion error" in str(exc_info.value)
                assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_agenerate_response_no_model_configured(self):
        """Test error when no model is configured."""
        with patch.dict(os.environ, {}, clear=True):
            client = LLMAgnosticClient()
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(ValueError) as exc_info:
                await client.agenerate_response(messages, "unknown_purpose")

            assert "No model specified" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_agenerate_response_streaming(self):
        """Test streaming response generation."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-api-key",
                "INTERNAL_LLM_BASE_URL": "https://internal-llm.example.com/v1",
                "INTERNAL_LLM_MODEL": "internal-model-v1",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            async def mock_stream():
                for chunk in ["Hello", " ", "World"]:
                    yield MagicMock(choices=[MagicMock(delta=MagicMock(content=chunk))])

            with patch(
                "litellm.acompletion", new=AsyncMock(return_value=mock_stream())
            ) as mock_completion:
                messages = [{"role": "user", "content": "Hello"}]
                result = await client.agenerate_response(
                    messages, "generic", stream=True
                )

                mock_completion.assert_called_once()
                call_args = mock_completion.call_args
                assert call_args[1]["stream"] is True


class TestInternalLLMProviderIntegration:
    """Integration tests specifically for internal LLM provider pattern."""

    @pytest.mark.asyncio
    async def test_internal_llm_with_custom_embedding(self):
        """Test internal LLM provider with custom embedding model."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.example.com/v1",
                "INTERNAL_LLM_MODEL": "custom-chat-model",
                "INTERNAL_LLM_EMBEDDING_MODEL": "custom-embedding-model",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            assert client.use_internal_llm is True
            assert (
                client.internal_llm_config["embedding_model"]
                == "custom-embedding-model"
            )

    @pytest.mark.asyncio
    async def test_fallback_to_cloud_when_internal_not_configured(self):
        """Test that system falls back to cloud providers when internal LLM is not configured."""
        with patch.dict(
            os.environ,
            {"DEFAULT_LLM_MODEL": "gpt-4", "OPENAI_API_KEY": "openai-key"},
            clear=True,
        ):
            client = LLMAgnosticClient()

            assert not client.use_internal_llm

            mock_response = MagicMock()
            with patch(
                "litellm.acompletion", new=AsyncMock(return_value=mock_response)
            ) as mock_completion:
                messages = [{"role": "user", "content": "Test"}]
                await client.agenerate_response(messages, "generic")

                call_args = mock_completion.call_args
                # Should use cloud model
                assert call_args[1]["model"] == "gpt-4"
                assert (
                    "api_base" not in call_args[1]
                    or call_args[1].get("api_base") is None
                )
