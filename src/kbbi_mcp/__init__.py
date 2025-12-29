"""KBBI MCP server package.

This package can be used in two ways:

1) As an MCP server (stdio) via the `kbbi-mcp` console script or `python -m kbbi_mcp`.
2) As a Python library where you import the FastMCP server/client objects and embed
   them in-process (useful for testing or toolset integrations).

To keep imports "polite", we avoid importing `kbbi_mcp.server` eagerly.
"""

from __future__ import annotations

from typing import Any

from .api import create_client, create_mcp

__all__ = [
    "create_client",
    "create_mcp",
    "main",
]


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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
