# kbbi-mcp

[![CI](https://img.shields.io/github/actions/workflow/status/gaato/kbbi-mcp/ci.yml?label=CI)](https://github.com/gaato/kbbi-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/kbbi-mcp)](https://pypi.org/project/kbbi-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/kbbi-mcp)](https://pypi.org/project/kbbi-mcp/)
[![License](https://img.shields.io/pypi/l/kbbi-mcp)](https://github.com/gaato/kbbi-mcp/blob/HEAD/LICENSE)

An MCP server for querying KBBI (Kamus Besar Bahasa Indonesia / KBBI Daring).

**Python:** 3.13+

This project exposes a single, stable JSON tool output so LLM clients can decide how to format, translate, or summarize results.

## Relationship to KBBI Daring

This project is **unofficial** and is **not affiliated with** or endorsed by the official KBBI Daring service.

## Features

- MCP tool: `kbbi_lookup(query: str)`
- MCP resource: `kbbi://{query}` (same payload as `kbbi_lookup`)
- Works without credentials (anonymous mode)
- Optional authenticated mode via environment variables

## Configure in an MCP client (JSON)

Most MCP clients (including Claude Desktop) use a JSON config with a top-level `mcpServers` object.
This `mcpServers` format is an emergent standard across the MCP ecosystem (see: https://gofastmcp.com/integrations/mcp-json-configuration.md).

### `mcpServers`-based clients (Claude Desktop / Cursor / Windsurf)

This matches the convention used by many Python MCP servers.

Where to put it:

- Claude Desktop: `~/.claude/claude_desktop_config.json`
- Cursor: `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global)
- Windsurf: `~/.codeium/windsurf/mcp_config.json`

```json
{
	"mcpServers": {
		"kbbi": {
			"command": "uvx",
			"args": ["kbbi-mcp"]
		}
	}
}
```

Note: this example uses `uvx` (part of `uv`) to run the server.
Install uv here: https://docs.astral.sh/uv/getting-started/installation/

If you don't want to depend on `uv`, install `kbbi-mcp` into an environment and point your client to that environment's executable. For example:

- Use the console script (recommended when available): `kbbi-mcp`
- Or run the module: `python -m kbbi_mcp`

Authenticated mode is optional. If you have KBBI Daring credentials, configure the environment variables described in [Authentication (optional)](#authentication-optional).

### Local development (run from this repo)

You'll need `uv` installed: https://docs.astral.sh/uv/getting-started/installation/

This repo includes a `fastmcp.json` file that defines how to run the server (source + uv environment + stdio transport).

To run the server directly from this checkout:

```bash
fastmcp run
```

To generate an `mcpServers` entry you can paste into your MCP client config:

```bash
fastmcp install mcp-json fastmcp.json
```

Note: the generated configuration uses absolute paths so it works regardless of the client's working directory.

## Tool: `kbbi_lookup`

**Input**

- `query` (string): a word or phrase

Example tool arguments:

```json
{
	"query": "makan"
}
```

**Output**

Returns a JSON object:

- `found` (bool)
- `query` (string)
- `url` (string | null)
- `entries` (list)
- `suggestions` (list)
- `error` (string, optional): present only when the request is invalid (e.g. empty query) or an unexpected error occurs

`entries` is based on KBBI's `serialisasi()` shape from the underlying `kbbi` library, with a small normalization:

- `etimologi` is always present (as an object or `null`)
- related-word lists are always present (as arrays, possibly empty)

This keeps the tool output stable across anonymous/authenticated mode.

Example tool output:

```json
{
	"found": true,
	"query": "makan",
	"url": "https://kbbi.kemdikbud.go.id/entri/makan",
	"entries": [
		{
			"nama": "makan",
			"nomor": "",
			"kata_dasar": [],
			"pelafalan": "",
			"bentuk_tidak_baku": [],
			"varian": [],
			"makna": [],
			"etimologi": null,
			"kata_turunan": [],
			"gabungan_kata": [],
			"peribahasa": [],
			"idiom": []
		}
	],
	"suggestions": []
}
```

## Resource: `kbbi://{query}`

This server also exposes the same payload as a read-only MCP resource.

- `kbbi://makan`

For low-level debugging, a client would read it using `resources/read` with `{"uri": "kbbi://makan"}`.

## Authentication (optional)

Anonymous mode works out of the box.

If you have KBBI Daring credentials, some additional fields may become available.

Set the following environment variables:

- `KBBI_EMAIL`
- `KBBI_PASSWORD`
- `KBBI_COOKIE_PATH` (optional)

Most `mcpServers`-based clients support passing environment variables via `env` (all values must be strings). Example:

```json
{
	"mcpServers": {
		"kbbi": {
			"command": "uvx",
			"args": ["kbbi-mcp"],
			"env": {
				"KBBI_EMAIL": "<YOUR_EMAIL>",
				"KBBI_PASSWORD": "<YOUR_PASSWORD>",
				"KBBI_COOKIE_PATH": "<OPTIONAL_PATH>"
			}
		}
	}
}
```
