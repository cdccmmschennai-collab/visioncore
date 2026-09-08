"""Tests for the adaptive Claude-image optimizer.

These exercise `optimize_for_claude` directly against real Pillow-generated
images on disk (a temp dir per test, via pytest's `tmp_path`) — no DB, no
network, no Anthropic client needed.
"""
from __future__ import annotations

import io
import random

import pytest
from PIL import Image

from app.core.config import settings
from app.services.image_optimizer import (
    ImageValidationError,
    _looks_blank,
    _validate_optimized,
    optimize_for_claude,
    prepare_images_for_claude,
)


def _save_jpeg(path, size, color=(120, 140, 160), quality=95) -> bytes:
    img = Image.new("RGB", size, color)
    img.save(path, format="JPEG", quality=quality)
    return path.read_bytes()


def _save_noisy_jpeg(path, size, quality=95) -> bytes:
    """A random-noise JPEG compresses poorly (unlike a flat color), so its
    encoded size actually varies meaningfully with quality/dimension —
    needed to exercise the hard-cap fallback and combined-budget tightening,
    which a solid-color test image would defeat (it's tiny at any setting)."""
    rng = random.Random(42)
    img = Image.new("RGB", size)
    img.putdata([
        (rng.randrange(256), rng.randrange(256), rng.randrange(256))
        for _ in range(size[0] * size[1])
    ])
    img.save(path, format="JPEG", quality=quality)
    return path.read_bytes()


def test_small_reasonable_image_is_sent_unchanged(tmp_path):
    """A photo already under both thresholds must not be re-encoded at all
    — same bytes in, same bytes out, so there is zero quality loss."""
    path = tmp_path / "small.jpg"
    original = _save_jpeg(path, (400, 300))

    result = optimize_for_claude(path)

    assert result.was_optimized is False
    assert result.data == original
    assert result.media_type == "image/jpeg"


def test_oversized_dimension_is_downscaled_preserving_aspect_ratio(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "claude_image_max_dimension_px", 800)
    path = tmp_path / "big.jpg"
    _save_jpeg(path, (4000, 3000))  # 4:3, well over the 800px cap

    result = optimize_for_claude(path)

    assert result.was_optimized is True
    with Image.open(io.BytesIO(result.data)) as out:
        width, height = out.size
        assert max(width, height) <= 800
        # aspect ratio preserved within integer-rounding tolerance
        assert abs((width / height) - (4000 / 3000)) < 0.01


def test_oversized_bytes_below_the_dimension_cap_still_get_recompressed(tmp_path, monkeypatch):
    """Even a photo with modest dimensions gets a smaller in-memory copy if
    its byte size alone crosses the threshold (e.g. a very detailed/noisy
    photo that compresses poorly)."""
    monkeypatch.setattr(settings, "claude_image_max_bytes", 1024)  # force the recompress path
    path = tmp_path / "heavy.jpg"
    original = _save_jpeg(path, (1000, 800), quality=100)
    assert path.stat().st_size > 1024

    result = optimize_for_claude(path)

    assert result.was_optimized is True
    assert result.data != original
    with Image.open(io.BytesIO(result.data)) as out:
        assert out.format == "JPEG"


def test_original_file_on_disk_is_never_modified(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "claude_image_max_dimension_px", 100)
    path = tmp_path / "photo.jpg"
    original = _save_jpeg(path, (2000, 1500))

    optimize_for_claude(path)

    assert path.read_bytes() == original


def test_exif_rotation_is_baked_in_not_lost(tmp_path, monkeypatch):
    """Orientation 6 means 'rotate 90 CW to display correctly' — a viewer
    swaps width/height for it. exif_transpose must apply that before resize,
    so the optimized copy's stored (already-correct) dimensions reflect it,
    not the raw sensor dimensions."""
    monkeypatch.setattr(settings, "claude_image_max_dimension_px", 50)  # force the resize path
    path = tmp_path / "rotated.jpg"
    img = Image.new("RGB", (200, 100), (10, 20, 30))  # stored landscape
    exif = img.getexif()
    exif[0x0112] = 6  # Orientation tag
    img.save(path, format="JPEG", exif=exif)

    result = optimize_for_claude(path)

    with Image.open(io.BytesIO(result.data)) as out:
        # Corrected-for-display orientation is portrait (100x200 rotated),
        # so after downscaling to fit 50px the output must stay taller than
        # it is wide.
        assert out.size[1] >= out.size[0]


def test_corrupt_image_falls_back_to_raw_bytes(tmp_path):
    path = tmp_path / "corrupt.jpg"
    path.write_bytes(b"not actually a jpeg")

    result = optimize_for_claude(path)

    assert result.was_optimized is False
    assert result.data == b"not actually a jpeg"


def test_rgba_png_is_flattened_to_rgb_on_white(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "claude_image_max_bytes", 1)  # force optimization
    path = tmp_path / "transparent.png"
    img = Image.new("RGBA", (300, 300), (0, 0, 0, 0))  # fully transparent
    img.save(path, format="PNG")

    result = optimize_for_claude(path)

    assert result.media_type == "image/jpeg"
    with Image.open(io.BytesIO(result.data)) as out:
        assert out.mode == "RGB"
        # transparent pixels should have composited to white, not black
        assert out.getpixel((150, 150)) == (255, 255, 255)


