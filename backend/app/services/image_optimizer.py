"""Adaptive, in-memory image optimization for Claude vision calls only.

The photo on disk (STORAGE_DIR/uploads/...) is never opened in write mode and
never modified — every function here only ever *reads* the original file and
returns bytes held in memory. Those bytes are handed straight to the Anthropic
SDK by the caller and then dropped (normal Python garbage collection) once the
request is built; nothing here writes a temp file to disk, so there is
nothing to clean up afterwards.

Pipeline for one tag's photos (see `prepare_images_for_claude`, the entry
point `claude_extractor.py` actually calls):

    for each photo:  optimize_for_claude()
        inspect size/dimensions
        skip re-encoding if already small enough (no quality loss)
        otherwise: resize/recompress, THEN validate the result
        if validation fails, retry with a more conservative pass
        if that fails too, fall back to the original bytes
    THEN: if the whole tag's combined payload is still too big,
          tighten the largest photo(s) a second time (never combined
          into one image, never dropped)

A photo that is already small enough and low-resolution enough is returned
completely unmodified — not even re-encoded — so a normal-sized nameplate
photo pays zero extra cost. Only a photo over a threshold gets
resized/recompressed, and only for the one Claude request that needs it.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from app.core.config import settings

logger = logging.getLogger(__name__)

#: Media types Anthropic's vision endpoint accepts.
ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

_EXT_MEDIA_TYPE = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".jfif": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
}

#: Below this, an "optimized" file is almost certainly truncated/corrupt
#: rather than a real (if extremely simple) photo.
_MIN_VALID_BYTES = 200
_MIN_VALID_DIMENSION = 10

#: A second, smaller/lower-quality pass tried only when the standard pass
#: either fails validation or is still over CLAUDE_IMAGE_HARD_MAX_BYTES.
_FALLBACK_DIMENSION_FLOOR = 1400
_FALLBACK_QUALITY_DROP = 20
_FALLBACK_MIN_QUALITY = 60

#: The extra, more aggressive pass used only when a whole tag's combined
#: payload is still over budget after every photo's own normal pass.
_TIGHTEN_DIMENSION_FLOOR = 1000
_TIGHTEN_QUALITY_DROP = 30
_TIGHTEN_MIN_QUALITY = 55


class ImageValidationError(ValueError):
    """An optimized image isn't safe to send to Claude. Callers fall back to
    a different optimization strategy rather than letting this propagate."""


@dataclass
class OptimizedImage:
    data: bytes
    media_type: str
    was_optimized: bool
    original_bytes: int
    final_bytes: int


def _guess_media_type(path: Path) -> str:
    return _EXT_MEDIA_TYPE.get(path.suffix.lower(), "image/jpeg")


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    """Composite a transparent/paletted image onto white before JPEG-encoding
    it — JPEG has no alpha channel, and dropping alpha without compositing
    turns transparent pixels black instead of white."""
    if img.mode in ("RGB", "L"):
        return img
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return img.convert("RGB")


def _encode_jpeg(base: Image.Image, max_dimension: int, quality: int) -> bytes:
    """Resize (preserving aspect ratio, never upscaling) and JPEG-encode
    `base` — a copy, since PIL's `.thumbnail()` mutates in place and this may
    be called more than once against the same source image."""
    img = base.copy()
    if max(img.size) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
    img = _flatten_to_rgb(img)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def _validate_optimized(data: bytes) -> tuple[int, int]:
    """Decode-check optimized bytes before they're allowed to reach Claude.

    Confirms the bytes are non-trivial, actually decode as an image (not
    truncated/corrupt), and have sane (non-zero-ish) dimensions. Raises
    `ImageValidationError` — never lets a broken result through silently.
    """
    if len(data) < _MIN_VALID_BYTES:
        raise ImageValidationError(f"optimized image is only {len(data)} bytes")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        # verify() invalidates the Image for further use — reopen to read size.
        with Image.open(io.BytesIO(data)) as probe:
            width, height = probe.size
    except Exception as exc:
        raise ImageValidationError(f"optimized image failed to decode: {exc}") from exc
    if width < _MIN_VALID_DIMENSION or height < _MIN_VALID_DIMENSION:
        raise ImageValidationError(f"optimized image has degenerate dimensions {width}x{height}")
    return width, height


def _looks_blank(data: bytes) -> bool:
    """Best-effort, log-only heuristic for 'this optimized copy is a single
    flat color' (e.g. a resize/compression bug rendered a blank frame).

    Deliberately not a hard validation failure: a genuinely low-contrast
    nameplate photo (worn/faded plate, plain background) can legitimately
    have very low variance, and rejecting it outright would do more harm
    than the rare true blank frame this is meant to catch. Callers should
    only log this, not act on it.
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            sample = img.convert("L").resize((32, 32))
            low, high = sample.getextrema()
            return low == high
    except Exception:
        return False


