"""
Unit tests for HPC SSH Tool

Tests the parsing functions and mock tool behavior.
Integration tests with real HPC require HPC_HOST to be configured.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from agentic_framework_pkg.mcp_server.tools.hpc_ssh_tool import (
    _parse_sbatch_output,
    _parse_squeue_output,
    _get_hpc_connection,
)


class TestSbatchParsing:
    """Test sbatch output parsing."""

    def test_parse_standard_output(self):
        """Test standard sbatch success output."""
        output = "Submitted batch job 123456\n"
        job_id = _parse_sbatch_output(output)
        assert job_id == "123456"

    def test_parse_with_extra_text(self):
        """Test sbatch output with additional text."""
        output = "Warning: some warning\nSubmitted batch job 789012\nJob info..."
        job_id = _parse_sbatch_output(output)
        assert job_id == "789012"

    def test_parse_alternative_format(self):
        """Test alternative job ID format."""
        output = "Your job 456789 has been submitted"
        job_id = _parse_sbatch_output(output)
        assert job_id == "456789"

    def test_parse_failure_raises_error(self):
        """Test that parsing failure raises ValueError."""
        output = "sbatch: error: Batch job submission failed: invalid account\n"
        with pytest.raises(ValueError, match="Could not parse job ID"):
            _parse_sbatch_output(output)


class TestSqueueParsing:
    """Test squeue output parsing."""

    def test_parse_running_job(self):
        """Test parsing running job status."""
        output = """JOBID PARTITION     NAME     USER ST       TIME
123456   compute  myjob username  R    0:05:30"""

        result = _parse_squeue_output(output)

        assert result["job_id"] == "123456"
        assert result["job_state"] == "RUNNING"
        assert result["partition"] == "compute"
        assert result["job_name"] == "myjob"
        assert result["user"] == "username"
        assert result["runtime"] == "0:05:30"

    def test_parse_pending_job(self):
        """Test parsing pending job status."""
        output = """JOBID PARTITION     NAME     USER ST       TIME
456789     batch  test2  testuser PD    0:00:00"""

        result = _parse_squeue_output(output)

        assert result["job_id"] == "456789"
        assert result["job_state"] == "PENDING"

    def test_parse_failed_job(self):
        """Test parsing failed job status."""
        output = """JOBID PARTITION     NAME     USER ST       TIME
