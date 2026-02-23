# Repository instructions for GitHub Copilot

This repository is a **Python 3.13+** project (see `pyproject.toml`). It provides an MCP server for querying **KBBI**.

## Tooling (source of truth)

- Use **uv** for dependency management and running commands.
  - Prefer `uv sync ...` / `uv run ...`.
  - Avoid `pip install`, Poetry, or ad-hoc venv management in instructions.
- Use **Ruff** for linting and formatting.
- Use **ty** for type checking.
- Use **pytest** for tests.

## Commands to validate changes (match CI)

Run these before finishing a change:

- Install deps (incl. dev tools): `uv sync --frozen --group dev`
- Auto-format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Format (final guard): `uv run ruff format --check .`
- Type check: `uv run ty check`
- Tests: `uv run pytest`

If you introduce or update dependencies, keep `pyproject.toml` and the uv lockfile in sync.

## Project layout

- Package source: `src/kbbi_mcp/`
  - MCP server entrypoint: `src/kbbi_mcp/server.py`
- Tests: `tests/`
- Declarative server config: `fastmcp.json`

## Coding conventions

- Keep diffs minimal and consistent with existing style.
- Let Ruff handle formatting; don’t “hand-format” code.
- Prefer explicit, well-typed public APIs; avoid adding import-time side effects.
