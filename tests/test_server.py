import pytest
from conftest import fixture_html

import kbbi_mcp.server as server

URL = "https://kbbi.kemendikdasmen.go.id/entri/"


def parse(name: str, query: str):
    return server._parse_html(fixture_html(name), URL + query, query)


def test_slugify_query_uses_path_encoding():
    assert server._slugify_query("dua kata") == "dua%20kata"
    assert server._build_entri_url("https://example.test///", "  A/B é  ") == (
        "https://example.test/entri/a%2Fb%20%C3%A9"
    )


def test_makan_entries_labels_examples_and_meanings():
    result = parse("makan", "makan")
    assert result["found"] is True
    assert len(result["entries"]) == 2

    first = result["entries"][0]
    assert first["headword"] == "makan"
    assert first["homograph"] == 1
    assert len(first["senses"]) == 15

    sense = first["senses"][0]
    assert sense["labels"] == [{"code": "v", "name": "Verba", "description": "kata kerja"}]
    assert sense["gloss"] == (
        "memasukkan makanan pokok ke dalam mulut serta mengunyah dan menelannya"
    )
    assert sense["examples"] == [{"text": "mereka -- tiga kali sehari", "meaning": None}]
    assert len(first["senses"][5]["examples"]) == 2

    # Example meanings are paired with their example, not leaked into the gloss.
    assert first["senses"][10]["examples"] == [
        {"text": "layarnya tidak --", "meaning": "tidak memperoleh angin"},
        {"text": "sauhnya dapat --", "meaning": "mencapai dasar laut"},
    ]
    assert "angin" not in first["senses"][10]["gloss"]
    assert first["senses"][12]["labels"] == [
        {"code": "v", "name": "Verba", "description": "kata kerja"},
        {"code": "ki", "name": "kiasan", "description": ""},
    ]

    second = result["entries"][1]
    assert second["homograph"] == 2
    assert len(second["senses"]) == 1
    assert second["senses"][0]["labels"] == [
        {"code": "n", "name": "Nomina", "description": "kata benda"},
        {"code": "Tas", "name": "Tasawuf", "description": "-"},
    ]


def test_gemas_pronunciation_and_schema():
    assert parse("gemas", "gemas") == {
        "found": True,
        "query": "gemas",
        "url": URL + "gemas",
        "entries": [
            {
                "headword": "gemas",
                "homograph": None,
                "pronunciation": "/gêmas/",
                "root_words": [],
                "senses": [
                    {
                        "labels": [
                            {
                                "code": "a",
                                "name": "Adjektiva",
                                "description": "kata yang menjelaskan nomina atau pronomina",
                            }
                        ],
                        "gloss": "sangat jengkel (marah) dalam hati",
                        "examples": [
                            {
                                "text": (
                                    "saya sangat -- pada anak itu karena selalu mengotori lantai"
                                ),
                                "meaning": None,
                            }
                        ],
                    },
                    {
                        "labels": [
                            {
                                "code": "a",
                                "name": "Adjektiva",
                                "description": "kata yang menjelaskan nomina atau pronomina",
                            }
                        ],
                        "gloss": "sangat suka (cinta) bercampur jengkel; jengkel-jengkel cinta",
                        "examples": [{"text": "-- aku melihat anak ini", "meaning": None}],
                    },
                ],
            }
        ],
    }


def test_root_word_and_phrase_headword():
    punya = parse("mempunyai", "mempunyai")
    assert punya["entries"][0]["headword"] == "mempunyai"
    assert punya["entries"][0]["root_words"] == ["punya"]

    # The root word's own homograph number is neither part of the root nor ours.
    berlari = parse("berlari", "berlari")["entries"][0]
    assert berlari["headword"] == "berlari"
    assert berlari["root_words"] == ["lari"]
    assert berlari["homograph"] is None

    rumah = parse("rumah_sakit", "rumah sakit")
    assert rumah["entries"][0]["headword"] == "rumah sakit"


def test_not_found_page():
    result = parse("xyzqwe", "xyzqwe")
    assert result["found"] is False
    assert result["entries"] == []


def test_heading_without_senses_is_not_an_entry():
    result = server._parse_html("<h2>foo</h2><h4>other</h4>", "u", "foo")
    assert result["found"] is False


def test_first_sibling_sense_list_and_invalid_homograph():
    result = server._parse_html(
        "<h2>te.st<sup>x</sup></h2><div><ol><li>nested</li></ol></div>"
        "<ul><li>first</li></ul><ol><li>later</li></ol>",
        "u",
        "test",
    )
    assert len(result["entries"]) == 1
    entry = result["entries"][0]
    assert entry["headword"] == "test"
    assert entry["homograph"] is None
    assert [s["gloss"] for s in entry["senses"]] == ["first"]


def test_lookup_trims_query_and_fetches_once(serve_fixture):
    fetched = serve_fixture("gemas")
    result = server._kbbi_lookup_result("  gemas ")
    assert result["query"] == "gemas"
    assert result["url"] == URL + "gemas"
    assert fetched == [URL + "gemas"]

    server._kbbi_lookup_result("gemas")
    assert len(fetched) == 1, "repeat lookups are served from the cache"


def test_lookup_empty_query_raises():
    with pytest.raises(server.KBBILookupError, match="must not be empty"):
        server._kbbi_lookup_result("   ")


def test_lookup_unexpected_error_raises(monkeypatch):
    def boom(url: str, timeout_seconds: float) -> str:
        raise RuntimeError("network down")

    monkeypatch.setattr(server, "_fetch_html", boom)

    with pytest.raises(server.KBBILookupError, match="RuntimeError: network down"):
        server._kbbi_lookup_result("apel")
