"""
Integration test reproducing the internal LLM embedding issue.
This test validates that embeddings use the internal LLM provider when configured.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from agentic_framework_pkg.core.embedding_config import get_embedding_model


class TestInternalLLMEmbeddingIntegration:
    """Test suite for internal LLM provider embedding configuration."""

    def test_embedding_uses_internal_llm_when_configured(self):
        """Test that embeddings use internal LLM provider when all env vars are set."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "sk-test-key-example",
                "INTERNAL_LLM_BASE_URL": "https://ai-incubator-api.pnnl.gov/v1",
                "INTERNAL_LLM_MODEL": "o4-mini-birthright",
                "INTERNAL_LLM_EMBEDDING_MODEL": "text-embedding-3-small-project",
                # Even with Ollama configured, should use internal
                "OLLAMA_API_BASE": "http://localhost:11434",
                "EMBEDDING_DEFAULT_MODEL": "ollama/nomic-embed-text",
            },
            clear=True,
        ):
            embedding_model = get_embedding_model()

            # Should return OpenAIEmbeddings configured for internal endpoint
            assert embedding_model.__class__.__name__ == "OpenAIEmbeddings"
            # Verify it's configured with internal settings
            assert hasattr(embedding_model, "model") or hasattr(
                embedding_model, "model_name"
            )

    def test_embedding_falls_back_to_ollama_without_internal_config(self):
        """Test that embeddings fall back to Ollama when internal LLM is not configured."""
        with patch.dict(
            os.environ,
            {
                "OLLAMA_API_BASE_URL": "http://localhost:11434",
                "EMBEDDING_DEFAULT_MODEL": "ollama/nomic-embed-text",
            },
            clear=True,
        ):
            embedding_model = get_embedding_model()

            # Should return OllamaEmbeddings when internal not configured
            assert embedding_model.__class__.__name__ == "OllamaEmbeddings"

    def test_embedding_partial_internal_config_ignored(self):
        """Test that partial internal LLM configuration is ignored."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.example.com/v1",
                # Missing INTERNAL_LLM_EMBEDDING_MODEL
                "OLLAMA_API_BASE_URL": "http://localhost:11434",
                "EMBEDDING_DEFAULT_MODEL": "ollama/nomic-embed-text",
            },
            clear=True,
        ):
            embedding_model = get_embedding_model()

            # Should fall back to Ollama when internal config is incomplete
            assert embedding_model.__class__.__name__ == "OllamaEmbeddings"

    def test_embedding_internal_llm_takes_precedence_over_azure(self):
        """Test that internal LLM takes precedence over Azure configuration."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.example.com/v1",
                "INTERNAL_LLM_EMBEDDING_MODEL": "internal-embedding-model",
                # Azure also configured
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
                "EMBEDDING_DEFAULT_MODEL": "text-embedding-ada-002",
            },
            clear=True,
        ):
            embedding_model = get_embedding_model()

            # Should use internal LLM, not Azure
            assert embedding_model.__class__.__name__ == "OpenAIEmbeddings"
            # Note: Can't easily verify the exact base URL without accessing private attrs

    def test_embedding_base_url_without_v1_suffix(self):
        """Test embedding with internal LLM base URL that doesn't end in /v1."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.example.com",  # No /v1
                "INTERNAL_LLM_EMBEDDING_MODEL": "test-embedding-model",
            },
            clear=True,
        ):
            embedding_model = get_embedding_model()

            # Should still create OpenAIEmbeddings instance
            # The base URL will be passed as-is; OpenAI client will handle it
            assert embedding_model.__class__.__name__ == "OpenAIEmbeddings"

    def test_user_scenario_ai_incubator(self):
        """
        Test the exact user scenario with AI Incubator configuration.
        This reproduces the issue where Ollama was being used for embeddings
        instead of the internal LLM provider.
        """
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "sk-test-key-example",
                "INTERNAL_LLM_BASE_URL": "https://ai-incubator-api.pnnl.gov/v1",
                "INTERNAL_LLM_MODEL": "o4-mini-birthright",
                "INTERNAL_LLM_EMBEDDING_MODEL": "text-embedding-3-small-project",
                "LANGCHAIN_LLM_MODEL": "o3-mini",
                "STREAMLIT_DEFAULT_MODEL": "o3-mini",
                # Ollama is also running but should NOT be used for embeddings
                "OLLAMA_API_BASE": "http://ollama:11434",
                "EMBEDDING_DEFAULT_MODEL": "ollama/nomic-embed-text",
            },
            clear=True,
        ):
            embedding_model = get_embedding_model()

            # CRITICAL: Should use OpenAIEmbeddings with internal config, NOT OllamaEmbeddings
            assert embedding_model.__class__.__name__ == "OpenAIEmbeddings", (
                "Expected OpenAIEmbeddings for internal LLM provider, but got OllamaEmbeddings instead!"
            )

            # Verify the model name is set correctly
            model_attr = getattr(embedding_model, "model", None) or getattr(
                embedding_model, "model_name", None
            )
            assert model_attr == "text-embedding-3-small-project", (
                f"Expected model 'text-embedding-3-small-project' but got '{model_attr}'"
            )


class TestEmbeddingErrorCases:
    """Test error handling and edge cases for embedding configuration."""

    def test_embedding_no_configuration_at_all(self):
        """Test embedding when no configuration is provided."""
        with patch.dict(os.environ, {}, clear=True):
            embedding_model = get_embedding_model()

            # Should fall back to default (Ollama)
            assert embedding_model.__class__.__name__ == "OllamaEmbeddings"

    def test_embedding_empty_strings_not_treated_as_configured(self):
        """Test that empty string env vars are not treated as valid configuration."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "",
                "INTERNAL_LLM_BASE_URL": "",
                "INTERNAL_LLM_EMBEDDING_MODEL": "",
                "OLLAMA_API_BASE_URL": "http://localhost:11434",
                "EMBEDDING_DEFAULT_MODEL": "ollama/nomic-embed-text",
            },
            clear=True,
        ):
            embedding_model = get_embedding_model()

            # Should fall back to Ollama when internal config is empty strings
            assert embedding_model.__class__.__name__ == "OllamaEmbeddings"
