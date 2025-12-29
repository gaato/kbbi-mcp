"""Package entrypoint for `python -m kbbi_mcp`.

We keep this separate from `kbbi_mcp.__init__` so importing the package stays
side-effect free.
"""

from .server import mcp


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
