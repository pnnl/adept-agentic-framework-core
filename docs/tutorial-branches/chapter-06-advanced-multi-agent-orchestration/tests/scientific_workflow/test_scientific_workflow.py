import pytest
import os
import json
from unittest.mock import patch, AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph, END
from langchain_core.outputs import ChatGeneration, ChatResult


# Mock environment variables for consistent testing
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test_openai_key",
            "AZURE_API_KEY": "test_azure_key",
            "AZURE_API_BASE": "https://test.openai.azure.com/",
            "AZURE_API_VERSION": "2024-02-01",
            "NVIDIA_API_KEY": "test_nvidia_key",
            "NVIDIA_MULTI_MODAL_MODEL_NAME": "test_nvidia_model",
            "DEFAULT_LLM_MODEL": "test_default_model",
            "EMBEDDING_DEFAULT_MODEL": "test_embedding_model",
            "RAG_DEFAULT_MODEL": "test_rag_model",
            "STREAMLIT_DEFAULT_MODEL": "test_streamlit_model",
            "LITELLM_VERBOSE": "False",
            "USE_SPLIT_STREAM_GRAPH": "false",
            "USE_CHECKPOINTING": "false",
        },
        clear=True,
    ):  # clear=True ensures a clean slate for each test
        yield


# Mock LLMAgnosticClient and its methods
@pytest.fixture
def mock_llm_agnostic_client():
    with patch(
        "agentic_framework_pkg.core.llm_agnostic_layer.LLMAgnosticClient", autospec=True
    ) as MockLLMAgnosticClient:
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="LLM response"))
        mock_llm.invoke = MagicMock(return_value=AIMessage(content="LLM response"))
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        mock_llm_agnostic_client_instance = MockLLMAgnosticClient.return_value
        mock_llm_agnostic_client_instance.get_langchain_chat_model.return_value = (
            mock_llm,
            "mock_model_name",
        )

        yield mock_llm_agnostic_client_instance


# Mock MCPClient for mcp_langchain_tools
@pytest.fixture
def mock_mcp_client():
    # Patch fastmcp.Client directly where it's imported in mcp_langchain_tools.py
    with patch(
        "agentic_framework_pkg.scientific_workflow.mcp_langchain_tools.MCPClient",
        autospec=True,
    ) as MockMCPClient:
        # Create a mock instance that will be returned by the constructor
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value = (
            mock_client_instance  # For async with
        )
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.call_tool = AsyncMock(
            return_value=[
                MagicMock(
                    text=json.dumps(
                        {"status": "success", "result": "mock_mcp_tool_output"}
                    )
                )
            ]
        )

        MockMCPClient.return_value = (
            mock_client_instance  # What the constructor returns
        )
        yield mock_client_instance  # Yield the instance that will be used


# --- Tests for agent_state.py (TypedDict structure) ---
def test_agent_state_structure():
    from agentic_framework_pkg.scientific_workflow.agent_state import AgentState

    state = AgentState(messages=[], chat_history=[], full_tool_outputs=[])
    assert "messages" in state
    assert "chat_history" in state
    assert "full_tool_outputs" in state
    assert isinstance(state["messages"], list)
    assert isinstance(state["chat_history"], list)
    assert isinstance(state["full_tool_outputs"], list)


# --- Tests for graph_builder.py ---
@pytest.fixture
def graph_builder_instance(mock_llm_agnostic_client):
    from agentic_framework_pkg.scientific_workflow.graph_builder import (
        AgentGraphBuilder,
    )

    # Mock the LLM returned by get_langchain_chat_model
    mock_llm = mock_llm_agnostic_client.get_langchain_chat_model.return_value[0]

    # Mock a tool for the graph
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.ainvoke = AsyncMock(
        return_value=json.dumps({"status": "success", "output": "tool_output"})
    )
    mock_tool.invoke = MagicMock(
        return_value=json.dumps({"status": "success", "output": "tool_output"})
    )

    return AgentGraphBuilder(llm=mock_llm, tools=[mock_tool])


@pytest.mark.asyncio
async def test_graph_builder_call_model(graph_builder_instance):
    from agentic_framework_pkg.scientific_workflow.agent_state import AgentState

    state = AgentState(
        messages=[HumanMessage(content="Hello")], chat_history=[], full_tool_outputs=[]
    )
    result = await graph_builder_instance.call_model(state)
    assert result["messages"][0].content == "LLM response"


