import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from langchain_core.messages import AIMessage


@pytest.fixture(autouse=True)
def mock_llm_for_agent_gateway():
    """Mock LLMAgnosticClient so ScientificWorkflowAgent.__init__ can run without real LLM credentials."""
    with (
        patch(
            "agentic_framework_pkg.scientific_workflow.langchain_agent.LLMAgnosticClient",
            autospec=True,
        ) as MockLLMClient,
        patch(
            "agentic_framework_pkg.scientific_workflow.mcp_langchain_tools.MCPClient",
            autospec=True,
        ),
    ):
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="LLM response"))
        mock_llm.invoke = MagicMock(return_value=AIMessage(content="LLM response"))
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        mock_instance = MockLLMClient.return_value
        mock_instance.get_langchain_chat_model.return_value = (mock_llm, "mock_model")
        yield
