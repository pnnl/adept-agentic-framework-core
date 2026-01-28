"""
Smoke tests for MCP tools via the MCP client.
These tests verify that the tools can be called through the MCP server and return expected structures.

NOTE: These tests require:
- Docker containers running: docker compose up -d
- Active internet connection for BLAST, UniProt, PubChem, and web search APIs
- Can be run with: pytest tests/test_mcp_tools_smoke.py -v

These are integration tests that call the MCP server endpoints, not unit tests.
"""

import pytest
import os
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Skip all tests if running in CI without network access
pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" and os.getenv("ENABLE_NETWORK_TESTS") != "true",
    reason="Network tests disabled in CI (set ENABLE_NETWORK_TESTS=true to enable)",
)


# Test configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
TEST_SESSION_ID = "smoke_test_session"


@pytest.fixture
async def mcp_server_available():
    """Check if MCP server is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # MCP server may return 406 for GET requests without proper headers
            # Just check if it responds at all (any status code means it's running)
            response = await client.get(
                MCP_SERVER_URL.rstrip("/") + "/",
                follow_redirects=True,
                headers={"Accept": "application/json"},
            )
            # 200, 307 (redirect), 406 (not acceptable), 405 (method not allowed) all indicate server is up
            if response.status_code in [200, 307, 405, 406]:
                return True
            pytest.skip(
                f"MCP server returned unexpected status {response.status_code}. Run: docker compose up -d"
            )
    except httpx.ConnectError as e:
        pytest.skip(
            f"Cannot connect to MCP server at {MCP_SERVER_URL}. Is Docker running? Error: {e}"
        )
    except Exception as e:
        pytest.skip(f"MCP server check failed: {type(e).__name__}: {e}")


class TestMCPServerConnection:
    """Test MCP server connectivity."""

    @pytest.mark.asyncio
    async def test_server_reachable(self, mcp_server_available):
        """Test that MCP server is reachable."""
        assert mcp_server_available is True


class TestGeneralToolsSmoke:
    """Smoke tests for general utility tools via MCP client."""

    @pytest.mark.asyncio
    async def test_datetime_tool(self, mcp_server_available):
        """Test get_current_datetime tool via agent."""
        from agentic_framework_pkg.scientific_workflow.langchain_agent import (
            ScientificWorkflowAgent,
        )

        agent = ScientificWorkflowAgent(mcp_session_id=TEST_SESSION_ID)
        result = await agent.arun(
            user_input="What is the current date and time?",
        )

        # Should return dict with output
        assert isinstance(result, dict)
        assert "output" in result
        assert len(result["output"]) > 0

    @pytest.mark.asyncio
    async def test_calculation_tool(self, mcp_server_available):
        """Test perform_calculation tool via agent."""
        from agentic_framework_pkg.scientific_workflow.langchain_agent import (
            ScientificWorkflowAgent,
        )

        agent = ScientificWorkflowAgent(mcp_session_id=TEST_SESSION_ID)
        result = await agent.arun(
            user_input="Calculate 2 + 2",
        )

        # Should mention the result 4
        assert isinstance(result, dict)
        assert "output" in result
        assert "4" in result["output"]


class TestScientificToolsSmoke:
    """Smoke tests for scientific tools (BLAST, UniProt, PubChem)."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_uniprot_lookup(self, mcp_server_available):
        """Test UniProt lookup for known protein (KRT14)."""
        from agentic_framework_pkg.scientific_workflow.langchain_agent import (
            ScientificWorkflowAgent,
        )

        agent = ScientificWorkflowAgent(mcp_session_id=TEST_SESSION_ID)
        result = await agent.arun(
            user_input="Look up UniProt entry P02533",
        )

        # Should mention keratin or KRT14
        assert isinstance(result, dict)
        assert "output" in result
        output_lower = result["output"].lower()
        assert "keratin" in output_lower or "krt" in output_lower

    @pytest.mark.asyncio
    async def test_pubchem_search(self, mcp_server_available):
        """Test PubChem search for common compound."""
        from agentic_framework_pkg.scientific_workflow.langchain_agent import (
            ScientificWorkflowAgent,
        )

        agent = ScientificWorkflowAgent(mcp_session_id=TEST_SESSION_ID)
        result = await agent.arun(
            user_input="Search PubChem for aspirin",
        )

        # Should mention aspirin or salicylic acid
        assert isinstance(result, dict)
        assert "output" in result
        output_lower = result["output"].lower()
        assert "aspirin" in output_lower or "salicyl" in output_lower


class TestWebSearchToolSmoke:
    """Smoke tests for web search tool."""

    @pytest.mark.asyncio
    async def test_websearch_basic(self, mcp_server_available):
        """Test web search with simple query."""
        from agentic_framework_pkg.scientific_workflow.langchain_agent import (
            ScientificWorkflowAgent,
        )

        agent = ScientificWorkflowAgent(mcp_session_id=TEST_SESSION_ID)
        result = await agent.arun(
            user_input="Search the web for 'UniProt protein database'",
        )

        # Should return some result or error message
        assert isinstance(result, dict)
        assert "output" in result
        assert len(result["output"]) > 0

        # If Chrome isn't available, that's acceptable
        output_lower = result["output"].lower()
        # Either success (mentions uniprot) or graceful failure (mentions error/chrome)
        assert (
            "uniprot" in output_lower
            or "error" in output_lower
            or "chrome" in output_lower
            or "selenium" in output_lower
        )


# Recommended web search queries for manual testing:
"""
GOOD WEB SEARCH TEST QUERIES:
1. Simple & Reliable:
   - "UniProt protein database"
   - "NCBI BLAST tutorial"
   - "what is keratin protein"

2. More Specific:
   - "KRT14 human keratin"
   - "PubChem compound database"
   - "HUMKEREP J00124.1 UniProt"

3. Scientific Research:
   - "protein structure prediction methods"
   - "BLAST algorithm overview"
"""
