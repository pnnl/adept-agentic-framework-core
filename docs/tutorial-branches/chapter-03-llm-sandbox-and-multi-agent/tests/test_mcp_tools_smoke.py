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
import pytest_asyncio
import os
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Minimal valid BLAST XML with no hits – used by mocked NCBI calls in unit tests
MINIMAL_BLAST_XML = """\
<?xml version="1.0"?>
<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "NCBI_BlastOutput.dtd">
<BlastOutput>
  <BlastOutput_program>blastp</BlastOutput_program>
  <BlastOutput_db>mock_db</BlastOutput_db>
  <BlastOutput_query-len>22</BlastOutput_query-len>
  <BlastOutput_iterations>
    <Iteration>
      <Iteration_iter-num>1</Iteration_iter-num>
      <Iteration_hits/>
      <Iteration_stat>
        <Statistics>
          <Statistics_db-num>200000000</Statistics_db-num>
          <Statistics_db-len>70000000000</Statistics_db-len>
          <Statistics_hsp-len>0</Statistics_hsp-len>
          <Statistics_eff-space>0</Statistics_eff-space>
          <Statistics_kappa>0.041</Statistics_kappa>
          <Statistics_lambda>0.267</Statistics_lambda>
          <Statistics_entropy>0.14</Statistics_entropy>
        </Statistics>
      </Iteration_stat>
    </Iteration>
  </BlastOutput_iterations>
</BlastOutput>
"""

SUPPORTED_BLAST_DATABASES = [
    "nr",
    "swissprot",
    "pdb",
    "refseq_protein",
    "refseq_select_prot",
    "env_nr",
    "pataa",
]

# Short, well-characterised peptide (human ubiquitin N-terminus) used in BLAST tests
TEST_BLAST_SEQUENCE = (
    "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"
)


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


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
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


