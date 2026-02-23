from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Any

from bs4 import BeautifulSoup
from fastmcp import Client, Context, FastMCP

from .settings import get_settings
from .types import KBBILookupResult, _KBBIEntri, _KBBISerialisasi


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
- Primary: official KBBI VI Daring host
- Fallback: public mirror (kbbi.web.id) when the official host is unreachable
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
    return urllib.parse.quote_plus(query.strip().lower())


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
    """Return (nama, nomor) parsed from an <h2> text.

    The page often renders forms like `a.pel1` (with <sup>1</sup>) or
    `a.pel /apêl/`.
    """
    text = " ".join(raw.split()).strip()
    if not text:
        return fallback_query, ""

    match = re.search(r"^(.*?)(\d+)$", text)
    if match:
        nama = match.group(1).strip() or fallback_query
        nomor = match.group(2)
    else:
        nama = text
        nomor = ""

    # Remove syllable markers like a.pel -> apel for a cleaner canonical name.
    nama = nama.replace(".", "").strip()
    return nama or fallback_query, nomor


def _extract_makna_from_li(li: Any) -> dict[str, Any]:
    kelas: list[dict[str, str]] = []
    for span in li.select("font[color='red'] span"):
        kode = span.get_text(" ", strip=True)
        title = (span.get("title") or "").strip()
        name, _, desc = title.partition(":")
        kelas.append(
            {
                "kode": kode,
                "nama": (name or kode).strip(),
                "deskripsi": desc.strip(),
            }
        )

    contoh = [ex.get_text(" ", strip=True) for ex in li.select("font[color='grey'] i")]
    contoh = [c for c in contoh if c]

    # Build definition text without class/example decorations.
    li_copy = BeautifulSoup(str(li), "html.parser")
    for noisy in li_copy.select("font[color='red'], font[color='grey']"):
        noisy.decompose()
    submakna_text = li_copy.get_text(" ", strip=True)

    return {
        "kelas": kelas,
        "submakna": [submakna_text] if submakna_text else [],
        "info": "",
        "contoh": contoh,
    }


def _normalize_entry(entry: dict[str, Any]) -> _KBBIEntri:
    """Normalize an entry dict so downstream clients get a stable shape."""
    return {
        "nama": entry.get("nama", ""),
        "nomor": entry.get("nomor", ""),
        "kata_dasar": entry.get("kata_dasar", []),
        "pelafalan": entry.get("pelafalan", ""),
        "bentuk_tidak_baku": entry.get("bentuk_tidak_baku", []),
        "varian": entry.get("varian", []),
        "makna": entry.get("makna", []),
        "etimologi": entry.get("etimologi"),
        "kata_turunan": entry.get("kata_turunan", []),
        "gabungan_kata": entry.get("gabungan_kata", []),
        "peribahasa": entry.get("peribahasa", []),
        "idiom": entry.get("idiom", []),
    }


def _parse_serialized_from_html(html: str, url: str, query: str) -> _KBBISerialisasi:
    soup = BeautifulSoup(html, "html.parser")

    page_text = soup.get_text(" ", strip=True).lower()
    if "entri tidak ditemukan" in page_text:
        return {
            "pranala": url,
            "entri": [],
            "saran_entri": [],
        }

    entries: list[_KBBIEntri] = []
    for h2 in soup.find_all("h2"):
        title_text = h2.get_text(" ", strip=True)
        if not title_text:
            continue

        nama, nomor = _clean_headword(title_text, query)
        pelafalan_el = h2.select_one("span.syllable")
        pelafalan = pelafalan_el.get_text(" ", strip=True) if pelafalan_el else ""

        # Collect the first list (<ol>/<ul>) after the header before next <h2>.
        makna_items: list[dict[str, Any]] = []
        for sibling in h2.next_siblings:
            sibling_name = getattr(sibling, "name", None)
            if sibling_name == "h2":
                break
            if sibling_name in {"ol", "ul"}:
                lis = sibling.find_all("li")
                for li in lis:
                    makna_items.append(_extract_makna_from_li(li))
                if lis:
                    break

        if not makna_items:
            continue

        entries.append(
            {
                "nama": nama,
                "nomor": nomor,
                "kata_dasar": [],
                "pelafalan": pelafalan,
                "bentuk_tidak_baku": [],
                "varian": [],
                "makna": makna_items,
                "etimologi": None,
                "kata_turunan": [],
                "gabungan_kata": [],
                "peribahasa": [],
                "idiom": [],
            }
        )

    return {
        "pranala": url,
        "entri": entries,
        "saran_entri": [],
    }


@lru_cache(maxsize=256)
def _lookup_serialized(query: str) -> _KBBISerialisasi:
    """Look up a query in KBBI and return a serialized dictionary.

    Args:
        query (str): A word or phrase to look up.

    Returns:
        _KBBISerialisasi: A dictionary compatible with the previous kbbi lib shape.
    """
    settings = get_settings()
    official_url = _build_entri_url(settings.base_url, query)

    try:
        html = _fetch_html(official_url, timeout_seconds=settings.timeout_seconds)
        return _parse_serialized_from_html(html, official_url, query)
    except (urllib.error.URLError, TimeoutError):
        fallback_url = _build_entri_url(settings.fallback_base_url, query)
        html = _fetch_html(fallback_url, timeout_seconds=settings.timeout_seconds)
        return _parse_serialized_from_html(html, fallback_url, query)


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

    entries = [_normalize_entry(e) for e in serialized.get("entri", [])]
    suggestions = serialized.get("saran_entri", [])

    return {
        "found": len(entries) > 0,
        "query": normalized_query,
        "url": serialized.get("pranala"),
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
