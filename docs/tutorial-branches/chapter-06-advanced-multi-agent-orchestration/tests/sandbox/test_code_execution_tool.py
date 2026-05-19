"""Tests for nsjail integration in code_execution_tool.py.

These tests validate the nsjail execution path, command construction,
network isolation (A4), and resource limits (A5) without requiring
a real Docker daemon or nsjail binary — all external calls are mocked.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


# ── helpers ────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure a predictable environment for every test."""
    monkeypatch.setenv("SANDBOX_BACKEND", "nsjail")
    monkeypatch.setenv("NSJAIL_BINARY_PATH", "/usr/local/bin/nsjail")


# ── _build_nsjail_command ──────────────────────────────────────────────────────


def test_build_nsjail_command_structure():
    """_build_nsjail_command returns a list starting with the nsjail binary
    and ending with the interpreter and script path."""
    from agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool import (
        _build_nsjail_command,
    )

    cmd = _build_nsjail_command("/usr/local/bin/python3", "/tmp/user_code.py")
    assert cmd[0] == "/usr/local/bin/nsjail"
    assert "--mode" in cmd and "once" in cmd
    assert "--" in cmd
    assert cmd[-2] == "/usr/local/bin/python3"
    assert cmd[-1] == "/tmp/user_code.py"


def test_build_nsjail_command_uid_gid():
    """nsjail command must run as unprivileged user 65534 (nobody)."""
    from agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool import (
        _build_nsjail_command,
    )

    cmd = _build_nsjail_command("/usr/local/bin/python3", "/tmp/user_code.py")
    uid_idx = cmd.index("--user") + 1
    gid_idx = cmd.index("--group") + 1
    assert cmd[uid_idx] == "65534"
    assert cmd[gid_idx] == "65534"


def test_build_nsjail_command_network_disabled():
    """nsjail command must NOT include --disable_clone_newnet (§2.4 claims
    'networking disabled'). By omission, nsjail creates a new empty network
    namespace — effectively disabling network access."""
    from agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool import (
        _build_nsjail_command,
    )

    cmd = _build_nsjail_command("/usr/local/bin/python3", "/tmp/user_code.py")
    assert "--disable_clone_newnet" not in cmd, (
        "nsjail must not disable network namespace isolation — manuscript claims networking is disabled"
    )


def test_build_nsjail_command_resource_limits():
    """nsjail command must include resource limits matching §2.4 'strict resource
    limits' claim: address space, open files, and process count."""
    from agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool import (
        _build_nsjail_command,
    )

    cmd = _build_nsjail_command("/usr/local/bin/python3", "/tmp/user_code.py")
    assert "--rlimit_as" in cmd, "Must set address space (memory) limit"
    assert "--rlimit_nofile" in cmd, "Must set open file descriptor limit"
    assert "--rlimit_nproc" in cmd, "Must set process count limit"
    assert "--time_limit" in cmd, "Must set execution time limit"


# ── NSJAIL_AVAILABLE flag ─────────────────────────────────────────────────────


def test_nsjail_available_false_when_binary_missing(monkeypatch, tmp_path):
    """NSJAIL_AVAILABLE is False when the binary path does not exist."""
    monkeypatch.setenv("NSJAIL_BINARY_PATH", str(tmp_path / "no_such_binary"))
    import importlib
    import agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool as mod

    importlib.reload(mod)
    assert mod.NSJAIL_AVAILABLE is False


def test_nsjail_available_true_when_binary_exists(monkeypatch, tmp_path):
    """NSJAIL_AVAILABLE is True when the binary path exists and is executable."""
    fake_binary = tmp_path / "nsjail"
    fake_binary.write_text("#!/bin/sh\n")
    fake_binary.chmod(0o755)
    monkeypatch.setenv("NSJAIL_BINARY_PATH", str(fake_binary))
    import importlib
    import agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool as mod

    importlib.reload(mod)
    assert mod.NSJAIL_AVAILABLE is True


