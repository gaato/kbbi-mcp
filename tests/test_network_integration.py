import pytest
from conftest import _as_mapping

import kbbi_mcp


@pytest.mark.anyio
@pytest.mark.network
async def test_kbbi_lookup_real_network_smoke(network_enabled):
    """Optional real-network smoke test.

    This test is intentionally non-strict: it only verifies that a real call
    returns a well-shaped payload without raising errors.
    """
    async with kbbi_mcp.create_client() as client:
        result = await client.call_tool("kbbi_lookup", {"query": "apel"}, timeout=15.0)

    payload = _as_mapping(result.data)

    # Stable top-level shape.
    for key in ("found", "query", "url", "entries", "suggestions"):
        assert key in payload

    assert payload["query"] == "apel"
    assert isinstance(payload["found"], bool)
    assert isinstance(payload["entries"], list)
    assert isinstance(payload["suggestions"], list)
