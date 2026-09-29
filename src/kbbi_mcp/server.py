from __future__ import annotations

import base64
import logging
import urllib.parse
import urllib.request
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Annotated, get_args

from bs4 import BeautifulSoup, Comment, NavigableString, PageElement, Tag
from mcp.client import Client
from mcp.server.caching import CacheableMethod, CacheHint
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp_types import Icon, ToolAnnotations
from pydantic import Field

from kbbi_mcp.settings import get_settings
from kbbi_mcp.types import Entry, Example, KBBILookupResult, Label, Sense


def _get_package_version() -> str | None:
    """Return the installed package version, if available.

    Returns:
        str | None: The version string, or None when running from source without metadata.
    """
    try:
        return package_version("kbbi-mcp")
    except PackageNotFoundError:
        return None


logger = logging.getLogger(__name__)


class KBBILookupError(Exception):
    """Raised when a KBBI lookup cannot be performed (bad input or upstream failure)."""


_INSTRUCTIONS = """\
Query KBBI (Kamus Besar Bahasa Indonesia / KBBI Daring).

- Tool: kbbi_lookup(query: str) -> JSON
- Resource: kbbi://{query} (same payload)

Data source policy:
- Official KBBI VI Daring host by default
"""

_ICON_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">\
<rect width="64" height="64" rx="14" fill="#b91c1c"/>\
<path d="M14 18c6-3 12-3 18 1 6-4 12-4 18-1v29c-6-3-12-3-18 1-6-4-12-4-18-1z" fill="#fff"/>\
<path d="M32 19v29" stroke="#b91c1c" stroke-width="2"/>\
</svg>"""

_ICONS = [
    Icon(
        src="data:image/svg+xml;base64," + base64.b64encode(_ICON_SVG.encode()).decode(),
        mime_type="image/svg+xml",
        sizes=["any"],
    )
]

# Dictionary content changes rarely and is identical for every caller.
_CACHE_HINT = CacheHint(ttl_ms=3600 * 1000, scope="public")


mcp = MCPServer(
    name="KBBI MCP",
    instructions=_INSTRUCTIONS,
    version=_get_package_version() or "",
    website_url="https://github.com/gaato/kbbi-mcp",
    icons=_ICONS,
    cache_hints=dict.fromkeys(get_args(CacheableMethod), _CACHE_HINT),
)


def create_mcp() -> MCPServer:
    """Return the MCP server instance.

    This makes it easy to embed the server in-process (e.g. for testing).

    Returns:
        MCPServer: The configured server instance.
    """
    return mcp


def create_client() -> Client:
    """Create an in-memory MCP client connected to this server.

    This avoids spawning a subprocess or using a network transport, which is
    ideal for deterministic unit tests and Python integrations.

    Returns:
        Client: An MCP client using in-memory transport.
    """
    return Client(create_mcp())


def _slugify_query(query: str) -> str:
    return urllib.parse.quote(query.strip().lower(), safe="")


def _build_entri_url(base_url: str, query: str) -> str:
    return f"{base_url.rstrip('/')}/entri/{_slugify_query(query)}"


def _fetch_html(url: str, timeout_seconds: float) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"kbbi-mcp/{_get_package_version() or '0'} (https://github.com/gaato/kbbi-mcp)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as res:
        return res.read().decode("utf-8", errors="ignore")


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _is_excluded(tag: Tag, excluded: frozenset[str]) -> bool:
    if tag.name in excluded:
        return True
    if tag.name == "span" and any(f"span.{c}" in excluded for c in tag.get_attribute_list("class")):
        return True
    return tag.name == "font" and str(tag.get("color") or "").lower() in excluded


def _text_except(node: PageElement, excluded: frozenset[str]) -> str:
    """Concatenate the text under `node`, skipping excluded elements.

    `excluded` holds tag names, `span.<class>` selectors, and `<font>` colors.

    Args:
        node (PageElement): The element (or string) to extract text from.
        excluded (frozenset[str]): Elements to skip, as described above.

    Returns:
        str: The raw (unnormalized) text.
    """
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag) or _is_excluded(node, excluded):
        return ""
    return "".join(_text_except(child, excluded) for child in node.children)


_HEADWORD_DECORATIONS = frozenset({"span.rootword", "span.syllable", "sup"})
_SENSE_DECORATIONS = frozenset({"red", "grey", "brown"})


def _parse_entry(h2: Tag, senses: list[Sense]) -> Entry:
    # Root-word links carry their own homograph <sup> (`lari<sup>1</sup>`); skip those.
    sup = next(
        (t for t in h2.select("sup") if t.find_parent("span", class_="rootword") is None), None
    )
    homograph: int | None = None
    if sup is not None:
        try:
            homograph = int(_normalize(sup.get_text()))
        except ValueError:
            homograph = None

    syllable = h2.select_one("span.syllable")
    return {
        # Syllable dots are dropped: `ma.kan` -> `makan`.
        "headword": _normalize(_text_except(h2, _HEADWORD_DECORATIONS)).replace(".", ""),
        "homograph": homograph,
        "pronunciation": _normalize(syllable.get_text()) if syllable is not None else None,
        "root_words": [
            _normalize(_text_except(a, frozenset({"sup"}))) for a in h2.select("span.rootword a")
        ],
        "senses": senses,
    }


def _collect_examples(node: Tag, examples: list[Example]) -> None:
    if node.name == "font":
        color = str(node.get("color") or "").lower()
        if color == "grey":
            for i in node.select("i"):
                text = _normalize(i.get_text())
                if text not in {"", ";", ","}:
                    examples.append({"text": text, "meaning": None})
            return
        if color == "brown":
            # A brown <font> explains the example right before it.
            meaning = _normalize(node.get_text())
            if meaning and examples:
                examples[-1]["meaning"] = meaning
            return

    for child in node.children:
        if isinstance(child, Tag):
            _collect_examples(child, examples)


def _parse_sense(li: Tag) -> Sense:
    labels: list[Label] = []
    for span in li.select("font[color=red] span[title]"):
        code = _normalize(span.get_text())
        name, _, description = str(span.get("title") or "").partition(":")
        labels.append({
            "code": code,
            "name": _normalize(name) or code,
            "description": _normalize(description),
        })

    examples: list[Example] = []
    _collect_examples(li, examples)

    gloss = _normalize(_text_except(li, _SENSE_DECORATIONS)).rstrip(":").strip()
    return {"labels": labels, "gloss": gloss, "examples": examples}


def _first_sense_list(h2: Tag) -> list[Sense]:
    """Return the senses of the first non-empty <ol>/<ul> sibling before the next <h2>.

    Args:
        h2 (Tag): The entry heading.

    Returns:
        list[Sense]: The parsed senses, or an empty list if none follow the heading.
    """
    for sibling in h2.find_next_siblings():
        if sibling.name == "h2":
            break
        if sibling.name in {"ol", "ul"}:
            senses = [_parse_sense(li) for li in sibling.find_all("li", recursive=False)]
            if senses:
                return senses
    return []


def _parse_html(html: str, url: str, query: str) -> KBBILookupResult:
    soup = BeautifulSoup(html, "html.parser")

    entries: list[Entry] = []
    if "entri tidak ditemukan" not in soup.get_text(" ", strip=True).lower():
        for h2 in soup.find_all("h2"):
            if senses := _first_sense_list(h2):
                entries.append(_parse_entry(h2, senses))

    return {
        "found": bool(entries),
        "query": query,
        "url": url,
        "entries": entries,
    }


@lru_cache(maxsize=256)
def _cached_lookup(query: str) -> KBBILookupResult:
    """Fetch and parse the KBBI page for an already-normalized query.

    Args:
        query (str): A non-empty, trimmed word or phrase.

    Returns:
        KBBILookupResult: The parsed lookup result.
    """
    settings = get_settings()
    url = _build_entri_url(settings.base_url, query)
    html = _fetch_html(url, timeout_seconds=settings.timeout_seconds)
    return _parse_html(html, url, query)


def _kbbi_lookup_result(query: str) -> KBBILookupResult:
    normalized_query = query.strip()
    if not normalized_query:
        raise KBBILookupError("query must not be empty")

    try:
        return _cached_lookup(normalized_query)
    except Exception as e:
        raise KBBILookupError(f"KBBI lookup failed: {type(e).__name__}: {e}") from e


def _logged_lookup(query: str) -> KBBILookupResult:
    try:
        result = _kbbi_lookup_result(query)
    except KBBILookupError as e:
        logger.warning("lookup failed query=%r: %s", query, e)
        raise

    logger.info(
        "lookup query=%r found=%s entries=%d",
        result["query"],
        result["found"],
        len(result["entries"]),
    )
    return result


@mcp.tool(
    title="KBBI Lookup",
    description=(
        "Look up an Indonesian word or phrase in KBBI, the official Indonesian dictionary.\n\n"
        "Returns one entry per headword (homographs are separate entries, numbered in\n"
        "`homograph`) with its pronunciation, root words, and ordered senses. Each sense has\n"
        "labels (word class and usage labels), a gloss, and examples; in examples `--` or `~`\n"
        "stands for the headword, and `meaning` explains idiomatic ones. If nothing matches,\n"
        "`found` is false; try a base word (e.g. `punya` for `mempunyai`) or another spelling."
    ),
    icons=_ICONS,
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
def kbbi_lookup(
    query: Annotated[str, Field(description="A word or phrase to look up.")],
) -> KBBILookupResult:
    """Look up a word or phrase in KBBI (the tool description is set on the decorator).

    Args:
        query (str): A word or phrase to look up.

    Returns:
        KBBILookupResult: A stable, JSON-serializable object containing lookup results.

    Raises:
        ToolError: If the query is empty or KBBI cannot be reached or parsed.
    """
    try:
        return _logged_lookup(query)
    except KBBILookupError as e:
        raise ToolError(str(e)) from e


@mcp.resource(
    "kbbi://{query}",
    title="KBBI Entry",
    description="KBBI lookup result for a word or phrase, as JSON (same payload as kbbi_lookup).",
    mime_type="application/json",
    icons=_ICONS,
)
def kbbi_resource(query: str) -> KBBILookupResult:
    """Read-only resource for `kbbi://{query}`.

    Args:
        query (str): A word or phrase to look up.

    Returns:
        KBBILookupResult: The same payload as `kbbi_lookup`.

    Raises:
        ResourceError: If KBBI cannot be reached or parsed.
    """
    try:
        return _logged_lookup(query)
    except KBBILookupError as e:
        raise ResourceError(str(e)) from e
