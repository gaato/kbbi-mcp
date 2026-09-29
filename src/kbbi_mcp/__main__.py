"""Package entrypoint for `python -m kbbi_mcp`.

We keep this separate from `kbbi_mcp.__init__` so importing the package stays
side-effect free.
"""

import logging
import sys

from .server import mcp
from .settings import get_settings


def main() -> None:
    """Run the MCP server over stdio."""
    # stdout carries the MCP protocol, so logs go to stderr (MCP logging is deprecated).
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    package_logger = logging.getLogger("kbbi_mcp")
    package_logger.addHandler(handler)
    package_logger.setLevel(get_settings().log_level.upper())
    mcp.run()


if __name__ == "__main__":
    main()
