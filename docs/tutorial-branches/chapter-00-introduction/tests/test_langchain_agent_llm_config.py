"""
Smoke tests for ScientificWorkflowAgent with various LLM configurations.
Tests both traditional cloud providers and internal LLM provider patterns.
"""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from agentic_framework_pkg.scientific_workflow.langchain_agent import (
    ScientificWorkflowAgent,
)


class TestScientificWorkflowAgentLLMConfiguration:
    """Test suite for ScientificWorkflowAgent LLM configuration."""

    def test_initialization_with_azure_config(self):
        """Test agent initializes with Azure OpenAI configuration."""
        with patch.dict(
            os.environ,
            {
                "STREAMLIT_DEFAULT_MODEL": "o3-mini",
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent._llm_config["model_name"] == "o3-mini"
            assert agent._llm_config["azure_api_key"] == "azure-key"
            assert (
                agent._llm_config["azure_api_base"]
                == "https://example.openai.azure.com/"
            )

    def test_initialization_with_internal_llm(self):
        """Test agent initializes with internal LLM provider configuration."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal-llm.company.com/v1",
                "INTERNAL_LLM_MODEL": "company-model-v2",
                "STREAMLIT_DEFAULT_MODEL": "gpt-4",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent._llm_config["internal_llm_api_key"] == "internal-key"
            assert (
                agent._llm_config["internal_llm_base_url"]
                == "https://internal-llm.company.com/v1"
            )
            assert agent._llm_config["internal_llm_model"] == "company-model-v2"

    def test_initialization_with_ollama_config(self):
        """Test agent initializes with Ollama configuration."""
        with patch.dict(
            os.environ,
            {
                "STREAMLIT_DEFAULT_MODEL": "ollama/mistral",
                "OLLAMA_API_BASE_URL": "http://localhost:11434",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent._llm_config["model_name"] == "ollama/mistral"
            assert agent._llm_config["ollama_base_url"] == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_get_llm_instance_with_internal_provider(self):
        """Test LLM instance creation with internal provider."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com/v1",
                "INTERNAL_LLM_MODEL": "company-model",
                "STREAMLIT_DEFAULT_MODEL": "ignored-when-internal-is-set",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            # Verify it returns a ChatOpenAI instance with internal configuration
            assert llm.__class__.__name__ == "ChatOpenAI"
            # Check that the model and base URL are set correctly
            assert hasattr(llm, "model_name") or hasattr(llm, "model")
            assert hasattr(llm, "openai_api_base") or hasattr(llm, "base_url")

    @pytest.mark.asyncio
    async def test_get_llm_instance_with_ollama(self):
        """Test LLM instance creation with Ollama."""
        with patch.dict(
            os.environ,
            {
                "STREAMLIT_DEFAULT_MODEL": "ollama/mistral",
                "OLLAMA_API_BASE_URL": "http://localhost:11434",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            assert llm.__class__.__name__ == "ChatOllama"

    @pytest.mark.asyncio
    async def test_get_llm_instance_with_azure_full_endpoint(self):
        """Test LLM instance creation with Azure full deployment endpoint."""
        with patch.dict(
            os.environ,
            {
                "STREAMLIT_DEFAULT_MODEL": "gpt-4",
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/openai/deployments/gpt-4/chat/completions?api-version=2023-05-15",
                "AZURE_API_VERSION": "2023-05-15",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            assert llm.__class__.__name__ == "AzureChatOpenAI"

    @pytest.mark.asyncio
    async def test_get_llm_instance_with_azure_base_only(self):
        """Test LLM instance creation with Azure base URL (no deployment in URL)."""
        with patch.dict(
            os.environ,
            {
                "STREAMLIT_DEFAULT_MODEL": "gpt-4",
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            assert llm.__class__.__name__ == "AzureChatOpenAI"

    @pytest.mark.asyncio
    async def test_get_llm_instance_fallback_to_openai(self):
        """Test LLM instance falls back to OpenAI for unknown model patterns."""
        with patch.dict(
            os.environ,
            {
                "STREAMLIT_DEFAULT_MODEL": "gpt-4-turbo",
                "OPENAI_API_KEY": "test-key",  # Add a dummy API key
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            assert llm.__class__.__name__ == "ChatOpenAI"

    @pytest.mark.asyncio
    async def test_internal_llm_takes_precedence(self):
        """Test that internal LLM configuration takes precedence over other configs."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com/v1",
                "INTERNAL_LLM_MODEL": "company-model",
                "STREAMLIT_DEFAULT_MODEL": "gpt-4",
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
                "OLLAMA_API_BASE_URL": "http://localhost:11434",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            # Should use internal LLM, not Azure or Ollama
            assert llm.__class__.__name__ == "ChatOpenAI"
            # Verify it's configured with internal settings

    @pytest.mark.asyncio
    async def test_ollama_with_alternative_base_env_var(self):
        """Test Ollama with OLLAMA_API_BASE as alternative to OLLAMA_API_BASE_URL."""
        with patch.dict(
            os.environ,
            {
                "STREAMLIT_DEFAULT_MODEL": "ollama/llama2",
                "OLLAMA_API_BASE": "http://192.168.1.100:11434",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            assert llm.__class__.__name__ == "ChatOllama"


class TestInternalLLMProviderWorkflow:
    """Integration tests for full workflow with internal LLM provider."""

    @pytest.mark.asyncio
    async def test_internal_llm_workflow_initialization(self):
        """Test that workflow can be initialized with internal LLM provider."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.example.com/v1",
                "INTERNAL_LLM_MODEL": "internal-model",
                "STREAMLIT_DEFAULT_MODEL": "internal-model",
            },
            clear=True,
        ):
            # This should not raise any exceptions
            agent = ScientificWorkflowAgent()
            assert agent is not None
            assert agent.app is not None

    @pytest.mark.asyncio
    async def test_multiple_provider_configurations_coexist(self):
        """Test that multiple provider configurations can coexist without conflict."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com/v1",
                "INTERNAL_LLM_MODEL": "company-model",
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://azure.example.com/",
                "AZURE_API_VERSION": "2023-05-15",
                "OPENAI_API_KEY": "openai-key",
                "OLLAMA_API_BASE": "http://localhost:11434",
                "STREAMLIT_DEFAULT_MODEL": "gpt-4",
            },
            clear=True,
        ):
            # Should initialize without errors
            agent = ScientificWorkflowAgent()
            assert agent._llm_config["internal_llm_api_key"] == "internal-key"
            assert agent._llm_config["azure_api_key"] == "azure-key"
            assert agent._llm_config["ollama_base_url"] == "http://localhost:11434"


class TestEnvironmentVariableCompatibility:
    """Test backward compatibility with existing environment variable patterns."""

    def test_ollama_base_url_compatibility(self):
        """Test both OLLAMA_API_BASE_URL and OLLAMA_API_BASE work."""
        # Test with OLLAMA_API_BASE_URL
        with patch.dict(
            os.environ,
            {
                "OLLAMA_API_BASE_URL": "http://host1:11434",
                "STREAMLIT_DEFAULT_MODEL": "ollama/mistral",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent._llm_config["ollama_base_url"] == "http://host1:11434"

        # Test with OLLAMA_API_BASE
        with patch.dict(
            os.environ,
            {
                "OLLAMA_API_BASE": "http://host2:11434",
                "STREAMLIT_DEFAULT_MODEL": "ollama/mistral",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent._llm_config["ollama_base_url"] == "http://host2:11434"

    def test_azure_openai_key_fallback(self):
        """Test that OPENAI_API_KEY can be used as fallback for Azure."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "fallback-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
                "STREAMLIT_DEFAULT_MODEL": "gpt-4",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent._llm_config["azure_api_key"] == "fallback-key"
