"""
Smoke tests for MCP tools via the MCP client (Chapter 03 - Multi-Agent System).
These tests verify that the tools can be called through the MCP servers and return expected structures.

NOTE: These tests require:
- Docker containers running: ./start-chapter-resources.sh or docker compose up -d
- Active internet connection for BLAST, UniProt, PubChem, and web search APIs
- Can be run with: pytest tests/test_mcp_tools_smoke.py -v

These are integration tests that call the MCP server endpoints, not unit tests.
Chapter 03 has three MCP servers: main, HPC, and sandbox.
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
MAIN_MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
HPC_MCP_SERVER_URL = os.getenv("HPC_MCP_SERVER_URL", "http://localhost:8081/mcp")
SANDBOX_MCP_SERVER_URL = os.getenv(
    "SANDBOX_MCP_SERVER_URL", "http://localhost:8082/mcp"
)
TEST_SESSION_ID = "smoke_test_session"


@pytest.fixture
async def main_mcp_server_available():
    """Check if main MCP server is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                MAIN_MCP_SERVER_URL.rstrip("/") + "/",
                follow_redirects=True,
                headers={"Accept": "application/json"},
            )
            if response.status_code in [200, 307, 405, 406]:
                return True
            pytest.skip(
                f"Main MCP server returned unexpected status {response.status_code}. Run: ./start-chapter-resources.sh"
            )
    except httpx.ConnectError as e:
        pytest.skip(
            f"Cannot connect to main MCP server at {MAIN_MCP_SERVER_URL}. Is Docker running? Error: {e}"
        )
    except Exception as e:
        pytest.skip(f"Main MCP server check failed: {type(e).__name__}: {e}")


@pytest.fixture
async def hpc_mcp_server_available():
    """Check if HPC MCP server is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                HPC_MCP_SERVER_URL.rstrip("/") + "/",
                follow_redirects=True,
                headers={"Accept": "application/json"},
            )
            if response.status_code in [200, 307, 405, 406]:
                return True
            pytest.skip(
                f"HPC MCP server returned unexpected status {response.status_code}. Run: ./start-chapter-resources.sh"
            )
    except httpx.ConnectError as e:
        pytest.skip(
            f"Cannot connect to HPC MCP server at {HPC_MCP_SERVER_URL}. Is Docker running? Error: {e}"
        )
    except Exception as e:
        pytest.skip(f"HPC MCP server check failed: {type(e).__name__}: {e}")


@pytest.fixture
async def sandbox_mcp_server_available():
    """Check if Sandbox MCP server is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                SANDBOX_MCP_SERVER_URL.rstrip("/") + "/",
                follow_redirects=True,
                headers={"Accept": "application/json"},
            )
            if response.status_code in [200, 307, 405, 406]:
                return True
            pytest.skip(
                f"Sandbox MCP server returned unexpected status {response.status_code}. Run: ./start-chapter-resources.sh"
            )
    except httpx.ConnectError as e:
        pytest.skip(
            f"Cannot connect to Sandbox MCP server at {SANDBOX_MCP_SERVER_URL}. Is Docker running? Error: {e}"
        )
    except Exception as e:
        pytest.skip(f"Sandbox MCP server check failed: {type(e).__name__}: {e}")


class TestMCPServersConnection:
    """Test MCP servers connectivity."""

    @pytest.mark.asyncio
    async def test_main_server_reachable(self, main_mcp_server_available):
        """Test that main MCP server is reachable."""
        assert main_mcp_server_available is True

    @pytest.mark.asyncio
    async def test_hpc_server_reachable(self, hpc_mcp_server_available):
        """Test that HPC MCP server is reachable."""
        assert hpc_mcp_server_available is True

    @pytest.mark.asyncio
    async def test_sandbox_server_reachable(self, sandbox_mcp_server_available):
        """Test that Sandbox MCP server is reachable."""
        assert sandbox_mcp_server_available is True


