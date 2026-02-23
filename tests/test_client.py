import json

import pytest
from conftest import _as_mapping

import kbbi_mcp
import kbbi_mcp.server as server


@pytest.mark.anyio
async def test_create_client_can_call_tool(monkeypatch):
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

    async with kbbi_mcp.create_client() as client:
        result = await client.call_tool("kbbi_lookup", {"query": "apel"})

    payload = _as_mapping(result.data)
    assert payload["found"] is True
    assert payload["query"] == "apel"
    assert payload["url"] == "https://kbbi.kemdikbud.go.id/entri/apel"
    assert len(payload["entries"]) == 1


@pytest.mark.anyio
async def test_create_client_exposes_kbbi_resource_template(monkeypatch):
    async with kbbi_mcp.create_client() as client:
        templates = await client.list_resource_templates()

    # mcp.types.ResourceTemplate has `uriTemplate`.
    uri_templates = {t.uriTemplate for t in templates}
    assert "kbbi://{query}" in uri_templates


@pytest.mark.anyio
async def test_create_client_can_read_kbbi_resource(monkeypatch):
    def fake_lookup_serialized(query: str):
        assert query == "apel"
        return {
            "pranala": "https://kbbi.kemdikbud.go.id/entri/apel",
            "entri": [],
            "saran_entri": ["apel-apel"],
        }

    monkeypatch.setattr(server, "_lookup_serialized", fake_lookup_serialized)

    async with kbbi_mcp.create_client() as client:
        contents = await client.read_resource("kbbi://apel")

    assert contents, "resource must return at least one content item"
    text = getattr(contents[0], "text", None)
    assert isinstance(text, str)

    payload = json.loads(text)
    assert payload["query"] == "apel"
    assert payload["suggestions"] == ["apel-apel"]
