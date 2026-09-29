"""Release smoke test.

This script is intended to be executed in CI against the built artifacts:
- a wheel ("dist/*.whl")
- a source distribution ("dist/*.tar.gz")

In GitHub Actions, it is executed via:

- uv run --isolated --no-project --with dist/*.whl scripts/smoke_test.py
- uv run --isolated --no-project --with dist/*.tar.gz scripts/smoke_test.py

The test must be:
- Fast (no network)
- Deterministic
- Strict enough to catch missing files / import issues
"""

import asyncio


async def _check_mcp_surface() -> None:
    import kbbi_mcp

    async with kbbi_mcp.create_client() as client:
        tools = {t.name: t for t in await client.list_tools()}
        assert "kbbi_lookup" in tools, "kbbi_lookup tool must be exposed"
        assert tools["kbbi_lookup"].annotations is not None
        assert tools["kbbi_lookup"].annotations.read_only_hint is True

        templates = {t.uri_template for t in await client.list_resource_templates()}
        assert "kbbi://{query}" in templates, "kbbi://{query} resource must be exposed"

        # An empty query is rejected before any network access.
        result = await client.call_tool("kbbi_lookup", {"query": ""}, raise_on_error=False)
        assert result.is_error, "empty query must be reported as a tool error"


def main() -> None:
    # Import should succeed from both wheel and sdist installs.
    import kbbi_mcp

    # Basic surface area expected by users.
    assert hasattr(kbbi_mcp, "mcp"), "kbbi_mcp.mcp must exist"
    assert hasattr(kbbi_mcp, "main"), "kbbi_mcp.main must exist"

    asyncio.run(_check_mcp_surface())


if __name__ == "__main__":
    main()
