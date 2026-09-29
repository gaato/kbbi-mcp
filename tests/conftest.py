import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Protocol, cast

import pytest


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() not in {"", "0", "false", "no", "off"}


class _SupportsModelDump(Protocol):
    """Protocol for objects with a model_dump method."""

    def model_dump(self) -> dict[str, Any]:  # pragma: no cover
        ...


def _as_mapping(value: Any) -> dict[str, Any]:
    """Convert a value to a mapping, supporting Pydantic models and dicts.

    Args:
        value: The value to convert to a mapping.

    Returns:
        A dictionary representation of the value.
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
    }


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


FIXTURES = Path(__file__).parent / "fixtures"


def fixture_html(name: str) -> str:
    """Return a saved KBBI page from `tests/fixtures` (fetched 2026-09-29).

    Args:
        name (str): The fixture file stem, e.g. `makan`.

    Returns:
        str: The page HTML.
    """
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_lookup_cache() -> Iterator[None]:
    """Keep the lookup cache from leaking results between tests."""
    import kbbi_mcp.server as server

    server._cached_lookup.cache_clear()
    yield
    server._cached_lookup.cache_clear()


@pytest.fixture
def serve_fixture(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], list[str]]:
    """Make `_fetch_html` return a fixture page instead of hitting KBBI.

    Returns:
        Callable[[str], list[str]]: Call it with a fixture name; it returns the list of
        URLs that were "fetched".
    """
    import kbbi_mcp.server as server

    def install(name: str) -> list[str]:
        fetched: list[str] = []

        def fake_fetch(url: str, timeout_seconds: float) -> str:
            fetched.append(url)
            return fixture_html(name)

        monkeypatch.setattr(server, "_fetch_html", fake_fetch)
        return fetched

    return install
