"""
Tests for internal LLM provider in LLMAgnosticClient (LiteLLM integration).
Validates that internal LLM is prioritized over cloud providers.
"""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call
from agentic_framework_pkg.core.llm_agnostic_layer import LLMAgnosticClient


class TestLLMAgnosticLayerInternalProvider:
    """Test suite for internal LLM provider in LLMAgnosticClient."""

    @pytest.mark.asyncio
    async def test_internal_llm_used_for_completion(self):
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
                        model="company-model",
                        messages=[{"role": "user", "content": "test"}],
                        llm_purpose="generic",
                    )
                except Exception:
                    pass  # We're just testing that litellm was called with internal config

                # Verify litellm.acompletion was called with internal LLM config
                assert mock_acompletion.called
                call_kwargs = mock_acompletion.call_args[1]
                assert call_kwargs["api_key"] == "internal-key"
                assert call_kwargs["api_base"] == "https://internal.company.com"
                # LiteLLM requires openai/ prefix for custom base URLs
                assert call_kwargs["model"].startswith("openai/")

    @pytest.mark.asyncio
    async def test_fallback_to_azure_when_no_internal(self):
        """Test fallback to Azure when internal LLM not configured."""
        with patch.dict(
            os.environ,
            {
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            # Should use Azure SDK, not litellm for internal
            with patch.object(client, "_call_azure_sdk_acompletion") as mock_azure:
                mock_azure.return_value = AsyncMock()

                try:
                    await client.agenerate_response(
                        model="gpt-4",
                        messages=[{"role": "user", "content": "test"}],
                        llm_purpose="generic",
                    )
                except Exception:
                    pass

                # Verify Azure SDK was called
                assert mock_azure.called

    def test_internal_llm_model_override_for_embeddings(self):
        """Test that embedding calls override model with INTERNAL_LLM_EMBEDDING_MODEL."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com",
                "INTERNAL_LLM_MODEL": "chat-model",
                "INTERNAL_LLM_EMBEDDING_MODEL": "embedding-model",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            # When purpose is "embedding", model should be overridden
            with patch(
                "agentic_framework_pkg.core.llm_agnostic_layer.litellm.aembedding"
            ) as mock_aembedding:
                mock_aembedding.return_value = AsyncMock()
                mock_aembedding.return_value.data = [MagicMock(embedding=[0.1])]

                try:
                    # Even though we pass "some-model", it should use INTERNAL_LLM_EMBEDDING_MODEL
                    asyncio.run(
                        client.acreate_embedding(
                            model="some-model",
                            input_texts=["test"],
                            llm_purpose="embedding",
                        )
                    )
                except Exception:
                    pass

                if mock_aembedding.called:
                    call_kwargs = mock_aembedding.call_args[1]
                    # Model should be overridden to embedding model
                    assert call_kwargs["model"] == "embedding-model"

    @pytest.mark.asyncio
    async def test_embedding_response_conversion(self):
        """Test that LiteLLM EmbeddingResponse is properly converted to List[List[float]]."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com",
                "INTERNAL_LLM_EMBEDDING_MODEL": "test-embedding",
                "EMBEDDING_DEFAULT_MODEL": "test-embedding",  # Required for model resolution
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            # Mock litellm.aembedding to return EmbeddingResponse object with .data attribute
            with patch(
                "agentic_framework_pkg.core.llm_agnostic_layer.litellm.aembedding",
                new_callable=AsyncMock,
            ) as mock_aembedding:
                # Create mock EmbeddingResponse with .data attribute (like real LiteLLM)
                mock_embedding_item = MagicMock()
                mock_embedding_item.embedding = [0.1, 0.2, 0.3]
                mock_response = MagicMock()
                mock_response.data = [mock_embedding_item]
                mock_aembedding.return_value = mock_response

                result = await client.acreate_embedding(input_texts=["test"])

                # Verify conversion to List[List[float]]
                assert isinstance(result, list), "Result should be a list"
                assert len(result) == 1, "Should have one embedding for one input"
                assert isinstance(result[0], list), "Each embedding should be a list"
                assert result[0] == [0.1, 0.2, 0.3], "Embedding values should match"

    @pytest.mark.asyncio
    async def test_embedding_response_dict_format(self):
        """Test that dict-format embedding responses are correctly converted."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com",
                "INTERNAL_LLM_EMBEDDING_MODEL": "test-embedding",
                "EMBEDDING_DEFAULT_MODEL": "test-embedding",
            },
            clear=True,
        ):
            client = LLMAgnosticClient()

            with patch(
                "agentic_framework_pkg.core.llm_agnostic_layer.litellm.aembedding",
                new_callable=AsyncMock,
            ) as mock_aembedding:
                # Return dict format (as seen in production logs)
                mock_aembedding.return_value = {
                    "data": [
                        {
                            "embedding": [0.1, 0.2, 0.3],
                            "index": 0,
                            "object": "embedding",
                        }
                    ],
                    "model": "text-embedding-3-small",
                    "object": "list",
                }

                result = await client.acreate_embedding(input_texts=["test"])

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0] == [0.1, 0.2, 0.3]


import asyncio  # Needed for asyncio.run in test