def optimize_for_claude(path: Path) -> OptimizedImage:
    """Return the bytes to send to Claude for one photo.

    Already-small-enough photos are returned completely unmodified (after a
    decode/validation sanity check). A too-large or too-high-resolution
    photo gets a resized/recompressed in-memory copy — validated before
    being returned; if that fails, a second, more conservative pass is
    tried; if that fails too, this falls back to the original bytes so
    Claude's own API can surface a clear error rather than us guessing
    further. Never writes to `path`.

    Synchronous (Pillow has no async API) — callers on the event loop should
    run this via `asyncio.to_thread`.
    """
    original_bytes = path.stat().st_size
    media_type = _guess_media_type(path)

    try:
        with Image.open(path) as img:
            width, height = img.size
            needs_resize = max(width, height) > settings.claude_image_max_dimension_px
            needs_recompress = original_bytes > settings.claude_image_max_bytes
            needs_format_fix = media_type not in ALLOWED_MEDIA_TYPES

            if not (needs_resize or needs_recompress or needs_format_fix):
                data = path.read_bytes()
                try:
                    _validate_optimized(data)
                    return OptimizedImage(data, media_type, False, original_bytes, len(data))
                except ImageValidationError as exc:
                    logger.warning(
                        "Original image %s failed validation (%s) — re-encoding "
                        "instead of sending it as-is", path, exc,
                    )
                    # Fall through to the resize/recompress passes below,
                    # which may well fix a bad encode (e.g. odd color profile).

            base = ImageOps.exif_transpose(img)

        # Two passes: the configured "standard" settings, then a smaller/
        # lower-quality "conservative" one if the first is invalid or still
        # over the per-image hard cap. Keeps the best *valid* result seen so
        # a validation failure on pass 2 doesn't throw away a valid pass 1.
        passes = (
            (settings.claude_image_max_dimension_px, settings.claude_image_jpeg_quality),
            (
                min(settings.claude_image_max_dimension_px, _FALLBACK_DIMENSION_FLOOR),
                max(_FALLBACK_MIN_QUALITY, settings.claude_image_jpeg_quality - _FALLBACK_QUALITY_DROP),
            ),
        )
        best: OptimizedImage | None = None
        for dimension, quality in passes:
            data = _encode_jpeg(base, dimension, quality)
            try:
                _validate_optimized(data)
            except ImageValidationError as exc:
                logger.warning(
                    "Optimized copy of %s (dimension<=%d, quality=%d) failed "
                    "validation (%s); trying a more conservative pass",
                    path, dimension, quality, exc,
                )
                continue
            if _looks_blank(data):
                logger.warning(
                    "Optimized copy of %s (dimension<=%d, quality=%d) looks "
                    "like a single flat color — sending it anyway (may be a "
                    "genuinely plain plate; not treated as invalid)",
                    path, dimension, quality,
                )
            result = OptimizedImage(data, "image/jpeg", True, original_bytes, len(data))
            if len(data) <= settings.claude_image_hard_max_bytes:
                return result
            best = result  # valid but still over the soft cap; keep as a fallback

        if best is not None:
            logger.info(
                "Optimized copy of %s is %d bytes, over the %d byte per-image "
                "cap even after the conservative pass — sending the smallest "
                "valid copy produced",
                path, best.final_bytes, settings.claude_image_hard_max_bytes,
            )
            return best

        logger.error(
            "Could not produce a valid optimized copy of %s after %d attempts; "
            "sending the original bytes so Claude's API can report a clear error",
            path, len(passes),
        )
        data = path.read_bytes()
        fallback_type = media_type if media_type in ALLOWED_MEDIA_TYPES else "image/jpeg"
        return OptimizedImage(data, fallback_type, False, original_bytes, len(data))
    except Exception:
        # A corrupt/unreadable file must not fail the whole tag's extraction
        # here — fall back to the raw original bytes, same as before this
        # optimizer existed, and let Claude's own API surface a clear
        # "invalid image" error if it truly can't be decoded.
        logger.warning("Could not optimize image %s for Claude; sending original bytes", path, exc_info=True)
        fallback_type = media_type if media_type in ALLOWED_MEDIA_TYPES else "image/jpeg"
        data = path.read_bytes()
        return OptimizedImage(data, fallback_type, False, original_bytes, len(data))


