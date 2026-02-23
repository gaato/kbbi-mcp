# AGENTS.md

Guidance for coding agents working in this repository.

## Stack + tooling

- Python: 3.13+
- Dependency/runtime tool: `uv`
- Lint + format: `ruff`
- Type check: `ty`
- Test: `pytest`

## Working rules

1. Keep diffs minimal and focused.
2. Use `uv` commands (not `pip`/Poetry).
3. Run formatter before final checks.
4. Keep `pyproject.toml` and `uv.lock` in sync when dependencies change.

## Local validation flow

```bash
uv sync --frozen --group dev
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```

## Notes

- Source: `src/kbbi_mcp/`
- Tests: `tests/`
- MCP entrypoint: `src/kbbi_mcp/server.py`