@pytest.mark.asyncio
async def test_graph_builder_should_continue():
    from agentic_framework_pkg.scientific_workflow.agent_state import AgentState
    from agentic_framework_pkg.scientific_workflow.graph_builder import (
        AgentGraphBuilder,
    )

    # Mock LLM and tools are not needed for should_continue
    builder = AgentGraphBuilder(llm=MagicMock(), tools=[])

    # Test continue (tool_calls exist)
    state_with_tool_calls = AgentState(
        messages=[
            AIMessage(
                content="", tool_calls=[{"id": "call_123", "name": "tool", "args": {}}]
            )
        ],
        chat_history=[],
        full_tool_outputs=[],
    )
    assert builder.should_continue(state_with_tool_calls) == "continue"

    # Test end (no tool_calls)
    state_no_tool_calls = AgentState(
        messages=[AIMessage(content="Final answer")],
        chat_history=[],
        full_tool_outputs=[],
    )
    assert builder.should_continue(state_no_tool_calls) == "end"


@pytest.mark.asyncio
async def test_graph_builder_custom_tool_node(graph_builder_instance):
    from agentic_framework_pkg.scientific_workflow.agent_state import AgentState

    # Mock the tool's ainvoke method to return a JSON string
    graph_builder_instance.tools[0].ainvoke.return_value = json.dumps(
        {"status": "success", "data": "processed"}
    )

    state = AgentState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "call_123", "name": "test_tool", "args": {"input": "data"}}
                ],
            )
        ],
        chat_history=[],
        full_tool_outputs=[],
    )
    result = await graph_builder_instance._custom_tool_node(state)
    assert result["messages"][0].content == json.dumps(
        {"status": "success", "data": "processed"}
    )
    assert result["full_tool_outputs"][0] == {"status": "success", "data": "processed"}
    graph_builder_instance.tools[0].ainvoke.assert_called_once_with({"input": "data"})


@pytest.mark.asyncio
async def test_graph_builder_build(graph_builder_instance):
    graph = graph_builder_instance.build()
    assert isinstance(graph, StateGraph)
    # Further tests could involve running the compiled graph, but that's more complex


# --- Tests for langchain_agent.py ---
@pytest.fixture
def scientific_workflow_agent_instance(mock_llm_agnostic_client, mock_mcp_client):
    from agentic_framework_pkg.scientific_workflow.langchain_agent import (
        ScientificWorkflowAgent,
    )

    return ScientificWorkflowAgent(mcp_session_id="test_session_id")


@pytest.mark.asyncio
async def test_scientific_workflow_agent_arun_no_tool(
    scientific_workflow_agent_instance, mock_llm_agnostic_client
):
    # Mock the compiled graph (runnable) directly. create_react_agent internally
    # pipes the model (model | parser), which breaks plain MagicMock since __or__
    # returns a new MagicMock that loses our configured ainvoke.
    # Testing arun's post-processing logic is the goal here; LangGraph internals
    # are not under test.
    scientific_workflow_agent_instance.runnable = MagicMock()
    scientific_workflow_agent_instance.runnable.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="Final answer from LLM.")]}
    )

    response = await scientific_workflow_agent_instance.arun(
        user_input="What is the capital of France?"
    )
    assert response["output"] == "Final answer from LLM."
    scientific_workflow_agent_instance.runnable.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_scientific_workflow_agent_arun_with_tool(
    scientific_workflow_agent_instance, mock_mcp_client, mock_llm_agnostic_client
):
    # Mock the compiled graph to return a state that includes tool execution results.
    tool_output = json.dumps({"status": "success", "echo": "Tool output: hello"})
    scientific_workflow_agent_instance.runnable = MagicMock()
    scientific_workflow_agent_instance.runnable.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Use the test_tool with message 'hello'"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "call_tool",
                            "name": "test_tool",
                            "args": {"message": "hello"},
                        }
                    ],
                ),
                ToolMessage(
                    content=tool_output, tool_call_id="call_tool", name="test_tool"
                ),
                AIMessage(content="Tool output: hello"),
            ]
        }
    )

    response = await scientific_workflow_agent_instance.arun(
        user_input="Use the test_tool with message 'hello'"
    )
    assert "Tool output: hello" in response["output"]


