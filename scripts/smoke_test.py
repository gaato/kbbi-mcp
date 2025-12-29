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


def main() -> None:
    # Import should succeed from both wheel and sdist installs.
    import kbbi_mcp

    # Basic surface area expected by users.
    assert hasattr(kbbi_mcp, "mcp"), "kbbi_mcp.mcp must exist"
    assert hasattr(kbbi_mcp, "main"), "kbbi_mcp.main must exist"

    # Use the internal helper so the test doesn't depend on FastMCP's wrapper type.
    # This should not perform network calls for an empty query.
    from kbbi_mcp.server import _kbbi_lookup_result

    # Validate stable JSON shape without doing any lookup.
    payload = _kbbi_lookup_result("")
    assert isinstance(payload, dict)

    # Ensure stable top-level keys.
    # NOTE: `error` is optional in the schema; it is present for invalid input.
    required_keys = {"found", "query", "url", "entries", "suggestions"}
    assert required_keys.issubset(set(payload.keys()))

    assert payload["found"] is False
    assert payload["url"] is None
    assert payload["entries"] == []
    assert payload["suggestions"] == []
    error = payload.get("error")
    assert isinstance(error, str)


if __name__ == "__main__":
    main()
