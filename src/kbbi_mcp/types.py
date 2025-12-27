from typing import NotRequired, TypedDict


class _KBBIKelas(TypedDict):
    kode: str
    nama: str
    deskripsi: str


class _KBBIMakna(TypedDict):
    kelas: list[_KBBIKelas]
    submakna: list[str]
    info: str
    contoh: list[str]


class _KBBIEtimologi(TypedDict):
    bahasa: str
    kelas: list[str]
    asal_kata: str
    pelafalan: str
    arti: list[str]


class _KBBIEntriMaybeUser(TypedDict):
    nama: str
    nomor: str
    kata_dasar: list[str]
    pelafalan: str
    bentuk_tidak_baku: list[str]
    varian: list[str]
    makna: list[_KBBIMakna]

    # Present only when authenticated and `fitur_pengguna=True`.
    etimologi: NotRequired[_KBBIEtimologi | None]
    kata_turunan: NotRequired[list[str]]
    gabungan_kata: NotRequired[list[str]]
    peribahasa: NotRequired[list[str]]
    idiom: NotRequired[list[str]]


class _KBBIEntri(TypedDict):
    nama: str
    nomor: str
    kata_dasar: list[str]
    pelafalan: str
    bentuk_tidak_baku: list[str]
    varian: list[str]
    makna: list[_KBBIMakna]

    # User features (normalized for anonymous mode).
    etimologi: _KBBIEtimologi | None
    kata_turunan: list[str]
    gabungan_kata: list[str]
    peribahasa: list[str]
    idiom: list[str]


class _KBBISerialisasi(TypedDict):
    pranala: str
    entri: list[_KBBIEntriMaybeUser]
    saran_entri: NotRequired[list[str]]


class KBBILookupResult(TypedDict):
    """JSON-serializable output payload for a KBBI lookup."""

    found: bool
    query: str
    url: str | None
    entries: list[_KBBIEntri]
    suggestions: list[str]
    error: NotRequired[str]
