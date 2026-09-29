kbbi-mcp
========

.. image:: https://img.shields.io/github/actions/workflow/status/gaato/kbbi-mcp/ci.yml?label=CI
   :target: https://github.com/gaato/kbbi-mcp/actions/workflows/ci.yml
   :alt: CI

.. image:: https://img.shields.io/pypi/v/kbbi-mcp
   :target: https://pypi.org/project/kbbi-mcp/
   :alt: PyPI

.. image:: https://img.shields.io/pypi/pyversions/kbbi-mcp
   :target: https://pypi.org/project/kbbi-mcp/
   :alt: Python

.. image:: https://img.shields.io/pypi/l/kbbi-mcp
   :target: https://github.com/gaato/kbbi-mcp/blob/HEAD/LICENSE
   :alt: License

An MCP server for querying KBBI (Kamus Besar Bahasa Indonesia / KBBI Daring).

**Python:** 3.13+

This project exposes a single, stable JSON tool output so LLM clients can decide how to format, translate, or summarize results.

Relationship to KBBI Daring
---------------------------

This project is **unofficial** and is **not affiliated with** or endorsed by the official KBBI Daring service.

Features
--------

- MCP tool: ``kbbi_lookup(query: str)``
- MCP resource: ``kbbi://{query}`` (same payload as ``kbbi_lookup``)
- No login/auth flow required
- Uses official KBBI VI Daring by default

Configure in an MCP client (JSON)
----------------------------------

Most MCP clients (including Claude Desktop) use a JSON config with a top-level ``mcpServers`` object.
This ``mcpServers`` format is an emergent standard across the MCP ecosystem (see: https://gofastmcp.com/integrations/mcp-json-configuration.md).

``mcpServers``-based clients (Claude Desktop / Cursor / Windsurf)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This matches the convention used by many Python MCP servers.

Where to put it:

- Claude Desktop: ``~/.claude/claude_desktop_config.json``
- Cursor: ``.cursor/mcp.json`` (project) or ``~/.cursor/mcp.json`` (global)
- Windsurf: ``~/.codeium/windsurf/mcp_config.json``

.. code-block:: json

   {
       "mcpServers": {
           "kbbi": {
               "command": "uvx",
               "args": ["kbbi-mcp"]
           }
       }
   }

Note: this example uses ``uvx`` (part of ``uv``) to run the server.
Install uv here: https://docs.astral.sh/uv/getting-started/installation/

If you don't want to depend on ``uv``, install ``kbbi-mcp`` into an environment and point your client to that environment's executable. For example:

- Use the console script (recommended when available): ``kbbi-mcp``
- Or run the module: ``python -m kbbi_mcp``

The server performs direct lookups to the official KBBI VI Daring site.

Local development (run from this repo)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You'll need ``uv`` installed: https://docs.astral.sh/uv/getting-started/installation/

To run the server over stdio directly from this checkout:

.. code-block:: bash

   uv run kbbi-mcp

To point an MCP client at this checkout, use an ``mcpServers`` entry like this
(replace the path with the absolute path of your clone):

.. code-block:: json

   {
       "mcpServers": {
           "kbbi-dev": {
               "command": "uv",
               "args": ["--directory", "/path/to/kbbi-mcp", "run", "kbbi-mcp"]
           }
       }
   }

Tool: ``kbbi_lookup``
---------------------

**Input**

- ``query`` (string): a word or phrase

Example tool arguments:

.. code-block:: json

   {
       "query": "makan"
   }

**Output**

Returns a JSON object:

- ``found`` (bool): whether ``entries`` is non-empty
- ``query`` (string): the trimmed query
- ``url`` (string): the KBBI page that was read
- ``entries`` (list): one item per headword; homographs such as *makan¹* and *makan²* are separate entries
- ``suggestions`` (list of strings): similar headwords, only when nothing was found

Each entry has:

- ``headword`` (string): syllable dots removed (``ma.kan`` → ``makan``)
- ``homograph`` (int | null): the superscript number, if any
- ``pronunciation`` (string | null): e.g. ``/gêmas/``
- ``root_words`` (list of strings): e.g. ``["punya"]`` for *mempunyai*
- ``senses`` (list), in page order, each with:

  - ``labels``: ``{code, name, description}`` for word classes (``v``, ``n``, …) and usage labels (``ki``, ``Tas``, …)
  - ``gloss`` (string): the definition text
  - ``examples``: ``{text, meaning}``; ``--`` or ``~`` in ``text`` stands for the headword, and ``meaning`` (string | null) explains idiomatic examples

Every key is always present (``null`` or an empty list when absent), so the output shape is stable.

An empty query or a failed lookup (e.g. KBBI unreachable) is reported as an MCP tool error
(``isError: true``) with a message, not as a JSON payload.

Example tool output:

.. code-block:: json

   {
       "found": true,
       "query": "gemas",
       "url": "https://kbbi.kemendikdasmen.go.id/entri/gemas",
       "entries": [
           {
               "headword": "gemas",
               "homograph": null,
               "pronunciation": "/gêmas/",
               "root_words": [],
               "senses": [
                   {
                       "labels": [
                           {
                               "code": "a",
                               "name": "Adjektiva",
                               "description": "kata yang menjelaskan nomina atau pronomina"
                           }
                       ],
                       "gloss": "sangat jengkel (marah) dalam hati",
                       "examples": [
                           {
                               "text": "saya sangat -- pada anak itu karena selalu mengotori lantai",
                               "meaning": null
                           }
                       ]
                   },
                   {
                       "labels": [
                           {
                               "code": "a",
                               "name": "Adjektiva",
                               "description": "kata yang menjelaskan nomina atau pronomina"
                           }
                       ],
                       "gloss": "sangat suka (cinta) bercampur jengkel; jengkel-jengkel cinta",
                       "examples": [
                           {
                               "text": "-- aku melihat anak ini",
                               "meaning": null
                           }
                       ]
                   }
               ]
           }
       ],
       "suggestions": []
   }

Resource: ``kbbi://{query}``
-----------------------------

This server also exposes the same payload as a read-only MCP resource (``application/json``).

- ``kbbi://makan``

For low-level debugging, a client would read it using ``resources/read`` with ``{"uri": "kbbi://makan"}``.

Data source
-----------

Lookup behavior:

- Official source: ``https://kbbi.kemendikdasmen.go.id/entri/{query}``

Optional environment variables:

- ``KBBI_BASE_URL`` (default: ``https://kbbi.kemendikdasmen.go.id``)
- ``KBBI_TIMEOUT_SECONDS`` (default: ``10.0``)
- ``KBBI_LOG_LEVEL`` (default: ``INFO``): level of the server's logs, written to stderr