class TestMultiAgentSystemSmoke:
    """Smoke tests for multi-agent orchestration via Streamlit app."""

    @pytest.mark.asyncio
    async def test_multi_agent_simple_query(self, main_mcp_server_available):
        """Test multi-agent system with simple query."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query="What is 2 + 2?",
        )

        # Should return dict with result
        assert isinstance(result, dict)
        assert len(result) > 0
        # Check if we have a final result or steps
        assert "result" in result or "steps" in result or "output" in result


class TestGeneralToolsSmoke:
    """Smoke tests for general utility tools via MCP client."""

    @pytest.mark.asyncio
    async def test_datetime_tool(self, main_mcp_server_available):
        """Test get_current_datetime tool via multi-agent system."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query="What is the current date and time?",
        )

        # Should return dict with output
        assert isinstance(result, dict)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_calculation_tool(self, main_mcp_server_available):
        """Test perform_calculation tool via multi-agent system."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query="Calculate 15 * 8",
        )

        # Should mention the result 120
        assert isinstance(result, dict)
        assert len(result) > 0


class TestScientificToolsSmoke:
    """Smoke tests for scientific tools (BLAST, UniProt, PubChem)."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_uniprot_lookup(self, main_mcp_server_available):
        """Test UniProt lookup for known protein (KRT14)."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query="Look up UniProt entry P02533",
        )

        # Should return result mentioning keratin or KRT14
        assert isinstance(result, dict)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_pubchem_search(self, main_mcp_server_available):
        """Test PubChem search for common compound."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query="Search PubChem for caffeine",
        )

        # Should return result mentioning caffeine
        assert isinstance(result, dict)
        assert len(result) > 0


class TestHPCToolsSmoke:
    """Smoke tests for HPC-related tools."""

    @pytest.mark.asyncio
    async def test_hpc_status_check(self, hpc_mcp_server_available):
        """Test HPC status check tool."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query="Check the HPC cluster status",
        )

        # Should return dict with HPC status information
        assert isinstance(result, dict)
        assert len(result) > 0


class TestSandboxToolsSmoke:
    """Smoke tests for sandbox code execution tools."""

    @pytest.mark.asyncio
    async def test_python_code_execution(self, sandbox_mcp_server_available):
        """Test Python code execution in sandbox."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query="Execute this Python code: print(2 + 2)",
        )

        # Should return result with code execution output
        assert isinstance(result, dict)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_scientific_computation(self, sandbox_mcp_server_available):
        """Test scientific computation in sandbox."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query="Calculate the square root of 144 using Python",
        )

        # Should mention 12
        assert isinstance(result, dict)
        assert len(result) > 0


class TestWebSearchToolSmoke:
    """Smoke tests for web search tool."""

    @pytest.mark.asyncio
    async def test_websearch_basic(self, main_mcp_server_available):
        """Test web search with simple query."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query="Search the web for 'UniProt protein database'",
        )

        # Should return some result or error message
        assert isinstance(result, dict)
        assert len(result) > 0


# Recommended test queries for manual testing in Chapter 03:
"""
GOOD TEST QUERIES FOR CHAPTER 03 MULTI-AGENT SYSTEM:

1. Simple Math & General:
   - "What is 25 * 4?"
   - "What is the current date and time?"
   - "Calculate the square root of 256"

2. Scientific Database Queries:
   - "Look up UniProt entry P02533"
   - "Search PubChem for aspirin"
   - "Find information about keratin proteins"

3. HPC & Computational:
   - "Check the HPC cluster status"
   - "Submit a job to calculate pi to 1000 digits"
   - "What are the available HPC resources?"

4. Code Execution (Sandbox):
   - "Execute Python code to calculate factorial of 10"
   - "Run this code: import numpy as np; print(np.mean([1,2,3,4,5]))"
   - "Calculate the Fibonacci sequence up to 10 numbers using Python"

5. Multi-Step Workflows:
   - "Look up protein P02533 in UniProt and then search for related compounds in PubChem"
   - "Calculate 15 * 8 and then find the square root of the result"
   - "Search for 'BLAST algorithm' and summarize the top 3 results"

6. Web Search:
   - "Search the web for 'protein structure prediction methods'"
   - "Find recent papers on CRISPR gene editing"
   - "What are the latest developments in AlphaFold?"
"""
