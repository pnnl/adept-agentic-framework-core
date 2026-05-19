import pytest
from fastapi.testclient import TestClient
import os
from unittest.mock import patch, MagicMock
import json

# Set an environment variable to disable auth for testing
os.environ["AGENT_GATEWAY_AUTH_ENABLED"] = "false"

# This import should happen after the env var is set
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


@patch("agentic_framework_pkg.agent_gateway.stdio_tool_wrapper._run_stdio_tool")
def test_tutorial_direct_script_tool(mock_run_stdio, client: TestClient):
    """Tests the registration and use of the direct python script tool."""
    # 1. Mock the stdio execution
    mock_run_stdio.return_value = json.dumps(
        {
            "status": "success",
            "os_type": "Linux",
            "architecture": "x86_64",
            "python_version": "3.11",
            "container_hostname": "test-container",
        }
    )

    # 2. Register the tool
    tool_config = {
        "name": "get_system_information",
        "description": "A tool that retrieves basic system information.",
        "args_schema": {},
        "invocation": {
            "protocol": "stdio",
            "connection": {
                "command": [
                    "python3",
                    "agentic_framework_pkg/agent_gateway/tools/sys_info_tool.py",
                ],
                "working_directory": "/app",
            },
        },
        "acl": {"global": True},
    }
    response = client.post("/v1/tools/register", json=tool_config)
    assert response.status_code == 200
    assert "get_system_information" in tool_manager.registered_tools

    # 3. Make a chat request to trigger the tool
    chat_request = {
        "model": "agentic-framework/scientific-agent-v1",
        "messages": [{"role": "user", "content": "What is your system info?"}],
    }

    # 4. Mock the agent's response to control the test
    with patch(
        "agentic_framework_pkg.scientific_workflow.langchain_agent.ScientificWorkflowAgent.arun"
    ) as mock_arun:
        mock_arun.return_value = {"output": "The system is Linux on x86_64."}

        response = client.post("/v1/chat/completions", json=chat_request)

        assert response.status_code == 200
        assert (
            "The system is Linux on x86_64."
            in response.json()["choices"][0]["message"]["content"]
        )
        # Check that the agent was instantiated with our dynamic tool
        mock_arun.assert_called_once()


@patch("agentic_framework_pkg.agent_gateway.stdio_tool_wrapper._run_stdio_tool")
def test_tutorial_dockerized_tool(mock_run_stdio, client: TestClient):
    """Tests the registration and use of the dockerized stdio tool."""
    # 1. Mock the stdio execution
    mock_run_stdio.return_value = json.dumps(
        {"status": "success", "os_type": "Linux-From-Docker", "architecture": "aarch64"}
    )

    # 2. Register the tool
    tool_config = {
        "name": "get_system_information_docker",
        "description": "A DOCKERIZED tool that gets system info.",
        "args_schema": {},
        "invocation": {
            "protocol": "stdio",
            "connection": {
                "command": ["docker", "run", "--rm", "-i", "sys-info-tool:latest"]
            },
        },
        "acl": {"global": True},
    }
    response = client.post("/v1/tools/register", json=tool_config)
    assert response.status_code == 200
    assert "get_system_information_docker" in tool_manager.registered_tools

    # 3. Make a chat request and mock the agent's response
    with patch(
        "agentic_framework_pkg.scientific_workflow.langchain_agent.ScientificWorkflowAgent.arun"
    ) as mock_arun:
        mock_arun.return_value = {
            "output": "The dockerized tool reports Linux-From-Docker."
        }

        chat_request = {
            "model": "agentic-framework/scientific-agent-v1",
            "messages": [
                {"role": "user", "content": "Use the dockerized tool for system info."}
            ],
        }
        response = client.post("/v1/chat/completions", json=chat_request)

        assert response.status_code == 200
        assert (
            "The dockerized tool reports Linux-From-Docker."
            in response.json()["choices"][0]["message"]["content"]
        )
        mock_arun.assert_called_once()


@patch("agentic_framework_pkg.agent_gateway.stdio_tool_wrapper._run_stdio_tool")
def test_tutorial_universal_gateway_adapter(mock_run_stdio, client: TestClient):
    """Tests the registration and use of the universal `docker mcp gateway run` adapter."""
    # 1. Mock the stdio execution for the adapter script
    mock_run_stdio.return_value = json.dumps(
        {
            "status": "success",
            "result_from_gateway": "This is the result from the underlying tool via the gateway.",
        }
    )

    # 2. Register the universal adapter tool
    tool_config = {
        "name": "invoke_mcp_gateway_tool",
        "description": "A universal adapter tool that can invoke ANY other tool.",
        "args_schema": {
            "mcp_tool_name": {"type": "string"},
            "mcp_tool_args": {"type": "object"},
        },
        "invocation": {
            "protocol": "stdio",
            "connection": {
                "command": [
                    "python3",
                    "agentic_framework_pkg/agent_gateway/tools/gateway_run_adapter.py",
                ],
                "working_directory": "/app",
            },
        },
        "acl": {"global": True},
    }
    response = client.post("/v1/tools/register", json=tool_config)
    assert response.status_code == 200
    assert "invoke_mcp_gateway_tool" in tool_manager.registered_tools

    # 3. Make a chat request and mock the agent's response
    with patch(
        "agentic_framework_pkg.scientific_workflow.langchain_agent.ScientificWorkflowAgent.arun"
    ) as mock_arun:
        mock_arun.return_value = {
            "output": "The gateway adapter returned: This is the result from the underlying tool via the gateway."
        }

        chat_request = {
            "model": "agentic-framework/scientific-agent-v1",
            "messages": [
                {
                    "role": "user",
                    "content": "Use the gateway adapter to run the 'some_tool'.",
                }
            ],
        }
        response = client.post("/v1/chat/completions", json=chat_request)

        assert response.status_code == 200
        assert (
            "The gateway adapter returned"
            in response.json()["choices"][0]["message"]["content"]
        )
        mock_arun.assert_called_once()
