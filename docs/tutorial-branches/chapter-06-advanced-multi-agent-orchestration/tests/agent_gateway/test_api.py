import pytest
from fastapi.testclient import TestClient
import os
from unittest.mock import patch, MagicMock

# Set an environment variable to disable auth for testing
os.environ["AGENT_GATEWAY_AUTH_ENABLED"] = "false"

from agentic_framework_pkg.agent_gateway.app import app, tool_manager


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_tool_manager_before_each_test():
    """Fixture to clear the tool manager's state before each test."""
    tool_manager.registered_tools.clear()
    yield


def test_register_http_tool_success(client: TestClient):
    """Test successful registration of a valid HTTP tool."""
    http_tool_config = {
        "name": "test_http_tool",
        "description": "A test HTTP tool.",
        "args_schema": {"query": {"type": "string"}},
        "invocation": {
            "protocol": "http",
            "connection": {"url": "http://example.com/tool"},
        },
        "acl": {"global": True},
    }
    response = client.post("/v1/tools/register", json=http_tool_config)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "test_http_tool" in tool_manager.registered_tools


def test_register_stdio_tool_success(client: TestClient):
    """Test successful registration of a valid stdio tool."""
    stdio_tool_config = {
        "name": "test_stdio_tool",
        "description": "A test stdio tool.",
        "args_schema": {"message": {"type": "string"}},
        "invocation": {
            "protocol": "stdio",
            "connection": {"command": ["echo", "hello"]},
        },
        "acl": {"global": True},
    }
    response = client.post("/v1/tools/register", json=stdio_tool_config)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "test_stdio_tool" in tool_manager.registered_tools


def test_register_tool_invalid_protocol(client: TestClient):
    """Test registration of a tool with an unsupported protocol."""
    invalid_tool_config = {
        "name": "invalid_protocol_tool",
        "description": "A tool with an invalid protocol.",
        "args_schema": {},
        "invocation": {"protocol": "invalid_protocol", "connection": {}},
    }
    response = client.post("/v1/tools/register", json=invalid_tool_config)
    assert response.status_code == 400
    assert "Unsupported tool protocol" in response.json()["detail"]


@patch("agentic_framework_pkg.agent_gateway.external_tool_manager._create_http_tool")
def test_chat_completions_with_dynamic_http_tool(
    mock_create_http_tool, client: TestClient
):
    """Test that the agent can use a dynamically registered HTTP tool."""
    # 1. Mock the tool's behavior
    mock_tool_coroutine = MagicMock()
    # Since the tool's coroutine returns a string, we mock it to return a JSON string
    mock_tool_coroutine.return_value = '{"result": "success from http tool"}'

    mock_langchain_tool = MagicMock()
    mock_langchain_tool.name = "dynamic_http_tool"
    mock_langchain_tool.description = "A dynamic HTTP tool."
    mock_langchain_tool.coroutine = mock_tool_coroutine
    mock_langchain_tool.args_schema = MagicMock()

    mock_create_http_tool.return_value = mock_langchain_tool

    # 2. Register the tool
    http_tool_config = {
        "name": "dynamic_http_tool",
        "description": "A dynamic HTTP tool.",
        "args_schema": {"param": {"type": "string"}},
        "invocation": {"protocol": "http", "connection": {"url": "http://fake.url"}},
        "acl": {"global": True},
    }
    client.post("/v1/tools/register", json=http_tool_config)

    # 3. Mock the agent's arun method to simulate the LLM's response
    with patch(
        "agentic_framework_pkg.scientific_workflow.langchain_agent.ScientificWorkflowAgent.arun"
    ) as mock_arun:
        # Simulate the agent deciding to use the tool and returning its output
        mock_arun.return_value = {
            "output": "The dynamic tool says: success from http tool"
        }

        # 4. Make a chat request that should trigger the tool
        chat_request = {
            "model": "agentic-framework/scientific-agent-v1",
            "messages": [{"role": "user", "content": "Use the dynamic http tool"}],
        }
        response = client.post("/v1/chat/completions", json=chat_request)

        assert response.status_code == 200
        assert (
            "The dynamic tool says: success from http tool"
            in response.json()["choices"][0]["message"]["content"]
        )


@patch("agentic_framework_pkg.agent_gateway.stdio_tool_wrapper._run_stdio_tool")
def test_chat_completions_with_dynamic_stdio_tool(mock_run_stdio, client: TestClient):
    """Test that the agent can use a dynamically registered stdio tool."""
    # 1. Mock the underlying stdio execution function
    mock_run_stdio.return_value = (
        '{"status": "success", "echo": "Message from stdio tool"}'
    )

    # 2. Register the stdio tool
    stdio_tool_config = {
        "name": "dynamic_stdio_tool",
        "description": "A dynamic stdio tool.",
        "args_schema": {"message": {"type": "string"}},
        "invocation": {
            "protocol": "stdio",
            "connection": {"command": ["echo", "hello"]},
        },
        "acl": {"global": True},
    }
    client.post("/v1/tools/register", json=stdio_tool_config)

    # 3. Mock the agent's arun method and make a chat request
    with patch(
        "agentic_framework_pkg.scientific_workflow.langchain_agent.ScientificWorkflowAgent.arun"
    ) as mock_arun:
        mock_arun.return_value = {"output": "Message from stdio tool"}

        chat_request = {
            "model": "agentic-framework/scientific-agent-v1",
            "messages": [
                {
                    "role": "user",
                    "content": "Use the dynamic stdio tool with message 'hello'",
                }
            ],
        }
        response = client.post("/v1/chat/completions", json=chat_request)

        assert response.status_code == 200
        assert (
            "Message from stdio tool"
            in response.json()["choices"][0]["message"]["content"]
        )
        mock_arun.assert_called_once()


def test_chat_completions_with_docker_stdio_tool(client: TestClient):
    """Test that the agent can use a dynamically registered stdio tool with a Docker invocation."""
    # 1. Register the stdio tool with Docker invocation
    docker_stdio_tool_config = {
        "name": "docker_echo_tool",
        "description": "A stdio tool running inside a Docker container.",
        "args_schema": {"message": {"type": "string"}},
        "invocation": {
            "protocol": "stdio",
            "connection": {
                "command": [
                    "python3",
                    "/app/src/agentic_framework_pkg/agent_gateway/tools/echo_docker_tool.py",
                ]
            },
        },
        "acl": {"global": True},
    }
    response = client.post("/v1/tools/register", json=docker_stdio_tool_config)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "docker_echo_tool" in tool_manager.registered_tools

    # 2. Mock the agent's arun method and make a chat request
    with patch(
        "agentic_framework_pkg.scientific_workflow.langchain_agent.ScientificWorkflowAgent.arun"
    ) as mock_arun:
        mock_arun.return_value = {"output": "Docker tool received: hello from docker"}

        chat_request = {
            "model": "agentic-framework/scientific-agent-v1",
            "messages": [
                {
                    "role": "user",
                    "content": "Use the docker_echo_tool with message 'hello from docker'",
                }
            ],
        }
        response = client.post("/v1/chat/completions", json=chat_request)

        assert response.status_code == 200
        assert (
            "Docker tool received: hello from docker"
            in response.json()["choices"][0]["message"]["content"]
        )
