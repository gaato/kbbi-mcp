import kbbi_mcp.server as server


def test_slugify_query_uses_path_encoding():
    assert server._slugify_query("dua kata") == "dua%20kata"


def test_kbbi_lookup_empty_query_returns_error():
    result = server._kbbi_lookup_result("   ")
    assert result["found"] is False
    assert result["entries"] == []
    assert result["suggestions"] == []
    assert "error" in result


def test_kbbi_lookup_success(monkeypatch):
    def fake_lookup_serialized(query: str):
        assert query == "apel"
        return {
            "source_url": "https://kbbi.kemendikdasmen.go.id/entri/apel",
            "entries": [
                {
                    "headword": "apel",
                    "sense_number": "",
                    "root_words": [],
                    "pronunciation": "",
                    "nonstandard_forms": [],
                    "variants": [],
                    "definitions": [
                        {
                            "word_classes": [],
                            "glosses": ["buah"],
                            "note": "",
                            "examples": [],
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr(server, "_lookup_serialized", fake_lookup_serialized)

    result = server._kbbi_lookup_result(" apel ")
    assert result["found"] is True
    assert result["query"] == "apel"
    assert result["url"] == "https://kbbi.kemendikdasmen.go.id/entri/apel"
    assert len(result["entries"]) == 1
    assert result["suggestions"] == []
    assert "error" not in result


def test_kbbi_lookup_not_found_suggestions(monkeypatch):
    def fake_lookup_serialized(query: str):
        assert query == "asdfgh"
        return {
            "source_url": "https://kbbi.kemendikdasmen.go.id/entri/asdfgh",
            "entries": [],
            "suggestions": ["asdf", "asdh"],
        }

    monkeypatch.setattr(server, "_lookup_serialized", fake_lookup_serialized)

    result = server._kbbi_lookup_result("asdfgh")
    assert result["found"] is False
    assert result["entries"] == []
    assert result["suggestions"] == ["asdf", "asdh"]
    assert "error" not in result


def test_kbbi_lookup_unexpected_error_is_structured(monkeypatch):
    def boom(_: str):
        raise RuntimeError("network down")

    monkeypatch.setattr(server, "_lookup_serialized", boom)

    result = server._kbbi_lookup_result("apel")
    assert result["found"] is False
    assert result["entries"] == []
    assert result["suggestions"] == []
    assert "error" in result
    assert "RuntimeError" in result["error"]


def test_parse_not_found_extracts_suggestions_from_links():
    html = """
    <html><body>
      <h4>Entri tidak ditemukan.</h4>
      <ul>
        <li><a href="/entri/asdf">asdf</a></li>
        <li><a href="/entri/asdh">asdh</a></li>
      </ul>
    </body></html>
    """

    parsed = server._parse_serialized_from_html(
        html,
        "https://kbbi.kemendikdasmen.go.id/entri/asdfgh",
        "asdfgh",
    )

    assert parsed["entries"] == []
    assert parsed["suggestions"] == ["asdf", "asdh"]


def test_parse_entries_empty_extracts_suggestions():
    html = """
    <html><body>
      <h2>dummy</h2>
      <p>no definitions here</p>
      <a href="/entri/foo">foo</a>
      <a href="/entri/bar">bar</a>
    </body></html>
    """

    parsed = server._parse_serialized_from_html(
        html,
        "https://kbbi.kemendikdasmen.go.id/entri/dummy",
        "dummy",
    )

    assert parsed["entries"] == []
    assert parsed["suggestions"] == ["foo", "bar"]
