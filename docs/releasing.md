# Releasing

This document is intentionally not linked from `README.md`.

## Overview

This repo is set up to publish to PyPI via GitHub Actions on tag push (`v*`) using PyPI Trusted Publishing (OIDC).

On the same tag push, the workflow also creates a GitHub Release with automatically generated release notes and attaches `dist/*` artifacts.

Workflow: `.github/workflows/publish.yml`

## Release steps

1. Bump version in `pyproject.toml`
2. Run local checks:
   - ruff (lint/format), ty, pytest, and build
3. Commit the version bump
4. Create and push a tag like `vX.Y.Z`
5. Confirm GitHub Actions "Publish" succeeded

## Notes

- Ensure `dist/` artifacts are not committed.
- The tag trigger is `v*`.
