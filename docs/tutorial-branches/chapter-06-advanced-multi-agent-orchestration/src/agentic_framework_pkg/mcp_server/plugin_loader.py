"""
Plugin auto-discovery for the MCP server.

Reference implementation of directory-based tool auto-discovery.
Scans a tools/ package for modules exposing a ``register_tools(mcp, ...)``
callable and registers them on the FastMCP server instance.

Usage (in main.py)::

    from .plugin_loader import auto_discover_and_register_tools

    auto_discover_and_register_tools(
        mcp=mcp,
        tools_package="agentic_framework_pkg.mcp_server.tools",
        llm_client=llm_agnostic_client_instance,
    )
"""

import importlib
import inspect
import pkgutil

from ..logger_config import get_logger

logger = get_logger(__name__)


def auto_discover_and_register_tools(mcp, tools_package: str, **kwargs):
    """Scan *tools_package* for modules with a ``register_tools`` callable.

    Each discovered callable is invoked with ``mcp`` plus whichever
    ``kwargs`` its signature accepts.  Modules that lack the callable
    or fail to import are skipped with a log message.

    Args:
        mcp: The FastMCP server instance.
        tools_package: Fully-qualified package name (e.g.
            ``"agentic_framework_pkg.mcp_server.tools"``).
        **kwargs: Extra dependencies forwarded to ``register_tools``
            (e.g. ``llm_client``).

    Returns:
        List of module names that were successfully registered.
    """
    package = importlib.import_module(tools_package)
    registered = []

    for finder, name, _ in pkgutil.iter_modules(package.__path__):
        module_name = f"{tools_package}.{name}"
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            logger.error(f"Failed to import {module_name}", exc_info=True)
            continue

        fn = getattr(mod, "register_tools", None)
        if fn is None or not callable(fn):
            logger.debug(f"Skipping {name}: no register_tools callable")
            continue

        # Only pass kwargs that the function's signature accepts
        sig = inspect.signature(fn)
        filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
        try:
            fn(mcp, **filtered)
            logger.info(f"Registered tool module: {name}")
            registered.append(name)
        except Exception:
            logger.error(f"Failed to register {module_name}", exc_info=True)

    logger.info(f"Auto-discovery complete: {len(registered)} registered")
    return registered