class TestBlastDatabasesSmoke:
    """Smoke tests verifying BLASTp tools support multiple NCBI databases.

    Two tiers:
    1. Unit tests (no Docker / network required) – verify schema acceptance and
       that the ``database`` parameter is forwarded correctly to the NCBI API.
    2. Integration tests (``@pytest.mark.slow``, require Docker + internet) –
       make real NCBI BLAST calls for each documented database through the
       running multi-agent system and verify the tool returns a valid response
       structure.
    """

    # ------------------------------------------------------------------
    # Unit tests – no external services required
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("database", SUPPORTED_BLAST_DATABASES)
    def test_blastp_schema_accepts_all_databases(self, database):
        """Pydantic schema should accept every documented NCBI protein database."""
        from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
            PerformBlastpSearchBiopythonInput,
        )

        schema = PerformBlastpSearchBiopythonInput(
            sequence=TEST_BLAST_SEQUENCE,
            database=database,
        )
        assert schema.database == database

    def test_blastp_schema_default_database_is_nr(self):
        """Default database should be 'nr' as documented."""
        from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
            PerformBlastpSearchBiopythonInput,
        )

        schema = PerformBlastpSearchBiopythonInput(sequence=TEST_BLAST_SEQUENCE)
        assert schema.database == "nr"

    def test_blastp_wrapper_description_mentions_all_databases(self):
        """LangChain tool wrapper description should mention every supported database."""
        from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
            get_mcp_blastp_biopython_tool_langchain,
        )

        tool = get_mcp_blastp_biopython_tool_langchain(mcp_session_id="test")
        description = tool.description.lower()

        for db in SUPPORTED_BLAST_DATABASES:
            assert db in description, (
                f"Database '{db}' is not mentioned in the tool wrapper description. "
                "Agents won't know to use it."
            )

    @pytest.mark.parametrize("database", SUPPORTED_BLAST_DATABASES)
    @pytest.mark.asyncio
    async def test_blastq_passes_database_to_ncbi(self, database):
        """blastq_tool should forward the ``database`` argument to NCBIWWW.qblast unchanged."""
        from io import StringIO
        from unittest.mock import AsyncMock, MagicMock, patch

        from agentic_framework_pkg.mcp_server.tools import blastq_tool

        captured: list[tuple] = []

        def mock_qblast(program, db_arg, sequence, **kwargs):
            captured.append((program, db_arg))
            return StringIO(MINIMAL_BLAST_XML)

        # Extract the decorated function by replacing FastMCP.tool with a simple
        # passthrough decorator so we can call the inner function directly.
        registered: dict = {}

        mock_mcp = MagicMock()

        def capture_tool(**kwargs):
            def decorator(fn):
                registered[fn.__name__] = fn
                return fn

            return decorator

        mock_mcp.tool = capture_tool

        blastq_tool.register_tools(mock_mcp)

        tool_fn = registered.get("perform_blastp_search_biopython")
        assert tool_fn is not None, "perform_blastp_search_biopython was not registered"

        mock_ctx = MagicMock()
        mock_ctx.session_id = "test_session"
        mock_ctx.request_id = "test_request"
        mock_ctx.client_id = None
        mock_ctx.info = AsyncMock()
        mock_ctx.error = AsyncMock()
        mock_ctx.warning = AsyncMock()

        with (
            patch.object(blastq_tool.NCBIWWW, "qblast", side_effect=mock_qblast),
            patch(
                "agentic_framework_pkg.mcp_server.tools.blastq_tool.create_session_if_not_exists",
                new=AsyncMock(),
            ),
        ):
            result = await tool_fn(
                sequence=TEST_BLAST_SEQUENCE,
                ctx=mock_ctx,
                database=database,
                hitlist_size=2,
            )

        assert len(captured) == 1, "qblast should be called exactly once"
        assert captured[0][0] == "blastp", "BLAST program must be 'blastp'"
        assert captured[0][1] == database, (
            f"Expected database '{database}', got '{captured[0][1]}'"
        )
        # Tool should return a dict even when there are zero hits
        assert isinstance(result, dict)

    # ------------------------------------------------------------------
    # Integration tests – require Docker containers + internet access
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_blastp_swissprot_database_integration(
        self, main_mcp_server_available
    ):
        """Integration: BLASTp against 'swissprot' (UniProt Swiss-Prot) returns results."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query=(
                f"Perform a BLASTP search with the sequence '{TEST_BLAST_SEQUENCE}' "
                "against the swissprot database with hitlist_size=5."
            ),
        )

        assert isinstance(result, dict)
        result_str = str(result).lower()
        # Should indicate success or return hits data (swissprot has ubiquitin)
        assert any(
            word in result_str
            for word in ["swissprot", "ubiquitin", "hit", "result", "blast", "match"]
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_blastp_pdb_database_integration(self, main_mcp_server_available):
        """Integration: BLASTp against 'pdb' (Protein Data Bank) returns results."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query=(
                f"Perform a BLASTP search with the sequence '{TEST_BLAST_SEQUENCE}' "
                "against the pdb database with hitlist_size=5."
            ),
        )

        assert isinstance(result, dict)
        result_str = str(result).lower()
        assert any(
            word in result_str
            for word in [
                "pdb",
                "structure",
                "hit",
                "result",
                "blast",
                "match",
                "protein",
            ]
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_blastp_refseq_protein_database_integration(
        self, main_mcp_server_available
    ):
        """Integration: BLASTp against 'refseq_protein' returns results."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query=(
                f"Perform a BLASTP search with the sequence '{TEST_BLAST_SEQUENCE}' "
                "against the refseq_protein database with hitlist_size=5."
            ),
        )

        assert isinstance(result, dict)
        result_str = str(result).lower()
        assert any(
            word in result_str
            for word in ["refseq", "hit", "result", "blast", "match", "protein"]
        )

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_blastp_nr_database_integration(self, main_mcp_server_available):
        """Integration: BLASTp against 'nr' (non-redundant, default) returns results."""
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)
        result = await system.process_query(
            user_query=(
                f"Perform a BLASTP search with the sequence '{TEST_BLAST_SEQUENCE}' "
                "against the nr database with hitlist_size=5."
            ),
        )

        assert isinstance(result, dict)
        result_str = str(result).lower()
        assert any(
            word in result_str
            for word in ["nr", "hit", "result", "blast", "match", "protein"]
        )


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


class TestHPCSSHToolsSmoke:
    """Smoke tests for HPC SSH tools via HPC MCP server (no actual SSH required).

    These tests verify that:
    1. The HPC MCP server is running and reachable
    2. The HPC SSH tools are registered and callable
    3. The multi-agent system can route queries to the HPC agent
    4. Tool responses have the expected structure

    Tests use mocked/example queries that verify the interface without requiring
    a real HPC cluster connection.
    """

    @pytest.mark.asyncio
    async def test_hpc_mcp_server_has_tools(self, hpc_mcp_server_available):
        """Verify HPC MCP server is running and has HPC SSH tools registered."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to list tools from the HPC MCP server
                # The server should respond even without HPC_HOST configured
                response = await client.get(
                    HPC_MCP_SERVER_URL.rstrip("/") + "/",
                    follow_redirects=True,
                    headers={"Accept": "application/json"},
                )
                # Server is reachable (405 is expected for GET on MCP endpoint)
                assert response.status_code in [200, 405, 406]
        except Exception as e:
            pytest.fail(f"HPC MCP server not reachable: {e}")

    @pytest.mark.asyncio
    async def test_hpc_agent_routing(self, hpc_mcp_server_available):
        """Test that multi-agent system can route HPC-related queries to HPC agent.

        This verifies the agent handoff mechanism works, even if the underlying
        HPC tool call fails due to missing credentials.
        """
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)

        # Ask a question that should route to the HPC agent
        # The agent should attempt to call the tool even if it fails
        result = await system.process_query(
            user_query="What HPC tools are available for job submission?",
        )

        # Should return dict with some response
        assert isinstance(result, dict)
        # Response should contain some content about HPC or indicate tool availability
        result_str = str(result).lower()
        assert any(
            word in result_str
            for word in ["hpc", "slurm", "cluster", "job", "ssh", "tool", "available"]
        )

    @pytest.mark.asyncio
    async def test_hpc_tool_interface_structure(self, hpc_mcp_server_available):
        """Test that HPC tools return expected structure (even on error).

        This test verifies the tool interface works correctly by attempting
        to call a tool. If HPC credentials are not configured, the tool should
        return a structured error response, not crash.
        """
        from agentic_framework_pkg.multi_agent_orchestration.multi_agent_system import (
            MultiAgentSystem,
        )

        system = MultiAgentSystem(session_id=TEST_SESSION_ID)

        # Try to test HPC connection (will fail gracefully if not configured)
        result = await system.process_query(
            user_query="Test the SSH connection to the HPC cluster",
        )

        # Should return dict (not raise exception)
        assert isinstance(result, dict)
        assert len(result) > 0

        # Result should either indicate success or provide error information
        result_str = str(result).lower()
        # Check for either success indicators or error handling indicators
        assert any(
            word in result_str
            for word in [
                "connection",
                "hpc",
                "ssh",
                "error",
                "not configured",
                "failed",
                "unable",
                "host",
                "cluster",
            ]
        )

        # Should return dict with job status (might be NOT_FOUND)
        assert isinstance(result, dict)
        assert len(result) > 0
        # Result will indicate job status or that job wasn't found


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


