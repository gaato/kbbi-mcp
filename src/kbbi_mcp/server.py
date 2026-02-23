from __future__ import annotations

import re
import urllib.parse
import urllib.request
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Any

from bs4 import BeautifulSoup, Tag
from fastmcp import Client, Context, FastMCP

from .settings import get_settings
from .types import KBBILookupResult, _Definition, _Entry, _LookupSerialized, _WordClass


def _get_package_version() -> str | None:
    """Return the installed package version, if available.

    Returns:
        str | None: The version string, or None when running from source without metadata.
    """
    try:
        return package_version("kbbi-mcp")
    except PackageNotFoundError:
        return None


_INSTRUCTIONS = """\
Query KBBI (Kamus Besar Bahasa Indonesia / KBBI Daring).

- Tool: kbbi_lookup(query: str) -> JSON
- Resource: kbbi://{query} (same payload)

Data source policy:
- Official KBBI VI Daring host by default
"""


mcp = FastMCP(
    name="KBBI MCP",
    instructions=_INSTRUCTIONS,
    version=_get_package_version(),
    website_url="https://github.com/gaato/kbbi-mcp",
)


def create_mcp() -> FastMCP:
    """Return the FastMCP server instance.

    This makes it easy to embed the server in-process (e.g. for testing or to
    pass it directly to libraries like Pydantic AI's `FastMCPToolset`).

    Returns:
        FastMCP: The configured server instance.
    """
    return mcp


