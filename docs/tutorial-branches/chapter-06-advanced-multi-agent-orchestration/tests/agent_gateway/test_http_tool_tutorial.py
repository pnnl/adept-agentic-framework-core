import pytest
from fastapi.testclient import TestClient
import os
from unittest.mock import patch, MagicMock
import json
import aiohttp  # Import aiohttp for mocking

# Set an environment variable to disable auth for testing
os.environ["AGENT_GATEWAY_AUTH_ENABLED"] = "false"

# Import app and tool_manager after setting the environment variable
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


@patch("aiohttp.ClientSession.request")
def test_tutorial_http_tool_registration(mock_request, client: TestClient):
    """Tests the registration and simulated use of an HTTP-based tool."""
    # 1. Mock the external HTTP API response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.content_type = "application/json"
    mock_response.json.return_value = {"temperature": 25, "conditions": "Sunny"}
    mock_response.raise_for_status.return_value = None  # Ensure no HTTP errors
    mock_request.return_value.__aenter__.return_value = mock_response
    mock_request.return_value.__aexit__.return_value = None

    # 2. Register the HTTP tool
    http_tool_config = {
        "name": "get_weather_conditions",
        "description": "Fetches current weather conditions for a specified city.",
        "args_schema": {
            "city": {"type": "string"},
            "unit": {"type": "string", "default": "celsius"},
        },
        "invocation": {
            "protocol": "http",
            "connection": {
                "url": "https://api.example.com/weather/current",
                "method": "GET",
                "headers": {"X-API-Key": "TEST_API_KEY"},
            },
        },
        "acl": {"global": True},
    }
    response = client.post("/v1/tools/register", json=http_tool_config)
    assert response.status_code == 200
    assert "get_weather_conditions" in tool_manager.registered_tools

    # 3. Make a chat request to trigger the tool
    chat_request = {
        "model": "agentic-framework/scientific-agent-v1",
        "messages": [{"role": "user", "content": "What is the weather in Seattle?"}],
    }

    # 4. Mock the agent's arun method to simulate the LLM's response
    with patch(
        "agentic_framework_pkg.scientific_workflow.langchain_agent.ScientificWorkflowAgent.arun"
    ) as mock_arun:
        # Simulate the agent deciding to use the tool and returning its output
        mock_arun.return_value = {
            "output": "The weather in Seattle is 25 degrees Celsius and Sunny."
        }

        response = client.post("/v1/chat/completions", json=chat_request)

        assert response.status_code == 200
        assert (
            "The weather in Seattle is 25 degrees Celsius and Sunny."
            in response.json()["choices"][0]["message"]["content"]
        )

        # Verify that the agent was instantiated and its arun method was called
        mock_arun.assert_called_once()