# ── validation helpers ──────────────────────────────────────────────────


def test_validate_rejects_truncated_or_non_image_bytes():
    with pytest.raises(ImageValidationError):
        _validate_optimized(b"this is not an image, just some text padded out long enough")


def test_validate_rejects_too_small_byte_count():
    with pytest.raises(ImageValidationError):
        _validate_optimized(b"\xff\xd8\xff")


def test_validate_accepts_a_real_jpeg(tmp_path):
    path = tmp_path / "ok.jpg"
    data = _save_jpeg(path, (120, 90))
    width, height = _validate_optimized(data)
    assert (width, height) == (120, 90)


def test_looks_blank_true_for_flat_color(tmp_path):
    path = tmp_path / "flat.jpg"
    data = _save_jpeg(path, (60, 60), color=(15, 15, 15))
    assert _looks_blank(data) is True


def test_looks_blank_false_for_a_varied_image(tmp_path):
    path = tmp_path / "varied.jpg"
    data = _save_noisy_jpeg(path, (60, 60))
    assert _looks_blank(data) is False


# ── hard per-image cap: falls back to a smaller/lower-quality pass ──────


def test_hard_cap_produces_a_smaller_conservative_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "claude_image_max_bytes", 1)  # always optimize
    monkeypatch.setattr(settings, "claude_image_max_dimension_px", 1200)
    path = tmp_path / "noisy.jpg"
    _save_noisy_jpeg(path, (500, 500), quality=100)

    # First see what the standard pass alone produces, then set the hard cap
    # strictly below it so the conservative pass is forced to take over.
    monkeypatch.setattr(settings, "claude_image_hard_max_bytes", 10 ** 9)
    standard = optimize_for_claude(path)
    monkeypatch.setattr(settings, "claude_image_hard_max_bytes", standard.final_bytes // 2)

    tightened = optimize_for_claude(path)

    assert tightened.was_optimized is True
    assert tightened.final_bytes < standard.final_bytes
    with Image.open(io.BytesIO(tightened.data)) as out:
        assert out.format == "JPEG"


def test_unreachable_hard_cap_still_returns_the_best_valid_copy(tmp_path, monkeypatch):
    """Even when the hard cap is impossible to hit (an absurdly low value —
    simulating an extremely detailed photo that just won't compress that
    far), optimize_for_claude must still return the smallest *valid* copy it
    made rather than fail the photo outright."""
    monkeypatch.setattr(settings, "claude_image_max_bytes", 1)
    monkeypatch.setattr(settings, "claude_image_hard_max_bytes", 10)
    path = tmp_path / "noisy.jpg"
    _save_noisy_jpeg(path, (400, 400))

    result = optimize_for_claude(path)

    assert result.was_optimized is True
    with Image.open(io.BytesIO(result.data)) as out:
        assert out.format == "JPEG"


# ── multi-photo tag: combined-payload budget ─────────────────────────────


def test_multi_photo_tag_never_combined_into_one_image(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "claude_image_max_dimension_px", 200)  # force optimization
    paths = []
    for i in range(4):
        p = tmp_path / f"photo{i}.jpg"
        _save_jpeg(p, (800, 600), color=(10 * i, 20 * i, 30 * i))
        paths.append(p)

    results = prepare_images_for_claude(paths)

    assert len(results) == 4
    for r in results:
        with Image.open(io.BytesIO(r.data)) as out:
            assert out.size[0] <= 200 and out.size[1] <= 200


def test_combined_payload_over_budget_tightens_the_largest_photos(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "claude_image_max_bytes", 1)  # always optimize each photo
    monkeypatch.setattr(settings, "claude_image_max_dimension_px", 3000)
    paths = []
    for i in range(4):
        p = tmp_path / f"photo{i}.jpg"
        _save_noisy_jpeg(p, (450, 450), quality=95)
        paths.append(p)

    baseline_total = sum(optimize_for_claude(p).final_bytes for p in paths)
    # Budget deliberately below what per-photo optimization alone achieves,
    # so prepare_images_for_claude must tighten further rather than send an
    # oversized combined request.
    monkeypatch.setattr(settings, "claude_request_max_bytes", baseline_total // 2)

    results = prepare_images_for_claude(paths)

    assert len(results) == 4  # still one entry per photo — never merged/dropped
    for r in results:
        with Image.open(io.BytesIO(r.data)) as out:
            assert out.format == "JPEG"
    assert sum(r.final_bytes for r in results) < baseline_total


def test_prepare_images_never_modifies_any_original(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "claude_image_max_dimension_px", 100)
    paths, originals = [], []
    for i in range(3):
        p = tmp_path / f"orig{i}.jpg"
        originals.append(_save_jpeg(p, (900, 700), color=(5 * i, 5 * i, 5 * i)))
        paths.append(p)

    prepare_images_for_claude(paths)

    for p, original in zip(paths, originals):
        assert p.read_bytes() == original
