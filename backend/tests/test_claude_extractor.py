"""Tests for ClaudeExtractor's image-preparation and response-handling paths.

No network calls: `messages.create` on the (real) AsyncAnthropic client is
replaced with a stub coroutine per test. Async test bodies are driven with
`asyncio.run` directly rather than pytest-asyncio, since that plugin isn't
part of this project's test dependencies.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from PIL import Image

from app.services.claude_extractor import ClaudeExtractor, ExtractionError


def _make_photo(tmp_path, name="photo.jpg", size=(200, 150)):
    path = tmp_path / name
    Image.new("RGB", size, (100, 120, 140)).save(path, format="JPEG", quality=90)
    return path


def _fake_response(text: str, stop_reason: str = "end_turn"):
    content = [SimpleNamespace(type="text", text=text)] if text else []
    return SimpleNamespace(
        content=content,
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        stop_reason=stop_reason,
    )


def test_extract_sends_one_image_block_per_photo_not_combined(tmp_path):
    """A 3-photo tag must produce exactly 3 image content blocks — photos
    are never merged into a single combined image."""
    extractor = ClaudeExtractor(api_key="sk-test-dummy")
    photos = [str(_make_photo(tmp_path, f"p{i}.jpg")) for i in range(3)]
    captured = {}

    async def fake_create(**kwargs):
        captured["content"] = kwargs["messages"][0]["content"]
        payload = '{"fields": {}, "remarks": "", "photo_status": "EASY", "qc_comment": ""}'
        return _fake_response(payload)

    extractor._client.messages.create = fake_create

    result = asyncio.run(extractor.extract(photos, "12-TAG-0001", "TEST VALVE"))

    image_blocks = [b for b in captured["content"] if b["type"] == "image"]
    assert len(image_blocks) == 3
    assert result.payload["fields"]["tag_number"]["value"] == "12-TAG-0001"


def test_extract_optimizes_before_building_the_request(tmp_path, monkeypatch):
    """Compression must happen BEFORE the Claude request is built — the
    bytes captured in the request must be the optimizer's output, not the
    raw file, whenever optimization actually changes them."""
    from app.services import claude_extractor as ce

    calls = []

    def fake_prepare(paths):
        calls.append(list(paths))
        return [
            SimpleNamespace(
                data=b"FAKE-OPTIMIZED-BYTES", media_type="image/jpeg",
                was_optimized=True, original_bytes=999999, final_bytes=21,
            )
            for _ in paths
        ]

    monkeypatch.setattr(ce, "prepare_images_for_claude", fake_prepare)

    extractor = ClaudeExtractor(api_key="sk-test-dummy")
    photos = [str(_make_photo(tmp_path))]
    captured = {}

    async def fake_create(**kwargs):
        captured["content"] = kwargs["messages"][0]["content"]
        return _fake_response('{"fields": {}, "remarks": "", "photo_status": "EASY", "qc_comment": ""}')

    extractor._client.messages.create = fake_create

    asyncio.run(extractor.extract(photos, "12-TAG-0001", "TEST VALVE"))

    assert len(calls) == 1  # prepare_images_for_claude called exactly once, for the whole tag
    import base64
    image_block = next(b for b in captured["content"] if b["type"] == "image")
    assert base64.standard_b64decode(image_block["source"]["data"]) == b"FAKE-OPTIMIZED-BYTES"


def test_extract_raises_retryable_on_empty_response(tmp_path):
    extractor = ClaudeExtractor(api_key="sk-test-dummy")
    photos = [str(_make_photo(tmp_path))]

    async def fake_create(**kwargs):
        return _fake_response("", stop_reason="max_tokens")

    extractor._client.messages.create = fake_create

    try:
        asyncio.run(extractor.extract(photos, "12-TAG-0001", "TEST VALVE"))
        assert False, "expected ExtractionError"
    except ExtractionError as exc:
        assert exc.retryable is True
        assert "empty response" in str(exc)


def test_extract_raises_retryable_on_whitespace_only_response(tmp_path):
    extractor = ClaudeExtractor(api_key="sk-test-dummy")
    photos = [str(_make_photo(tmp_path))]

    async def fake_create(**kwargs):
        return _fake_response("   \n\t  ")

    extractor._client.messages.create = fake_create

    try:
        asyncio.run(extractor.extract(photos, "12-TAG-0001", "TEST VALVE"))
        assert False, "expected ExtractionError"
    except ExtractionError as exc:
        assert exc.retryable is True
