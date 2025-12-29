import os
from typing import Any, Protocol, cast

import pytest


class _SupportsModelDump(Protocol):
    def model_dump(self) -> dict[str, Any]:  # pragma: no cover
        ...


def _as_mapping(value: Any) -> dict[str, Any]:
    """Convert a value to a mapping (dict).

    Handles dict, objects with model_dump(), and fallback attribute extraction.

    Args:
        value: The value to convert to a mapping.

    Returns:
        dict[str, Any]: A dictionary representation of the value.
    """
    if isinstance(value, dict):
        return cast(dict[str, Any], value)

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return cast(_SupportsModelDump, value).model_dump()

    # Fallback: best-effort attribute extraction
    return {
        "found": getattr(value, "found", None),
        "query": getattr(value, "query", None),
        "url": getattr(value, "url", None),
        "entries": getattr(value, "entries", None),
        "suggestions": getattr(value, "suggestions", None),
        "error": getattr(value, "error", None),
    }


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() not in {"", "0", "false", "no", "off"}


@pytest.fixture
def network_enabled() -> None:
    """Skip a test unless network tests were explicitly enabled.

    Network tests are opt-in because they can be flaky (service outages, rate
    limiting, connectivity) and may be slow.

    Enable by setting one of the following environment variables to a truthy value:
    - KBBI_MCP_RUN_NETWORK_TESTS
    - RUN_NETWORK_TESTS
    """
    enabled = _is_truthy(os.getenv("KBBI_MCP_RUN_NETWORK_TESTS")) or _is_truthy(
        os.getenv("RUN_NETWORK_TESTS")
    )
    if not enabled:
        pytest.skip("Network tests are disabled (set KBBI_MCP_RUN_NETWORK_TESTS=1 to enable).")
