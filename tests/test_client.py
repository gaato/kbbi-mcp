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

    async with kbbi_mcp.create_client() as client:
        result = await client.call_tool("kbbi_lookup", {"query": "apel"})

    payload = _as_mapping(result.data)
    assert payload["found"] is True
    assert payload["query"] == "apel"
    assert payload["url"] == "https://kbbi.kemendikdasmen.go.id/entri/apel"
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
            "source_url": "https://kbbi.kemendikdasmen.go.id/entri/apel",
            "entries": [],
            "suggestions": ["apel-apel"],
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