def create_client() -> Client[Any]:
    """Create an in-memory FastMCP client connected to this server.

    This avoids spawning a subprocess or using a network transport, which is
    ideal for deterministic unit tests and Python integrations.

    Returns:
        Client[Any]: A FastMCP client using in-memory transport.
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
            "User-Agent": "kbbi-mcp/0 (https://github.com/gaato/kbbi-mcp)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as res:
        return res.read().decode("utf-8", errors="ignore")


def _clean_headword(raw: str, fallback_query: str) -> tuple[str, str]:
    """Return (headword, sense_number) parsed from an <h2> text.

    The page often renders forms like `a.pel1` (with <sup>1</sup>) or
    `a.pel /apêl/`.
    """
    text = " ".join(raw.split()).strip()
    if not text:
        return fallback_query, ""

    match = re.search(r"^(.*?)(\d+)$", text)
    if match:
        headword = match.group(1).strip() or fallback_query
        sense_number = match.group(2)
    else:
        headword = text
        sense_number = ""

    # Remove syllable markers like a.pel -> apel for a cleaner canonical name.
    headword = headword.replace(".", "").strip()
    return headword or fallback_query, sense_number


def _extract_definition_from_li(li: Tag) -> _Definition:
    word_classes: list[_WordClass] = []
    for span in li.select("font[color='red'] span"):
        code = span.get_text(" ", strip=True)
        title = str(span.get("title") or "").strip()
        name, _, description = title.partition(":")
        word_classes.append({
            "code": code,
            "name": (name or code).strip(),
            "description": description.strip(),
        })

    examples = [ex.get_text(" ", strip=True) for ex in li.select("font[color='grey'] i")]
    examples = [c for c in examples if c]

    # Build definition text without class/example decorations.
    li_copy = BeautifulSoup(str(li), "html.parser")
    for noisy in li_copy.select("font[color='red'], font[color='grey']"):
        noisy.decompose()
    gloss_text = li_copy.get_text(" ", strip=True)

    return {
        "word_classes": word_classes,
        "glosses": [gloss_text] if gloss_text else [],
        "note": "",
        "examples": examples,
    }


def _normalize_entry(entry: dict[str, Any]) -> _Entry:
    """Normalize an entry dict so downstream clients get a stable shape.

    Args:
        entry (dict[str, Any]): A partially populated entry payload.

    Returns:
        _Entry: Entry payload with all optional fields normalized.
    """
    return {
        "headword": entry.get("headword", ""),
        "sense_number": entry.get("sense_number", ""),
        "root_words": entry.get("root_words", []),
        "pronunciation": entry.get("pronunciation", ""),
        "nonstandard_forms": entry.get("nonstandard_forms", []),
        "variants": entry.get("variants", []),
        "definitions": entry.get("definitions", []),
        "etymology": entry.get("etymology"),
        "derived_words": entry.get("derived_words", []),
        "compound_words": entry.get("compound_words", []),
        "proverbs": entry.get("proverbs", []),
        "idioms": entry.get("idioms", []),
    }


def _extract_suggestions(soup: BeautifulSoup, query: str) -> list[str]:
    """Best-effort extraction of suggestion terms from entry links.

    Args:
        soup (BeautifulSoup): Parsed HTML document.
        query (str): Original query string.

    Returns:
        list[str]: Deduplicated suggestion list.
    """
    suggestions: list[str] = []
    seen: set[str] = set()
    normalized_query = query.strip().lower()

    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "")
        if "/entri/" not in href:
            continue

        text = a.get_text(" ", strip=True)
        if not text:
            continue

        key = text.lower()
        if key == normalized_query or key in seen:
            continue

        seen.add(key)
        suggestions.append(text)

    return suggestions


def _parse_serialized_from_html(html: str, url: str, query: str) -> _LookupSerialized:
    soup = BeautifulSoup(html, "html.parser")

    page_text = soup.get_text(" ", strip=True).lower()
    if "entri tidak ditemukan" in page_text:
        return {
            "source_url": url,
            "entries": [],
            "suggestions": _extract_suggestions(soup, query),
        }

    entries: list[_Entry] = []
    for h2 in soup.find_all("h2"):
        title_text = h2.get_text(" ", strip=True)
        if not title_text:
            continue

        headword, sense_number = _clean_headword(title_text, query)
        pronunciation_el = h2.select_one("span.syllable")
        pronunciation = pronunciation_el.get_text(" ", strip=True) if pronunciation_el else ""

        # Collect the first list (<ol>/<ul>) after the header before next <h2>.
        definitions: list[_Definition] = []
        for sibling in h2.next_siblings:
            if not isinstance(sibling, Tag):
                continue

            if sibling.name == "h2":
                break

            if sibling.name in {"ol", "ul"}:
                lis = sibling.find_all("li")
                for li in lis:
                    if isinstance(li, Tag):
                        definitions.append(_extract_definition_from_li(li))
                if lis:
                    break

        if not definitions:
            continue

        entries.append({
            "headword": headword,
            "sense_number": sense_number,
            "root_words": [],
            "pronunciation": pronunciation,
            "nonstandard_forms": [],
            "variants": [],
            "definitions": definitions,
            "etymology": None,
            "derived_words": [],
            "compound_words": [],
            "proverbs": [],
            "idioms": [],
        })

    return {
        "source_url": url,
        "entries": entries,
        "suggestions": [] if entries else _extract_suggestions(soup, query),
    }


@lru_cache(maxsize=256)
def _lookup_serialized(query: str) -> _LookupSerialized:
    """Look up a query in KBBI and return a normalized serialized dictionary.

    Args:
        query (str): A word or phrase to look up.

    Returns:
        _LookupSerialized: Source URL, normalized entries, and suggestions.
    """
    settings = get_settings()
    official_url = _build_entri_url(settings.base_url, query)

    html = _fetch_html(official_url, timeout_seconds=settings.timeout_seconds)
    return _parse_serialized_from_html(html, official_url, query)


def _kbbi_lookup_result(query: str) -> KBBILookupResult:
    normalized_query = query.strip()
    if not normalized_query:
        return {
            "found": False,
            "query": query,
            "url": None,
            "entries": [],
            "suggestions": [],
            "error": "query must not be empty",
        }

    try:
        serialized = _lookup_serialized(normalized_query)
    except Exception as e:
        return {
            "found": False,
            "query": normalized_query,
            "url": None,
            "entries": [],
            "suggestions": [],
            "error": f"{type(e).__name__}: {e}",
        }

    entries = [_normalize_entry(e) for e in serialized.get("entries", [])]
    suggestions = serialized.get("suggestions", [])

    return {
        "found": len(entries) > 0,
        "query": normalized_query,
        "url": serialized.get("source_url"),
        "entries": entries,
        "suggestions": suggestions,
    }


@mcp.tool
async def kbbi_lookup(query: str, ctx: Context) -> KBBILookupResult:
    """Look up a word or phrase in KBBI and return structured JSON.

    Args:
        query (str): A word or phrase to look up.
        ctx (Context): FastMCP context for logging and request-scoped metadata.

    Returns:
        KBBILookupResult: A stable, JSON-serializable object containing lookup results.
    """
    await ctx.info(
        "kbbi_lookup called",
        extra={"query": query},
    )

    result = _kbbi_lookup_result(query)
    result_query = result.get("query", query)

    if "error" in result:
        await ctx.warning(
            "kbbi_lookup returned an error",
            extra={"query": result_query, "error": result.get("error")},
        )
        return result

    if result["found"]:
        await ctx.info(
            "kbbi_lookup found entries",
            extra={"query": result_query, "entries": len(result["entries"])},
        )
        return result

    await ctx.info(
        "kbbi_lookup found no entries",
        extra={"query": result_query, "suggestions": len(result["suggestions"])},
    )
    return result


@mcp.resource("kbbi://{query}")
def kbbi_resource(query: str) -> KBBILookupResult:
    """Read-only resource for `kbbi://{query}`.

    Args:
        query (str): A word or phrase to look up.

    Returns:
        KBBILookupResult: The same payload as `kbbi_lookup`.
    """
    return _kbbi_lookup_result(query)
