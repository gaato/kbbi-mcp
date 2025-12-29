import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Any, cast

from fastmcp import Client, Context, FastMCP
from kbbi import KBBI, AutentikasiKBBI, TidakDitemukan

from .settings import get_settings
from .types import KBBILookupResult, _KBBIEntri, _KBBIEntriMaybeUser, _KBBISerialisasi


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

Anonymous mode works out of the box.
Optional authenticated mode via env: KBBI_EMAIL, KBBI_PASSWORD (and optional KBBI_COOKIE_PATH).
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


@contextmanager
def _suppress_kbbi_deprecations() -> Iterator[None]:
    """Suppress noisy deprecation warnings emitted by `kbbi` internals.

    Yields:
        None: Control with kbbi deprecation warnings suppressed.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            module=r"kbbi\..*",
        )
        yield


def _normalize_entry(entry: _KBBIEntriMaybeUser) -> _KBBIEntri:
    """Normalize an entry dict so downstream clients get a stable shape.

    Args:
        entry (_KBBIEntriMaybeUser): Entry payload from `kbbi.KBBI.serialisasi()`.

    Returns:
        _KBBIEntri: Normalized entry payload.
    """
    return {
        "nama": entry["nama"],
        "nomor": entry["nomor"],
        "kata_dasar": entry["kata_dasar"],
        "pelafalan": entry["pelafalan"],
        "bentuk_tidak_baku": entry["bentuk_tidak_baku"],
        "varian": entry["varian"],
        "makna": entry["makna"],
        # User features (may be absent in anonymous mode).
        "etimologi": entry.get("etimologi"),
        "kata_turunan": entry.get("kata_turunan", []),
        "gabungan_kata": entry.get("gabungan_kata", []),
        "peribahasa": entry.get("peribahasa", []),
        "idiom": entry.get("idiom", []),
    }


@lru_cache(maxsize=1)
def _get_auth() -> AutentikasiKBBI | None:
    """Create an authenticated KBBI session, if credentials are configured.

    Returns:
        AutentikasiKBBI | None: Auth session, or `None` for anonymous mode.
    """
    settings = get_settings()

    if not settings.has_credentials():
        return None

    # AutentikasiKBBI persists cookies by default (platform-dependent path).
    if settings.cookie_path:
        return AutentikasiKBBI(settings.email, settings.password, lokasi_kuki=settings.cookie_path)

    return AutentikasiKBBI(settings.email, settings.password)


@lru_cache(maxsize=256)
def _lookup_serialized(query: str) -> _KBBISerialisasi:
    """Look up a query in KBBI and return the raw `serialisasi()` dictionary.

    Args:
        query (str): A word or phrase to look up.

    Returns:
        _KBBISerialisasi: A dict matching `_KBBISerialisasi`.
    """
    auth = _get_auth()

    with _suppress_kbbi_deprecations():
        try:
            entry = KBBI(query, auth) if auth is not None else KBBI(query)
        except TidakDitemukan as e:
            # The exception carries an object with suggestions.
            entry = e.objek

        # kbbi-python returns JSON-serializable dicts, but the library isn't typed.
        raw: dict[str, Any] = cast(Any, entry).serialisasi()
        return cast(_KBBISerialisasi, raw)


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
