from typing import NotRequired, TypedDict


class _WordClass(TypedDict):
    code: str
    name: str
    description: str


class _Definition(TypedDict):
    word_classes: list[_WordClass]
    glosses: list[str]
    note: str
    examples: list[str]


class _Etymology(TypedDict):
    language: str
    classes: list[str]
    source_word: str
    pronunciation: str
    meanings: list[str]


class _Entry(TypedDict):
    headword: str
    sense_number: str
    root_words: list[str]
    pronunciation: str
    nonstandard_forms: list[str]
    variants: list[str]
    definitions: list[_Definition]

    # Optional related fields (normalized to stable defaults).
    etymology: _Etymology | None
    derived_words: list[str]
    compound_words: list[str]
    proverbs: list[str]
    idioms: list[str]


class _LookupSerialized(TypedDict):
    source_url: str
    entries: list[_Entry]
    suggestions: NotRequired[list[str]]


class KBBILookupResult(TypedDict):
    """JSON-serializable output payload for a KBBI lookup."""

    found: bool
    query: str
    url: str | None
    entries: list[_Entry]
    suggestions: list[str]
    error: NotRequired[str]
