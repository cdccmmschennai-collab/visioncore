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
#: A space, comma or underscore directly after a digit is acting as the
#: boundary between the tag number's numeric tail and the description (e.g.
#: "1067 FIRE...", "1001,TEMPERATURE ELEMENT" or "1001_ELECTRONIC..."), so
#: treat it as a segment break there, same as a hyphen. Elsewhere a comma is
#: literal punctuation inside the description ("VALVE,GATE") and an
#: underscore is a plain space substitute ("BALL_VALVE") — both left alone;
#: a plain space elsewhere is already description-internal word-spacing
#: ("BALL VALVE") and needs no special handling.
_TAG_BOUNDARY_SEP = re.compile(r"(?<=\d)[,_ ]\s*")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".jfif"}


@dataclass(frozen=True)
class ParsedName:
    tag_number: str
    description: str
    ok: bool
    reason: str = ""


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _TAG_BOUNDARY_SEP.sub("-", text)
    # Underscores routinely stand in for spaces after a download or a zip
    # round-trip; the reference file arrived as BALL_VALVE.jpg.
    text = text.replace("_", " ")
    return _MULTISPACE.sub(" ", text).strip()


def _looks_like_description(segment: str) -> bool:
    """A description segment reads as words, not as a tag code.

    Only a segment containing a space, comma or slash counts here — a bare
    alphabetic segment ("lJBF", "TIT") is still a plausible tag code no
    matter how long it is, so it's only ever treated as a description when
    it's the *last* segment (see the fallback in `_split_tag_description`).
    Otherwise a 4+ letter tag code sitting mid-sequence would be misread as
    the start of the description.
    """
    s = segment.strip()
    if not s:
        return False
    return " " in s or "," in s or "/" in s


#: A bare numeric tag fragment with an optional one/two-letter revision
#: suffix ("8981B", "1234A", "0074") — still part of the tag, not an English
#: word, unlike a description word such as "MOTOR".
_TAG_FRAGMENT = re.compile(r"\d+[A-Za-z]{0,2}$")


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

    # The segment that triggered the split may itself glue a trailing tag
    # fragment onto the real description with a bare space, e.g. "8981B
    # MOTOR,PUMP" inside "PM-8981B MOTOR,PUMP" — peel that leading fragment
    # back onto the tag so "PM-8981B" doesn't get truncated to "PM".
    lead_segment = segments[split_at]
    head, _, rest = lead_segment.partition(" ")
    peel = bool(rest) and _TAG_FRAGMENT.fullmatch(head) is not None
    if peel:
        segments[split_at] = rest

    tag_segments = segments[:split_at] + ([head] if peel else [])
    tag_number = "-".join(tag_segments).upper()
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
