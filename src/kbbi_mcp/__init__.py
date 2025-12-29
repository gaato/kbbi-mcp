"""KBBI MCP server package.

This package can be used in two ways:

1) As an MCP server (stdio) via the `kbbi-mcp` console script or `python -m kbbi_mcp`.
2) As a Python library where you import the FastMCP server/client objects and embed
   them in-process (useful for testing or toolset integrations).

To keep imports "polite", we avoid importing `kbbi_mcp.server` eagerly.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastmcp import Client, FastMCP

__all__ = [
    "create_client",
    "create_mcp",
    "main",
]


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


def main() -> None:
    """Run the MCP server over stdio (console entrypoint)."""
    # Import lazily so `import kbbi_mcp` doesn't pull in server dependencies.
    from .__main__ import main as _main

    _main()


def __getattr__(name: str) -> Any:
    """Lazy attribute access for import friendliness.

    Args:
        name (str): Attribute name.

    Returns:
        Any: The requested attribute.

    Raises:
        AttributeError: If the attribute is unknown.
    """
    if name == "mcp":
        from .server import mcp

        return mcp
    raise AttributeError(name)