@pytest.mark.asyncio
async def test_scientific_workflow_agent_arun_with_docker_stdio_tool(
    scientific_workflow_agent_instance, mock_mcp_client, mock_llm_agnostic_client
):
    # Mock the compiled graph to simulate a Docker stdio tool execution.
    docker_output = json.dumps(
        {"status": "success", "echo": "Docker tool received: hello from docker"}
    )
    scientific_workflow_agent_instance.runnable = MagicMock()
    scientific_workflow_agent_instance.runnable.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(
                    content="Use the docker_echo_tool with message 'hello from docker'"
                ),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "call_docker_tool",
                            "name": "docker_echo_tool",
                            "args": {"message": "hello from docker"},
                        }
                    ],
                ),
                ToolMessage(
                    content=docker_output,
                    tool_call_id="call_docker_tool",
                    name="docker_echo_tool",
                ),
                AIMessage(content="Docker tool received: hello from docker"),
            ]
        }
    )

    response = await scientific_workflow_agent_instance.arun(
        user_input="Use the docker_echo_tool with message 'hello from docker'"
    )
    assert "Docker tool received: hello from docker" in response["output"]


# --- Tests for mcp_langchain_tools.py ---
@pytest.mark.asyncio
async def test_mcp_tool_wrapper_arun(mock_mcp_client):
    from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
        MCPToolWrapper,
    )

    tool_wrapper = MCPToolWrapper(
        name="TestTool",
        mcp_client_url="http://mock_mcp_server",
        actual_tool_name="test_mcp_tool",
        description="A test MCP tool.",
        mcp_session_id="test_session_123",
    )

    # Mock the return value of the underlying MCPClient.call_tool
    mock_mcp_client.call_tool.return_value = [
        MagicMock(text=json.dumps({"status": "success", "data": "mocked_data"}))
    ]

    result = await tool_wrapper._arun(param1="value1", param2="value2")
    assert result == json.dumps({"status": "success", "data": "mocked_data"})
    mock_mcp_client.call_tool.assert_called_once_with(
        "test_mcp_tool",
        {"param1": "value1", "param2": "value2", "mcp_session_id": "test_session_123"},
    )


@pytest.mark.asyncio
async def test_mcp_tool_wrapper_arun_no_session_id(mock_mcp_client):
    from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
        MCPToolWrapper,
    )

    tool_wrapper = MCPToolWrapper(
        name="TestTool",
        mcp_client_url="http://mock_mcp_server",
        actual_tool_name="test_mcp_tool",
        description="A test MCP tool.",
        mcp_session_id=None,  # No session ID set on wrapper
    )

    mock_mcp_client.call_tool.return_value = [
        MagicMock(text=json.dumps({"status": "success", "data": "mocked_data"}))
    ]

    result = await tool_wrapper._arun(param1="value1")
    assert result == json.dumps({"status": "success", "data": "mocked_data"})
    # Should be called without mcp_session_id in params
    mock_mcp_client.call_tool.assert_called_once_with(
        "test_mcp_tool", {"param1": "value1"}
    )


@pytest.mark.asyncio
async def test_mcp_tool_wrapper_arun_connection_refused(mock_mcp_client):
    from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
        MCPToolWrapper,
    )

    tool_wrapper = MCPToolWrapper(
        name="TestTool",
        mcp_client_url="http://mock_mcp_server",
        actual_tool_name="test_mcp_tool",
        description="A test MCP tool.",
    )
    mock_mcp_client.__aenter__.side_effect = ConnectionRefusedError(
        "Connection refused"
    )

    result = await tool_wrapper._arun(param1="value1")
    assert "Error: Could not connect to MCP server" in result


@pytest.mark.asyncio
async def test_mcp_tool_wrapper_arun_exception(mock_mcp_client):
    from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
        MCPToolWrapper,
    )

    tool_wrapper = MCPToolWrapper(
        name="TestTool",
        mcp_client_url="http://mock_mcp_server",
        actual_tool_name="test_mcp_tool",
        description="A test MCP tool.",
    )
    mock_mcp_client.call_tool.side_effect = Exception("Internal MCP error")

    result = await tool_wrapper._arun(param1="value1")
    assert "Error during MCP tool test_mcp_tool execution: Internal MCP error" in result
