from collections.abc import Sequence
from os import PathLike
from typing import Any, NotRequired, TypedDict

class KBBIKelas(TypedDict):
    kode: str
    nama: str
    deskripsi: str

class KBBIMakna(TypedDict):
    kelas: list[KBBIKelas]
    submakna: list[str]
    info: str
    contoh: list[str]

class KBBIEtimologi(TypedDict):
    bahasa: str
    kelas: list[str]
    asal_kata: str
    pelafalan: str
    arti: list[str]

class KBBIEntri(TypedDict):
    nama: str
    nomor: str
    kata_dasar: list[str]
    pelafalan: str
    bentuk_tidak_baku: list[str]
    varian: list[str]
    makna: list[KBBIMakna]

    # Present only when authenticated and `fitur_pengguna=True`.
    etimologi: NotRequired[KBBIEtimologi | None]
    kata_turunan: NotRequired[list[str]]
    gabungan_kata: NotRequired[list[str]]
    peribahasa: NotRequired[list[str]]
    idiom: NotRequired[list[str]]

class KBBISerialisasi(TypedDict):
    pranala: str
    entri: list[KBBIEntri]

    # Present only when authenticated and `fitur_pengguna=True` and no entries found.
    saran_entri: NotRequired[list[str]]

class Galat(Exception):
    pass

class TidakDitemukan(Galat):
    objek: KBBI

    def __init__(self, kueri: str, objek: KBBI | None = ...) -> None: ...

class TerjadiKesalahan(Galat):
    def __init__(self) -> None: ...

class BatasSehari(Galat):
    def __init__(self) -> None: ...

class AkunDibekukan(Galat):
    def __init__(self) -> None: ...

class GagalAutentikasi(Galat):
    def __init__(self, pesan: str | None = ...) -> None: ...

class KukiTidakDitemukan(GagalAutentikasi):
    def __init__(self, lokasi_kuki: str | PathLike[str], posel_sandi: bool = ...) -> None: ...

class AutentikasiKBBI:
    host: str
    lokasi: str
    lokasi_kuki: Any
    sesi: Any

    def __init__(
        self,
        posel: str | None = ...,
        sandi: str | None = ...,
        lokasi_kuki: str | PathLike[str] | None = ...,
    ) -> None: ...
    def simpan_kuki(self) -> None: ...

class KBBI:
    host: str

    nama: str
    entri: list[Any]
    saran_entri: list[str]
    terautentikasi: bool

    def __init__(self, kueri: str, auth: AutentikasiKBBI | None = ...) -> None: ...
    def serialisasi(self, fitur_pengguna: bool = ...) -> KBBISerialisasi: ...
    def __str__(
        self, contoh: bool = ..., terkait: bool = ..., fitur_pengguna: bool = ...
    ) -> str: ...

def autentikasi(argv: Sequence[str] | None = ...) -> int: ...
def main(argv: Sequence[str] | None = ...) -> int: ...
