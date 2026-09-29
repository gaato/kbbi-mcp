from typing import TypedDict


class Label(TypedDict):
    """A KBBI label such as a word class (`v`) or a usage/field label (`ki`, `Tas`)."""

    code: str
    name: str
    description: str


class Example(TypedDict):
    """A usage example; `--` or `~` stands for the headword."""

    text: str
    meaning: str | None


class Sense(TypedDict):
    """One numbered meaning of an entry."""

    labels: list[Label]
    gloss: str
    examples: list[Example]


class Entry(TypedDict):
    """One headword on the page (homographs are separate entries)."""

    headword: str
    homograph: int | None
    pronunciation: str | None
    root_words: list[str]
    senses: list[Sense]


class KBBILookupResult(TypedDict):
    """JSON-serializable output payload for a KBBI lookup."""

    found: bool
    query: str
    url: str
    entries: list[Entry]
