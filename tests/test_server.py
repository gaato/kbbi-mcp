import kbbi_mcp.server as server


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
            "pranala": "https://kbbi.kemdikbud.go.id/entri/apel",
            "entri": [
                {
                    "nama": "apel",
                    "nomor": "",
                    "kata_dasar": [],
                    "pelafalan": "",
                    "bentuk_tidak_baku": [],
                    "varian": [],
                    "makna": [
                        {
                            "kelas": [],
                            "submakna": ["buah"],
                            "info": "",
                            "contoh": [],
                        }
                    ],
                }
            ],
        }

    monkeypatch.setattr(server, "_lookup_serialized", fake_lookup_serialized)

    result = server._kbbi_lookup_result(" apel ")
    assert result["found"] is True
    assert result["query"] == "apel"
    assert result["url"] == "https://kbbi.kemdikbud.go.id/entri/apel"
    assert len(result["entries"]) == 1
    assert result["suggestions"] == []
    assert "error" not in result


def test_kbbi_lookup_not_found_suggestions(monkeypatch):
    def fake_lookup_serialized(query: str):
        assert query == "asdfgh"
        return {
            "pranala": "https://kbbi.kemdikbud.go.id/entri/asdfgh",
            "entri": [],
            "saran_entri": ["asdf", "asdh"],
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
