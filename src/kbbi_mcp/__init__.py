"""KBBI MCP server package."""

from .server import mcp

__all__ = [
    "main",
    "mcp",
]


def main() -> None:
    """Run the MCP server over stdio (console entrypoint)."""
    mcp.run()
