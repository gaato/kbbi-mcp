"""Public API helpers for embedding.

This module exists so `kbbi_mcp.__init__` can stay lightweight while still
exposing a convenient, import-friendly API for external users.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client, FastMCP


def create_mcp() -> FastMCP:
    """Return the FastMCP server instance.

    Returns:
        FastMCP: The configured server instance.
    """
    from .server import create_mcp as _create_mcp

    return _create_mcp()


def create_client() -> Client[Any]:
    """Create an in-memory FastMCP client connected to this server.

    Returns:
        Client[Any]: A client connected to the server via in-memory transport.
    """
    from .server import create_client as _create_client

    return _create_client()
