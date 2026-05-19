"""
Tests for the plugin auto-discovery utility (manuscript §2.5, step 4).

Validates that the scanner discovers valid tool modules, skips invalid ones,
and forwards kwargs only to functions whose signatures accept them.
"""

import sys
import types
import pytest
from unittest.mock import MagicMock

from agentic_framework_pkg.mcp_server.plugin_loader import (
    auto_discover_and_register_tools,
)


@pytest.fixture()
def fake_tools_package(tmp_path):
    """Create a minimal importable tools package with valid/invalid modules."""
    pkg = tmp_path / "fake_tools"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    # Tool that accepts only mcp
    (pkg / "simple_tool.py").write_text(
        "def register_tools(mcp):\n    mcp.simple = True\n"
    )

    # Tool that accepts mcp + llm_client
    (pkg / "llm_tool.py").write_text(
        "def register_tools(mcp, llm_client):\n    mcp.llm = llm_client\n"
    )

    # Module without register_tools (should be skipped)
    (pkg / "helper.py").write_text("X = 1\n")

    # Module that fails to import (should be skipped, not crash)
    (pkg / "broken.py").write_text("raise ImportError('boom')\n")

    sys.path.insert(0, str(tmp_path))
    yield "fake_tools"
    sys.path.remove(str(tmp_path))
    for key in list(sys.modules):
        if key == "fake_tools" or key.startswith("fake_tools."):
            del sys.modules[key]


def test_auto_discovery_registers_valid_and_skips_invalid(fake_tools_package):
    """Core auto-discovery behaviour: register valid tools, skip the rest."""
    mock_mcp = MagicMock()
    mock_llm = MagicMock()

    registered = auto_discover_and_register_tools(
        mcp=mock_mcp,
        tools_package=fake_tools_package,
        llm_client=mock_llm,
    )

    # Valid tools are registered
    assert "simple_tool" in registered
    assert "llm_tool" in registered
    assert mock_mcp.simple is True
    assert mock_mcp.llm == mock_llm

    # Invalid modules are not registered
    assert "helper" not in registered
    assert "broken" not in registered


def test_auto_discovery_empty_package(tmp_path):
    """An empty tools package returns an empty list without error."""
    pkg = tmp_path / "empty_tools"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    sys.path.insert(0, str(tmp_path))
    try:
        result = auto_discover_and_register_tools(
            mcp=MagicMock(),
            tools_package="empty_tools",
        )
        assert result == []
    finally:
        sys.path.remove(str(tmp_path))
        for key in list(sys.modules):
            if key == "empty_tools" or key.startswith("empty_tools."):
                del sys.modules[key]