111222      main  error    admin  F    1:23:45"""

        result = _parse_squeue_output(output)

        assert result["job_id"] == "111222"
        assert result["job_state"] == "FAILED"

    def test_parse_empty_output(self):
        """Test parsing when job not found."""
        output = ""

        result = _parse_squeue_output(output)

        assert result["job_state"] == "NOT_FOUND"
        assert "not in queue" in result["message"].lower()

    def test_parse_header_only(self):
        """Test parsing when only header present (job completed)."""
        output = """JOBID PARTITION     NAME     USER ST       TIME"""

        result = _parse_squeue_output(output)

        assert result["job_state"] == "COMPLETED_OR_REMOVED"

    def test_parse_error_message(self):
        """Test parsing error message from squeue."""
        output = "slurm_load_jobs error: Invalid job id specified"

        result = _parse_squeue_output(output)

        assert result["job_state"] == "ERROR"


class TestConnectionSetup:
    """Test HPC connection configuration."""

    @patch.dict(
        "os.environ",
        {
            "HPC_HOST": "test.hpc.edu",
            "HPC_USER": "testuser",
            "HPC_SSH_KEY_PATH": "/path/to/key.pem",
        },
    )
    @patch("os.path.exists", return_value=True)
    @patch("agentic_framework_pkg.mcp_server.tools.hpc_ssh_tool.Connection")
    def test_connection_with_ssh_key(self, mock_conn, mock_exists):
        """Test connection setup with SSH key."""
        conn = _get_hpc_connection()

        mock_conn.assert_called_once()
        call_kwargs = mock_conn.call_args[1]

        assert call_kwargs["host"] == "test.hpc.edu"
        assert call_kwargs["user"] == "testuser"
        assert call_kwargs["port"] == 22
        assert "key_filename" in call_kwargs["connect_kwargs"]

    @patch.dict(
        "os.environ",
        {
            "HPC_HOST": "test.hpc.edu",
            "HPC_USER": "testuser",
            "HPC_SSH_KEY_PATH": "/path/to/encrypted.pem",
            "HPC_SSH_KEY_PASSPHRASE": "secret",
        },
    )
    @patch("os.path.exists", return_value=True)
    @patch("agentic_framework_pkg.mcp_server.tools.hpc_ssh_tool.Connection")
    def test_connection_with_encrypted_key(self, mock_conn, mock_exists):
        """Test connection setup with passphrase-protected key."""
        conn = _get_hpc_connection()

        call_kwargs = mock_conn.call_args[1]

        assert "key_filename" in call_kwargs["connect_kwargs"]
        assert "passphrase" in call_kwargs["connect_kwargs"]
        assert call_kwargs["connect_kwargs"]["passphrase"] == "secret"

    @patch.dict(
        "os.environ",
        {
            "HPC_HOST": "test.hpc.edu",
            "HPC_USER": "testuser",
            "HPC_SSH_PASSWORD": "testpass",
        },
    )
    @patch("agentic_framework_pkg.mcp_server.tools.hpc_ssh_tool.Connection")
    def test_connection_with_password(self, mock_conn):
        """Test connection setup with password (fallback)."""
        conn = _get_hpc_connection()

        call_kwargs = mock_conn.call_args[1]

        assert "password" in call_kwargs["connect_kwargs"]
        assert call_kwargs["connect_kwargs"]["password"] == "testpass"

    @patch.dict("os.environ", {}, clear=True)
    def test_connection_missing_host(self):
        """Test that missing HPC_HOST raises error."""
        with pytest.raises(ValueError, match="HPC_HOST"):
            _get_hpc_connection()

    @patch.dict("os.environ", {"HPC_HOST": "test.hpc.edu"}, clear=True)
    def test_connection_missing_user(self):
        """Test that missing HPC_USER raises error."""
        with pytest.raises(ValueError, match="HPC_USER"):
            _get_hpc_connection()

    @patch.dict(
        "os.environ", {"HPC_HOST": "test.hpc.edu", "HPC_USER": "testuser"}, clear=True
    )
    def test_connection_missing_auth(self):
        """Test that missing auth method raises error."""
        with pytest.raises(ValueError, match="No authentication method"):
            _get_hpc_connection()

    @patch.dict(
        "os.environ",
        {
            "HPC_HOST": "test.hpc.edu",
            "HPC_USER": "testuser",
            "HPC_SSH_KEY_PATH": "/nonexistent/key.pem",
        },
    )
    @patch("os.path.exists", return_value=False)
    def test_connection_missing_key_file(self, mock_exists):
        """Test that missing key file raises error."""
        with pytest.raises(ValueError, match="SSH key not found"):
            _get_hpc_connection()


# Integration tests for HPC tools require actual HPC connection
# For agent-based smoke tests, see tests/test_mcp_tools_smoke.py and add:
#
# @pytest.mark.skipif(not os.getenv("HPC_HOST"), reason="HPC not configured")
# class TestHPCToolsSmoke:
#
#     async def test_hpc_connection_via_agent(self):
#         agent = ScientificWorkflowAgent(mcp_session_id="test-hpc")
#         result = await agent.arun("Test the connection to our HPC cluster")
#         assert "success" in result["output"].lower()
#
#     async def test_slurm_job_submission_via_agent(self):
#         agent = ScientificWorkflowAgent(mcp_session_id="test-hpc")
#         result = await agent.arun(
#             "Submit the hello world job at /home/testuser/jobs/hello.sh"
#         )
#         assert "job" in result["output"].lower()
#         assert "submitted" in result["output"].lower()
#
# To run with real HPC:
# 1. Set HPC_HOST, HPC_USER, HPC_SSH_KEY_PATH in .env
# 2. Ensure hello world script exists on HPC
# 3. Run: pytest tests/test_mcp_tools_smoke.py -v -k hpc
