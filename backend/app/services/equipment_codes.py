"""Resolve a tag-only upload's description from the equipment code embedded
in its tag number (e.g. the "BV" in "22-4203-BV-0119"), using whatever codes
are already known — the small hand-seeded list in filename_parser plus every
code already seen, with a description, on a previously extracted tag —
rather than a fixed list someone has to keep maintaining by hand.

No separate mapping table to keep in sync: `asset_tags` (the canonical,
de-duplicated tag record) already carries every tag number and its accepted
description, so the very first "...-BV-...-BALL VALVE.jpg" ever extracted is
enough to make every later tag-only "...-BV-..." upload resolve to "BALL
VALVE" automatically.
"""
from __future__ import annotations

import re

from sqlalchemy import func, select

from app.models import AssetTag
from app.services.filename_parser import EQUIPMENT_CODE_DESCRIPTIONS

#: A bare 2-6 letter equipment-code segment, e.g. "BV", "GLV", "LJBF".
_CODE_SEGMENT = re.compile(r"^[A-Za-z]{2,6}$")


def extract_code(tag_number: str) -> str | None:
    """The equipment-code segment embedded in a tag number, if any.

    Takes the *last* purely-alphabetic 2-6 letter segment ("BV" in
    "22-4203-BV-0119") — mirroring where filename_parser's own hand-seeded
    lookup looks — never a numeric or mixed alphanumeric segment (a revision
    fragment like "8981B" is left alone).
    """
    code = None
    for segment in tag_number.split("-"):
        if _CODE_SEGMENT.fullmatch(segment.strip()):
            code = segment.strip().upper()
    return code


async def resolve_description(db, tag_number: str) -> str | None:
    """The equipment/item name for a tag-only upload, or None to never guess.

    Checks the small hand-seeded list first, then falls back to whichever
    description that same code most often resolved to on tags already
    extracted (ties broken by most recent) — so the system keeps learning
    from real uploads without any separate mapping to maintain.
    """
    code = extract_code(tag_number)
    if code is None:
        return None

    seeded = EQUIPMENT_CODE_DESCRIPTIONS.get(code)
    if seeded:
        return seeded

    row = (
        await db.execute(
            select(AssetTag.description)
            .where(
                AssetTag.tag_number.ilike(f"%-{code}-%")
                | AssetTag.tag_number.ilike(f"%-{code}")
            )
            .group_by(AssetTag.description)
            .order_by(func.count().desc(), func.max(AssetTag.created_at).desc())
            .limit(1)
        )
    ).first()
    return row[0] if row else None