def _recompress_aggressively(path: Path, current: OptimizedImage) -> OptimizedImage:
    """One more, smaller/lower-quality pass on a single photo — used only by
    `prepare_images_for_claude` when a tag's *combined* payload is still
    over budget after every photo's own normal optimization pass. Falls back
    to `current` (already a valid, individually-optimized copy) if this
    extra pass can't produce a valid image, so a tightening attempt can
    never make things worse.
    """
    try:
        with Image.open(path) as img:
            base = ImageOps.exif_transpose(img)
        dimension = max(_TIGHTEN_DIMENSION_FLOOR, settings.claude_image_max_dimension_px // 2)
        quality = max(_TIGHTEN_MIN_QUALITY, settings.claude_image_jpeg_quality - _TIGHTEN_QUALITY_DROP)
        data = _encode_jpeg(base, dimension, quality)
        _validate_optimized(data)
        return OptimizedImage(data, "image/jpeg", True, current.original_bytes, len(data))
    except Exception:
        logger.warning(
            "Could not tighten %s further for the combined-payload budget; "
            "keeping its earlier optimized copy (%d bytes)",
            path, current.final_bytes, exc_info=True,
        )
        return current


def prepare_images_for_claude(paths: list[Path]) -> list[OptimizedImage]:
    """Optimize every one of a tag's photos individually (never combined
    into one image), then — only if their combined size would still make an
    oversized Claude request — tighten the largest ones further.

    This is the actual entry point `claude_extractor.py` calls: compression
    always happens here, fully, BEFORE any photo is base64-encoded or handed
    to the Anthropic client. Returns the bytes to send, one per input path,
    in the same order. Never touches any file in `paths` beyond reading it.
    """
    images = [optimize_for_claude(p) for p in paths]
    total = sum(im.final_bytes for im in images)
    if total <= settings.claude_request_max_bytes:
        return images

    logger.info(
        "Combined optimized payload for %d photo(s) is %d bytes, over the "
        "%d byte request budget — tightening the largest photo(s) further",
        len(paths), total, settings.claude_request_max_bytes,
    )
    order = sorted(range(len(images)), key=lambda i: images[i].final_bytes, reverse=True)
    for idx in order:
        if total <= settings.claude_request_max_bytes:
            break
        tightened = _recompress_aggressively(paths[idx], images[idx])
        total += tightened.final_bytes - images[idx].final_bytes
        images[idx] = tightened

    if total > settings.claude_request_max_bytes:
        logger.warning(
            "Combined optimized payload for %d photo(s) is still %d bytes "
            "after tightening (budget %d) — sending it to Claude anyway",
            len(paths), total, settings.claude_request_max_bytes,
        )
    return images
