from typing import Any, Protocol, cast

import pytest

import kbbi_mcp


class _SupportsModelDump(Protocol):
    def model_dump(self) -> dict[str, Any]:  # pragma: no cover
        ...


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return cast(dict[str, Any], value)

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return cast(_SupportsModelDump, value).model_dump()

    return {
        "found": getattr(value, "found", None),
        "query": getattr(value, "query", None),
        "url": getattr(value, "url", None),
        "entries": getattr(value, "entries", None),
        "suggestions": getattr(value, "suggestions", None),
        "error": getattr(value, "error", None),
    }


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
