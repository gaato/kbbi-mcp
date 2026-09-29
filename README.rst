kbbi-mcp
========

.. mcp-name: io.github.gaato/kbbi-mcp

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
   :target: https://github.com/gaato/kbbi-mcp/blob/HEAD/LICENSE.md
   :alt: License

.. image:: https://img.shields.io/badge/VS_Code-Install_Server-0098FF
   :target: https://insiders.vscode.dev/redirect/mcp/install?name=kbbi&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22kbbi-mcp%22%5D%7D
   :alt: Install in VS Code

.. image:: https://img.shields.io/badge/Cursor-Install_Server-000000?logo=cursor
   :target: https://cursor.com/en/install-mcp?name=kbbi&config=eyJjb21tYW5kIjoidXZ4IGtiYmktbWNwIn0%3D
   :alt: Install in Cursor

An MCP server that lets AI assistants look up Indonesian words in
`KBBI <https://kbbi.kemendikdasmen.go.id>`_ (Kamus Besar Bahasa Indonesia), the official Indonesian dictionary.
It returns structured entries (homographs, pronunciation, root words, word classes, definitions, and examples)
so the assistant can explain, translate, or quote them for you.

This is an **unofficial** client; see `Disclaimer`_.

Example prompts
---------------

- *What does "gemas" mean according to KBBI?*
- *Apa arti kata "mempunyai"? Apa kata dasarnya?*
- *Explain "layarnya tidak makan" using KBBI.*

Getting started
---------------

The server runs locally over stdio with `uv <https://docs.astral.sh/uv/getting-started/installation/>`_'s ``uvx``;
no API key or account is needed. Most clients accept this standard config:

.. code-block:: json

   {
       "mcpServers": {
           "kbbi": {
               "command": "uvx",
               "args": ["kbbi-mcp"]
           }
       }
   }

Claude Code
~~~~~~~~~~~

.. code-block:: bash

   claude mcp add kbbi -- uvx kbbi-mcp

Codex CLI
~~~~~~~~~

.. code-block:: bash

   codex mcp add kbbi -- uvx kbbi-mcp

Gemini CLI
~~~~~~~~~~

.. code-block:: bash

   gemini mcp add kbbi uvx kbbi-mcp

VS Code
~~~~~~~

Click the *Install in VS Code* badge at the top, or run:

.. code-block:: bash

   code --add-mcp '{"name":"kbbi","command":"uvx","args":["kbbi-mcp"]}'

Cursor
~~~~~~

Click the *Install in Cursor* badge at the top, or add the standard config to ``~/.cursor/mcp.json``
(or ``.cursor/mcp.json`` in a project).

Claude Desktop
~~~~~~~~~~~~~~

Open *Settings → Developer → Edit Config* and add the standard config to ``claude_desktop_config.json``:

- macOS: ``~/Library/Application Support/Claude/claude_desktop_config.json``
- Windows: ``%APPDATA%\Claude\claude_desktop_config.json``

Other clients
~~~~~~~~~~~~~

Use the standard config above. Without ``uv``, install the package with ``pip install kbbi-mcp`` and use
``kbbi-mcp`` (or ``python -m kbbi_mcp``) as the command.

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
- ``suggestions`` (list of strings): similar headwords when nothing was found, if the page lists any
  (usually empty; see `Limitations`_)

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

Configuration
-------------

Optional environment variables:

- ``KBBI_TIMEOUT_SECONDS`` (default: ``10.0``): timeout for each request to KBBI
- ``KBBI_LOG_LEVEL`` (default: ``INFO``): level of the server's logs, written to stderr
- ``KBBI_BASE_URL`` (default: ``https://kbbi.kemendikdasmen.go.id``): the KBBI site to query

For example, with Claude Code: ``claude mcp add kbbi -e KBBI_TIMEOUT_SECONDS=20 -- uvx kbbi-mcp``.
In the standard config, add an ``"env": {"KBBI_TIMEOUT_SECONDS": "20"}`` object next to ``"args"``.

Limitations
-----------

- Lookups are anonymous. KBBI shows etymology, related entries, and suggestions for missing words only to
  signed-in users, so they are not returned (``suggestions`` is usually empty).
- Each lookup fetches ``https://kbbi.kemendikdasmen.go.id/entri/{query}``. KBBI limits anonymous searches,
  so avoid rapid bulk lookups. Results are cached in memory while the server runs.
- The result depends on KBBI's page markup; if KBBI changes it, parsing may break until this package is updated.

Debugging
---------

Use the `MCP Inspector <https://github.com/modelcontextprotocol/inspector>`_:

.. code-block:: bash

   npx @modelcontextprotocol/inspector uvx kbbi-mcp

Development
-----------

With ``uv`` installed, run the server over stdio from a checkout:

.. code-block:: bash

   uv run kbbi-mcp

To point an MCP client at the checkout, use ``uv`` with ``--directory`` (an absolute path to your clone):

.. code-block:: json

   {
       "mcpServers": {
           "kbbi-dev": {
               "command": "uv",
               "args": ["--directory", "/path/to/kbbi-mcp", "run", "kbbi-mcp"]
           }
       }
   }

Checks (see ``AGENTS.md``):

.. code-block:: bash

   uv sync --frozen --group dev
   uv run ruff format .
   uv run ruff check .
   uv run ty check
   uv run pytest

Tests use saved KBBI pages in ``tests/fixtures`` and make no network requests.
Set ``KBBI_MCP_RUN_NETWORK_TESTS=1`` to also run a live smoke test.

Related projects
----------------

- `kbbi.mbt <https://github.com/gaato/kbbi.mbt>`_: a MoonBit library, CLI, and agent skill for KBBI.
  The parser and output schema of this server follow it.
- `kbbi-python <https://github.com/laymonage/kbbi-python>`_: a Python library and CLI for KBBI.

Disclaimer
----------

This project is unofficial and is not affiliated with or endorsed by the Language Development and
Cultivation Agency (Badan Bahasa) or KBBI Daring. Dictionary content belongs to its copyright holders;
see KBBI's `legal notice <https://kbbi.kemendikdasmen.go.id/Beranda/Hukum>`_. This server is meant for
personal, non-commercial lookups. You are responsible for how you use the results.

License
-------

`BlueOak-1.0.0 <https://github.com/gaato/kbbi-mcp/blob/HEAD/LICENSE.md>`_.
