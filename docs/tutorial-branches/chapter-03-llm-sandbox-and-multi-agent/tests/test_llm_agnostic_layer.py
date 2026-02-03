"""
Tests for internal LLM provider in LLMAgnosticClient (LiteLLM integration).
Validates that internal LLM is prioritized over cloud providers.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from agentic_framework_pkg.core.llm_agnostic_layer import LLMAgnosticClient


class TestLLMAgnosticLayerInternalProvider:
    """Test suite for internal LLM provider in LLMAgnosticClient."""

    @pytest.mark.asyncio
    async def test_internal_llm_completion(self):
        """Test that internal LLM is used for completion calls when configured."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com",
                "INTERNAL_LLM_MODEL": "company-model",
                "AZURE_API_KEY": "azure-key",  # Should be ignored
                "AZURE_API_BASE": "https://example.openai.azure.com/",  # Should be ignored
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            # Mock litellm.acompletion to verify it's called
            with patch(
                "agentic_framework_pkg.core.llm_agnostic_layer.litellm.acompletion"
            ) as mock_acompletion:
                mock_acompletion.return_value = AsyncMock()
                mock_acompletion.return_value.choices = [
                    MagicMock(message=MagicMock(content="Test response"))
                ]

                # Call should use internal LLM
                try:
                    await client.agenerate_response(
                        messages=[{"role": "user", "content": "test"}],
                        llm_purpose="test",
                        model="test-model",  # This should be overridden by internal model
                    )
                except Exception:
                    pass  # We're just testing that the mock was called correctly

                # Verify litellm.acompletion was called with internal LLM config
                assert mock_acompletion.called
                call_kwargs = mock_acompletion.call_args[1]
                assert call_kwargs["api_key"] == "internal-key"
                assert call_kwargs["api_base"] == "https://internal.company.com"
                # LiteLLM requires openai/ prefix for custom base URLs
                assert call_kwargs["model"].startswith("openai/")

    @pytest.mark.asyncio
    async def test_internal_llm_embedding(self):
        """Test that internal LLM is used for embedding calls when configured."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com",
                "INTERNAL_LLM_MODEL": "chat-model",
                "INTERNAL_LLM_EMBEDDING_MODEL": "embedding-model",
                "EMBEDDING_DEFAULT_MODEL": "embedding-model",  # For fallback
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            # Mock litellm.aembedding to verify it's called
            with patch(
                "agentic_framework_pkg.core.llm_agnostic_layer.litellm.aembedding",
                new_callable=AsyncMock,
            ) as mock_aembedding:
                # Create mock EmbeddingResponse
                mock_aembedding.return_value = [[0.1, 0.2, 0.3]]

                try:
                    result = await client.acreate_embedding(
                        input_texts=["test"],
                        model="some-model",  # Should be overridden by internal embedding model
                    )
                except Exception:
                    pass

                # Verify litellm.aembedding was called with internal LLM config
                assert mock_aembedding.called
                call_kwargs = mock_aembedding.call_args[1]
                assert call_kwargs["api_key"] == "internal-key"
                assert call_kwargs["api_base"] == "https://internal.company.com"
                # Model should be overridden to internal embedding model
                assert "embedding-model" in call_kwargs["model"]

    @pytest.mark.asyncio
    async def test_internal_llm_priority_over_azure(self):
        """Test that internal LLM takes precedence over Azure when both configured."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com",
                "INTERNAL_LLM_MODEL": "internal-model",
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
                "LANGCHAIN_LLM_MODEL": "gpt-4",  # Add a model name for fallback
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            with patch(
                "agentic_framework_pkg.core.llm_agnostic_layer.litellm.acompletion",
                new_callable=AsyncMock,
            ) as mock_acompletion:
                # Mock the return value properly
                mock_response = MagicMock()
                mock_response.choices = [
                    MagicMock(message=MagicMock(content="Response"))
                ]
                mock_acompletion.return_value = mock_response

                try:
                    await client.agenerate_response(
                        messages=[{"role": "user", "content": "test"}],
                        llm_purpose="test",
                        model="test-model",  # Provide a model name
                    )
                except Exception:
                    pass

                # Verify internal LLM was used (not Azure SDK)
                assert mock_acompletion.called
                call_kwargs = mock_acompletion.call_args[1]
                # Should use internal config, not Azure
                assert call_kwargs["api_base"] == "https://internal.company.com"
                assert (
                    "internal-model" in call_kwargs["model"]
                    or "openai/internal-model" in call_kwargs["model"]
                )

    @pytest.mark.asyncio
    async def test_fallback_to_azure_when_no_internal(self):
        """Test fallback to Azure when internal LLM not configured."""
        with patch.dict(
            os.environ,
            {
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
                "LANGCHAIN_LLM_MODEL": "gpt-4-deployment",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            # Should use Azure SDK, not litellm for internal
            with patch.object(client, "_call_azure_sdk_acompletion") as mock_azure:
                mock_azure.return_value = AsyncMock()

                try:
                    await client.agenerate_response(
                        messages=[{"role": "user", "content": "test"}],
                        llm_purpose="test",
                        model="gpt-4-deployment",
                    )
                except Exception:
                    pass

                # Verify Azure SDK was called
                assert mock_azure.called

    def test_get_langchain_chat_model_uses_internal(self):
        """Test get_langchain_chat_model uses internal LLM when configured."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com",
                "INTERNAL_LLM_MODEL": "internal-model",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()
            llm = client.get_langchain_chat_model(llm_purpose="test")

            assert llm is not None
            assert llm.__class__.__name__ == "ChatOpenAI"
            # Verify it's configured with internal LLM (check both attribute names)
            assert hasattr(llm, "openai_api_base") or hasattr(llm, "base_url")
            # Verify the actual value
            api_base = getattr(llm, "openai_api_base", None) or getattr(
                llm, "base_url", None
            )
            assert api_base == "https://internal.company.com"

    def test_incomplete_internal_config_uses_fallback(self):
        """Test that incomplete internal LLM config falls back to cloud providers."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                # Missing INTERNAL_LLM_BASE_URL and INTERNAL_LLM_MODEL
                "OPENAI_API_KEY": "openai-key",
                "LANGCHAIN_LLM_MODEL": "gpt-4",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()
            # Pass a model_name explicitly to avoid ValueError
            llm = client.get_langchain_chat_model(
                llm_purpose="test", model_name="gpt-4"
            )

            assert llm is not None
            # Should use OpenAI fallback
            assert llm.__class__.__name__ == "ChatOpenAI"
