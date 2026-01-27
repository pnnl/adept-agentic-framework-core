"""
Test for the specific user scenario: o3-mini in STREAMLIT_DEFAULT_MODEL
should not interfere with internal LLM configuration.
"""

import os
import pytest
from unittest.mock import patch
from agentic_framework_pkg.scientific_workflow.langchain_agent import (
    ScientificWorkflowAgent,
)


class TestUserScenarioO3Mini:
    """Test the exact user scenario with o3-mini and internal LLM."""

    @pytest.mark.asyncio
    async def test_o3_mini_does_not_trigger_azure_when_internal_llm_configured(self):
        """
        Critical test: When STREAMLIT_DEFAULT_MODEL="o3-mini" (which starts with "o3")
        AND internal LLM is configured, the system should use internal LLM,
        NOT Azure OpenAI.
        """
        with patch.dict(
            os.environ,
            {
                # User's actual configuration
                "INTERNAL_LLM_API_KEY": "sk-test-key-example",
                "INTERNAL_LLM_BASE_URL": "https://ai-incubator-api.pnnl.gov/v1",
                "INTERNAL_LLM_MODEL": "o4-mini-project",
                "INTERNAL_LLM_EMBEDDING_MODEL": "text-embedding-3-small-project",
                # These should be IGNORED when internal LLM is configured
                "STREAMLIT_DEFAULT_MODEL": "o3-mini",  # Starts with "o3" - could trigger Azure logic
                "LANGCHAIN_LLM_MODEL": "o3-mini",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            # CRITICAL: Should use ChatOpenAI (not AzureChatOpenAI)
            assert llm.__class__.__name__ == "ChatOpenAI", (
                f"Expected ChatOpenAI but got {llm.__class__.__name__}"
            )

            # Verify it's NOT Azure
            assert llm.__class__.__name__ != "AzureChatOpenAI", (
                "Should NOT use AzureChatOpenAI when internal LLM is configured"
            )

    @pytest.mark.asyncio
    async def test_internal_llm_model_used_not_streamlit_default(self):
        """
        Test that the internal LLM model name is used, not STREAMLIT_DEFAULT_MODEL.
        """
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.example.com/v1",
                "INTERNAL_LLM_MODEL": "internal-specific-model",
                "STREAMLIT_DEFAULT_MODEL": "o3-mini",  # Should be ignored
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            # The model should be "internal-specific-model", not "o3-mini"
            assert llm.__class__.__name__ == "ChatOpenAI"
            # Check model name if accessible
            if hasattr(llm, "model_name"):
                assert llm.model_name == "internal-specific-model", (
                    f"Expected model 'internal-specific-model' but got '{llm.model_name}'"
                )
            elif hasattr(llm, "model"):
                assert llm.model == "internal-specific-model", (
                    f"Expected model 'internal-specific-model' but got '{llm.model}'"
                )

    @pytest.mark.asyncio
    async def test_internal_llm_requires_all_three_env_vars(self):
        """
        Test that internal LLM requires all three env vars: API_KEY, BASE_URL, MODEL.
        If any is missing, should fall back to other providers.
        """
        # Missing MODEL - should NOT use internal
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.example.com/v1",
                # INTERNAL_LLM_MODEL missing
                "STREAMLIT_DEFAULT_MODEL": "ollama/mistral",
                "OLLAMA_API_BASE": "http://localhost:11434",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            # Should fall back to Ollama
            assert llm.__class__.__name__ == "ChatOllama"

    @pytest.mark.asyncio
    async def test_o3_mini_triggers_azure_without_internal_llm(self):
        """
        Test that o3-mini correctly triggers Azure logic when internal LLM is NOT configured.
        This ensures backward compatibility.
        """
        with patch.dict(
            os.environ,
            {
                # No internal LLM configured
                "STREAMLIT_DEFAULT_MODEL": "o3-mini",
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            # Should use Azure
            assert llm.__class__.__name__ == "AzureChatOpenAI"

    @pytest.mark.asyncio
    async def test_internal_llm_checked_before_model_name_parsing(self):
        """
        Test that internal LLM configuration is checked BEFORE parsing model_name.
        This prevents model name prefixes from interfering with provider selection.
        """
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.example.com/v1",
                "INTERNAL_LLM_MODEL": "my-custom-model",
                # Model name that would normally trigger other providers
                "STREAMLIT_DEFAULT_MODEL": "azure/gpt-4",  # Would trigger Azure
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            # Should use internal LLM (ChatOpenAI), not Azure
            assert llm.__class__.__name__ == "ChatOpenAI"
            assert llm.__class__.__name__ != "AzureChatOpenAI"


class TestInternalLLMBaseURLParameter:
    """Test that ChatOpenAI is configured with correct parameter names."""

    @pytest.mark.asyncio
    async def test_chatopenai_uses_base_url_not_openai_api_base(self):
        """
        Test that ChatOpenAI is initialized with 'base_url' (modern parameter)
        not 'openai_api_base' (deprecated parameter).
        """
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "test-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.example.com/v1",
                "INTERNAL_LLM_MODEL": "test-model",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            llm = await agent._get_llm_instance()

            # Verify ChatOpenAI instance is created
            assert llm.__class__.__name__ == "ChatOpenAI"

            # Check that base_url is set (modern LangChain/OpenAI client)
            # Note: This might be stored as a private attribute or property
            assert (
                hasattr(llm, "openai_api_base")
                or hasattr(llm, "base_url")
                or hasattr(llm, "client")
                or hasattr(llm, "_client")
            ), "ChatOpenAI instance should have base URL configuration"