# ── _run_code_in_sandbox_sync routing ─────────────────────────────────────────


@patch(
    "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.ArtifactSandboxSession"
)
def test_nsjail_backend_non_plot_uses_execute_command(mock_session_cls, monkeypatch):
    """When SANDBOX_BACKEND=nsjail and generate_plot=False, execution goes through
    execute_command (the nsjail path), NOT session.run()."""
    monkeypatch.setattr(
        "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.NSJAIL_AVAILABLE",
        True,
    )
    monkeypatch.setattr(
        "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.SANDBOX_BACKEND",
        "nsjail",
    )
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute_command.return_value = MagicMock(
        exit_code=0, stdout="42\n", stderr=""
    )
    mock_session_cls.return_value = mock_session

    from agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool import (
        _run_code_in_sandbox_sync,
    )

    result = _run_code_in_sandbox_sync(
        code="print(42)", language="python", generate_plot=False
    )

    mock_session.execute_command.assert_called_once()
    mock_session.run.assert_not_called()
    assert result["exit_code"] == 0
    assert "42" in result["stdout"]


@patch(
    "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.ArtifactSandboxSession"
)
def test_nsjail_backend_plot_falls_back_to_run(mock_session_cls, monkeypatch):
    """When SANDBOX_BACKEND=nsjail but generate_plot=True, execution falls back to
    session.run() (ArtifactSandboxSession Docker path) to enable plot capture."""
    monkeypatch.setattr(
        "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.NSJAIL_AVAILABLE",
        True,
    )
    monkeypatch.setattr(
        "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.SANDBOX_BACKEND",
        "nsjail",
    )
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_run_result = MagicMock(exit_code=0, stdout="", stderr="", plots=[])
    mock_session.run.return_value = mock_run_result
    mock_session_cls.return_value = mock_session

    from agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool import (
        _run_code_in_sandbox_sync,
    )

    _run_code_in_sandbox_sync(
        code="import matplotlib.pyplot as plt\nplt.show()",
        language="python",
        generate_plot=True,
    )

    mock_session.run.assert_called_once()
    mock_session.execute_command.assert_not_called()


@patch(
    "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.ArtifactSandboxSession"
)
def test_docker_backend_always_uses_run(mock_session_cls, monkeypatch):
    """When SANDBOX_BACKEND=docker, execution always uses session.run() regardless
    of generate_plot, preserving backward compatibility."""
    monkeypatch.setattr(
        "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.SANDBOX_BACKEND",
        "docker",
    )
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.run.return_value = MagicMock(
        exit_code=0, stdout="ok\n", stderr="", plots=[]
    )
    mock_session_cls.return_value = mock_session

    from agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool import (
        _run_code_in_sandbox_sync,
    )

    _run_code_in_sandbox_sync(
        code="print('ok')", language="python", generate_plot=False
    )
    mock_session.run.assert_called_once()
    mock_session.execute_command.assert_not_called()


@patch(
    "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.ArtifactSandboxSession"
)
def test_nsjail_unavailable_falls_back_to_run(mock_session_cls, monkeypatch):
    """If SANDBOX_BACKEND=nsjail but the binary is missing, execution falls back
    to session.run() rather than raising an unhandled exception."""
    monkeypatch.setattr(
        "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.NSJAIL_AVAILABLE",
        False,
    )
    monkeypatch.setattr(
        "agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool.SANDBOX_BACKEND",
        "nsjail",
    )
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.run.return_value = MagicMock(
        exit_code=0, stdout="fallback\n", stderr="", plots=[]
    )
    mock_session_cls.return_value = mock_session

    from agentic_framework_pkg.sandbox_mcp_server.tools.code_execution_tool import (
        _run_code_in_sandbox_sync,
    )

    result = _run_code_in_sandbox_sync(
        code="print('fallback')", language="python", generate_plot=False
    )
    mock_session.run.assert_called_once()
    assert result["exit_code"] == 0
