import os

import pytest


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
