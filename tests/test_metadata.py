import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_server_json_matches_package_version():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    server = json.loads((ROOT / "server.json").read_text())

    assert server["version"] == version
    assert [p["version"] for p in server["packages"]] == [version]


def test_readme_carries_mcp_registry_marker():
    # The MCP Registry verifies PyPI ownership by finding this token in the README.
    name = json.loads((ROOT / "server.json").read_text())["name"]
    readme = (ROOT / "README.rst").read_text()

    assert re.search(rf"mcp-name: {re.escape(name)}(\s|$)", readme)
