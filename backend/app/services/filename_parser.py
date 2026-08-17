"""Split an upload filename into a tag number and an equipment description.

Filenames follow `<TAG-SEGMENTS>-<DESCRIPTION>.<ext>`, e.g.

    12-4020-BV-0074-BALL VALVE.jpg  ->  ("12-4020-BV-0074", "BALL VALVE")

The awkward part is that the boundary is not at a fixed segment index — real
tags run from three segments (`21-JDD-01`) to four (`12-4020-BV-0074`) — so the
split is found by recognising what a *description* looks like rather than by
counting.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass

#: Trailing "(1)", "-copy", " - Copy" that browsers and file managers append.
_COPY_SUFFIX = re.compile(r"\s*(?:\(\d+\)|[-_ ]cop(?:y|ie)\d*)\s*$", re.IGNORECASE)
_MULTISPACE = re.compile(r"\s+")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".jfif"}


@dataclass(frozen=True)
class ParsedName:
    tag_number: str
    description: str
    ok: bool
    reason: str = ""


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    # Underscores routinely stand in for spaces after a download or a zip
    # round-trip; the reference file arrived as BALL_VALVE.jpg.
    text = text.replace("_", " ")
    return _MULTISPACE.sub(" ", text).strip()


def _looks_like_description(segment: str) -> bool:
    """A description segment reads as words, not as a tag code."""
    s = segment.strip()
    if not s:
        return False
    if " " in s or "," in s or "/" in s:
        return True
    # A lone alphabetic word of 4+ characters ("PUMP", "VALVE") is a
    # description; shorter ones ("BV", "ECP", "TIT") are tag codes.
    return s.isalpha() and len(s) >= 4


def _split_tag_description(stem: str, *, example: str) -> ParsedName:
    """Shared `<TAG>-<DESCRIPTION>` split used for both filenames and folder names."""
    stem = _COPY_SUFFIX.sub("", _clean(stem))
    if not stem:
        return ParsedName("", "", False, "Empty name")

    segments = [s.strip() for s in stem.split("-")]
    if len(segments) < 2 or any(not s for s in segments):
        return ParsedName("", "", False, f"Expected <TAG>-<DESCRIPTION>, for example {example}")

    split_at: int | None = None

    # Preferred signal: the first segment that reads as words. Start at index 1
    # so a tag can never be reduced to nothing.
    for i in range(1, len(segments)):
        if _looks_like_description(segments[i]):
            split_at = i
            break

    # Fallback for single-word descriptions with no space or comma: take the
    # last segment if it is alphabetic. Chosen over the *first* alphabetic
    # segment so a 4-letter code mid-tag does not steal the split.
    if split_at is None and len(segments) >= 2 and segments[-1].isalpha():
        split_at = len(segments) - 1

    if split_at is None:
        return ParsedName(
            "", "", False,
            "Could not tell where the tag number ends and the description begins",
        )

    tag_number = "-".join(segments[:split_at]).upper()
    description = "-".join(segments[split_at:]).upper().strip()

    if not tag_number or not description:
        return ParsedName("", "", False, "Tag number or description resolved to empty")

    return ParsedName(tag_number, description, True)


def parse_filename(filename: str) -> ParsedName:
    stem, ext = os.path.splitext(os.path.basename(filename))
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        return ParsedName("", "", False, f"Unsupported file type '{ext or "none"}'")

    return _split_tag_description(stem, example="12-4020-BV-0074-BALL VALVE.jpg")


def parse_folder_name(folder_name: str) -> ParsedName:
    """Same `<TAG>-<DESCRIPTION>` convention, applied to a subfolder's name.

    Used when a user uploads a folder tree instead of loose files: each leaf
    subfolder is treated as one tag, and its name is parsed the same way a
    filename would be.
    """
    name = os.path.basename(folder_name.rstrip("/\\"))
    return _split_tag_description(name, example="12-4020-BV-0074-BALL VALVE")


def excel_basename(tag_number: str, description: str) -> str:
    """`12-4020-BV-0074-BALL VALVE` — the stem both workbook names build on."""
    return f"{tag_number}-{description}"


def safe_filename(name: str) -> str:
    """Strip characters that break Content-Disposition or Windows paths.

    Commas are legitimate in these descriptions (`VALVE,GATE`) and are kept.
    """
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return cleaned.strip(" .") or "download"
