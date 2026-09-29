"""Public API helpers for embedding.

This module exists so `kbbi_mcp.__init__` can stay lightweight while still
exposing a convenient, import-friendly API for external users.
"""

from __future__ import annotations

from mcp.client import Client
from mcp.server.mcpserver import MCPServer


def create_mcp() -> MCPServer:
    """Return the MCP server instance.

    Returns:
        MCPServer: The configured server instance.
    """
    from .server import create_mcp as _create_mcp

    return _create_mcp()


def create_client() -> Client:
    """Create an in-memory MCP client connected to this server.

    Returns:
        Client: A client connected to the server via in-memory transport.
    """
    from .server import create_client as _create_client

    return _create_client()