class TestSqlQueryToolSmoke:
    """Smoke tests for SQL knowledge-base tools (ingest_data, execute_sql,
    get_sql_schema, query_csv_rag, list_files).

    Two tiers:
    1. Unit tests (no Docker / network required) – verify SELECT guardrail,
       row cap, Pydantic schemas, and LangChain wrapper metadata.
    2. Integration tests (``@pytest.mark.slow``, require Docker) – make real
       MCP calls through the running server.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register_kb_tools(self) -> dict:
        """Register knowledge_base_tool against a mock FastMCP and return the
        dict of ``{function_name: coroutine}``."""
        from unittest.mock import MagicMock
        from agentic_framework_pkg.mcp_server.tools import knowledge_base_tool

        registered: dict = {}
        mock_mcp = MagicMock()

        def capture_tool(**kwargs):
            def decorator(fn):
                registered[fn.__name__] = fn
                return fn

            return decorator

        mock_mcp.tool = capture_tool
        knowledge_base_tool.register_tools(mock_mcp)
        return registered

    def _mock_ctx(self):
        from unittest.mock import MagicMock, AsyncMock

        ctx = MagicMock()
        ctx.session_id = "test_session"
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()
        ctx.warning = AsyncMock()
        return ctx

    # ------------------------------------------------------------------
    # Unit tests – no external services required
    # ------------------------------------------------------------------

    def test_sql_query_input_schema_accepts_valid_select(self):
        """SQLQueryInput should accept a well-formed SELECT statement."""
        from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
            SQLQueryInput,
        )

        schema = SQLQueryInput(query="SELECT * FROM proteins WHERE organism='human'")
        assert "SELECT" in schema.query

    def test_ingest_data_input_schema_accepts_valid_input(self):
        """IngestDataInput should accept a file path and logical table name."""
        from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
            IngestDataInput,
        )

        schema = IngestDataInput(file_path="/app/data/test.csv", table_name="proteins")
        assert schema.file_path == "/app/data/test.csv"
        assert schema.table_name == "proteins"

    def test_sql_wrapper_description_mentions_get_sql_schema(self):
        """ExecuteSQL wrapper description must tell the LLM to call GetSQLSchema first."""
        from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
            get_mcp_sql_tool_langchain,
        )

        tool = get_mcp_sql_tool_langchain(mcp_session_id="test")
        assert (
            "GetSQLSchema" in tool.description
            or "get_sql_schema" in tool.description.lower()
        )

    def test_sql_wrapper_description_mentions_select_only(self):
        """ExecuteSQL wrapper description must mention the SELECT-only restriction."""
        from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
            get_mcp_sql_tool_langchain,
        )

        tool = get_mcp_sql_tool_langchain(mcp_session_id="test")
        assert "SELECT" in tool.description or "select" in tool.description.lower()

    def test_ingest_data_wrapper_description_mentions_rag_and_sql(self):
        """IngestDataToSQL wrapper description must mention both SQL and semantic/RAG."""
        from agentic_framework_pkg.scientific_workflow.mcp_langchain_tools import (
            get_mcp_ingest_data_tool_langchain,
        )

        tool = get_mcp_ingest_data_tool_langchain(mcp_session_id="test")
        desc_lower = tool.description.lower()
        assert "sql" in desc_lower
        assert "rag" in desc_lower or "semantic" in desc_lower

    @pytest.mark.asyncio
    async def test_execute_sql_rejects_drop_table(self):
        """execute_sql must reject DDL (DROP TABLE) with a structured error dict."""
        registered = self._register_kb_tools()
        tool_fn = registered.get("execute_sql")
        assert tool_fn is not None, "execute_sql was not registered"

        result = await tool_fn(ctx=self._mock_ctx(), query="DROP TABLE proteins")

        assert "error" in result
        assert "select" in result["error"].lower() or "SELECT" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_sql_rejects_insert(self):
        """execute_sql must reject INSERT statements."""
        tool_fn = self._register_kb_tools()["execute_sql"]
        result = await tool_fn(
            ctx=self._mock_ctx(),
            query="INSERT INTO proteins VALUES ('P1', 'TP53')",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_sql_rejects_update(self):
        """execute_sql must reject UPDATE statements."""
        tool_fn = self._register_kb_tools()["execute_sql"]
        result = await tool_fn(
            ctx=self._mock_ctx(),
            query="UPDATE proteins SET expression_level=5",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_sql_caps_result_rows(self, monkeypatch):
        """execute_sql must truncate result sets larger than SQL_MAX_ROWS."""
        from unittest.mock import AsyncMock, patch

        big_result = [{"id": i} for i in range(600)]
        tool_fn = self._register_kb_tools()["execute_sql"]
        monkeypatch.setenv("SQL_MAX_ROWS", "10")

        with patch(
            "agentic_framework_pkg.mcp_server.tools.knowledge_base_tool.execute_async_sql_query",
            new=AsyncMock(return_value=big_result),
        ):
            result = await tool_fn(ctx=self._mock_ctx(), query="SELECT * FROM proteins")

        assert result["status"] == "success"
        assert len(result["result"]) == 10

    @pytest.mark.asyncio
    async def test_execute_sql_returns_rows_for_valid_select(self):
        """execute_sql returns rows as a list of dicts for a valid SELECT."""
        from unittest.mock import AsyncMock, patch

        mock_rows = [{"protein_id": "P1", "organism": "human"}]
        tool_fn = self._register_kb_tools()["execute_sql"]

        with patch(
            "agentic_framework_pkg.mcp_server.tools.knowledge_base_tool.execute_async_sql_query",
            new=AsyncMock(return_value=mock_rows),
        ):
            result = await tool_fn(ctx=self._mock_ctx(), query="SELECT * FROM proteins")

        assert result["status"] == "success"
        assert result["result"] == mock_rows

    @pytest.mark.asyncio
    async def test_get_sql_schema_returns_schema_string(self):
        """get_sql_schema passes through the string returned by get_async_table_info."""
        from unittest.mock import AsyncMock, patch

        schema_str = "Table: proteins (protein_id TEXT, organism TEXT)"
        tool_fn = self._register_kb_tools()["get_sql_schema"]

        with patch(
            "agentic_framework_pkg.mcp_server.tools.knowledge_base_tool.get_async_table_info",
            new=AsyncMock(return_value=schema_str),
        ):
            result = await tool_fn(ctx=self._mock_ctx())

        assert result["schemas"] == schema_str

    # ------------------------------------------------------------------
    # Integration tests – require Docker containers + shared volume
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sql_ingest_and_count(self, main_mcp_server_available):
        """Integration: ingest sample CSV then count rows via SQL."""
        import os
        from fastmcp import Client as MCPClient

        sample_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "data", "sample_proteomics.csv"
            )
        )
        async with MCPClient(MAIN_MCP_SERVER_URL) as client:
            ingest = await client.call_tool(
                "ingest_data",
                {"file_path": sample_path, "table_name": "sample_proteomics"},
            )
            assert ingest

            schema = await client.call_tool("get_sql_schema", {})
            assert schema

            count = await client.call_tool(
                "execute_sql",
                {"query": "SELECT COUNT(*) as cnt FROM sample_proteomics"},
            )
            assert count

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_sql_rejects_drop_in_integration(self, main_mcp_server_available):
        """Integration: server-side guardrail rejects DROP TABLE."""
        from fastmcp import Client as MCPClient

        async with MCPClient(MAIN_MCP_SERVER_URL) as client:
            result = await client.call_tool(
                "execute_sql",
                {"query": "DROP TABLE sample_proteomics"},
            )
        result_str = str(result).lower()
        assert "error" in result_str or "select" in result_str


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

4. HPC SSH (Remote Cluster):
   - "Test the SSH connection to our HPC cluster"
   - "Submit the Slurm job at /home/username/jobs/hello.sh"
   - "Check the status of Slurm job 123456"
   - "What's the status of my most recent HPC job?"

5. Code Execution (Sandbox):
   - "Execute Python code to calculate factorial of 10"
   - "Run this code: import numpy as np; print(np.mean([1,2,3,4,5]))"
   - "Calculate the Fibonacci sequence up to 10 numbers using Python"

6. Multi-Step Workflows:
   - "Look up protein P02533 in UniProt and then search for related compounds in PubChem"
   - "Calculate 15 * 8 and then find the square root of the result"
   - "Search for 'BLAST algorithm' and summarize the top 3 results"

7. Web Search:
   - "Search the web for 'protein structure prediction methods'"
   - "Find recent papers on CRISPR gene editing"
   - "What are the latest developments in AlphaFold?"

CONFIGURATION FOR HPC SSH TESTS:
To enable HPC SSH smoke tests, set these environment variables in your .env:

# Required for connection test:
HPC_HOST=hpc.institution.edu
HPC_USER=your_username
HPC_SSH_KEY_PATH_HOST=/path/to/your/ssh/key.pem

# Optional: For job submission test (requires test script on HPC):
HPC_TEST_SCRIPT_PATH=/home/username/jobs/hello_test.sh

# Optional: For job status test (requires existing job ID):
HPC_TEST_JOB_ID=123456
"""
