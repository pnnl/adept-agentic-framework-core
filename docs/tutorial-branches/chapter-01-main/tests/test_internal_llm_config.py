"""
Tests for internal LLM provider configuration in chapter-01.
Validates that internal LLM settings are properly detected and prioritized.
"""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from agentic_framework_pkg.scientific_workflow.langchain_agent import (
    ScientificWorkflowAgent,
)


class TestInternalLLMConfiguration:
    """Test suite for internal LLM provider configuration in ScientificWorkflowAgent."""

    def test_initialization_with_internal_llm(self):
        """Test agent initializes with internal LLM provider as highest priority."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal-llm.company.com",
                "INTERNAL_LLM_MODEL": "company-model-v2",
                "AZURE_API_KEY": "azure-key",  # Should be ignored
                "AZURE_API_BASE": "https://example.openai.azure.com/",  # Should be ignored
                "AZURE_API_VERSION": "2023-05-15",  # Should be ignored
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            # Verify internal LLM is used (ChatOpenAI with custom base_url)
            assert agent.llm is not None
            assert agent.llm.__class__.__name__ == "ChatOpenAI"
            # Internal LLM uses ChatOpenAI with custom base_url, not AzureChatOpenAI
            assert hasattr(agent.llm, "base_url") or hasattr(
                agent.llm, "openai_api_base"
            )

    def test_initialization_with_azure_when_no_internal(self):
        """Test agent falls back to Azure when internal LLM not configured."""
        with patch.dict(
            os.environ,
            {
                "LANGCHAIN_LLM_MODEL": "gpt-4-deployment",
                "AZURE_API_KEY": "azure-key",
                "AZURE_API_BASE": "https://example.openai.azure.com/",
                "AZURE_API_VERSION": "2023-05-15",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent.llm is not None
            assert agent.llm.__class__.__name__ == "AzureChatOpenAI"

    def test_initialization_with_openai_when_no_internal_or_azure(self):
        """Test agent falls back to OpenAI when neither internal nor Azure configured."""
        with patch.dict(
            os.environ,
            {
                "LANGCHAIN_LLM_MODEL": "gpt-4",
                "OPENAI_API_KEY": "openai-key",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent.llm is not None
            assert agent.llm.__class__.__name__ == "ChatOpenAI"

    def test_reasoning_model_max_tokens(self):
        """Test that reasoning models (o4-mini, o3-mini) get max_tokens=4000."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com",
                "INTERNAL_LLM_MODEL": "o4-mini-project",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent.llm is not None
            # Verify max_tokens is set (implementation detail)
            assert hasattr(agent.llm, "max_tokens")
            assert agent.llm.max_tokens == 4000

    def test_non_reasoning_model_max_tokens(self):
        """Test that non-reasoning models get max_tokens=1000."""
        with patch.dict(
            os.environ,
            {
                "INTERNAL_LLM_API_KEY": "internal-key",
                "INTERNAL_LLM_BASE_URL": "https://internal.company.com",
                "INTERNAL_LLM_MODEL": "gpt-4-compatible",
            },
            clear=True,
        ):
            agent = ScientificWorkflowAgent()
            assert agent.llm is not None
            assert hasattr(agent.llm, "max_tokens")
            assert agent.llm.max_tokens == 1000

    def test_incomplete_internal_llm_config_falls_back(self):
        """Test that incomplete internal LLM config causes fallback to cloud providers."""
        # Only API key set, missing base URL and model
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
            agent = ScientificWorkflowAgent()
            # Should fall back to OpenAI
            assert agent.llm is not None
            assert agent.llm.__class__.__name__ == "ChatOpenAI"
            # Should not have custom base_url since using standard OpenAI
            if hasattr(agent.llm, "base_url"):
                # If base_url exists, it should be None or default OpenAI URL
                assert agent.llm.base_url is None or "openai.com" in str(
                    agent.llm.base_url
                )
