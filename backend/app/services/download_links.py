"""Signed, long-lived links for the AI OUTPUT EXCEL / INPUT PHOTO hyperlinks
embedded in an exported Template workbook.

Every other download in this app is guarded by a bearer JWT the SPA attaches
to each request (see app.core.deps.CurrentUser) — but a hyperlink click in
Excel is a bare GET issued by the OS's default browser, which never carries
that token. These links carry their own signed capability instead, scoped to
one tag number (never a raw file path), so a link can't be edited to reach
another tag's files and doesn't depend on this server's local filesystem
layout being visible to whatever machine later opens the workbook.
"""
from __future__ import annotations

from datetime import timedelta

from app.core.config import settings
from app.core.security import create_link_token, decode_link_token

_KIND_AI_EXCEL = "tag_ai_download"
_KIND_PHOTO = "tag_photo_view"


def _expiry() -> timedelta:
    return timedelta(days=settings.download_link_expire_days)


def ai_excel_download_url(tag_number: str) -> str:
    token = create_link_token({"kind": _KIND_AI_EXCEL, "tag_number": tag_number}, _expiry())
    base = settings.public_base_url.rstrip("/")
    return f"{base}/api/v1/tags/download/ai-link?token={token}"


def photo_view_url(tag_number: str) -> str:
    token = create_link_token({"kind": _KIND_PHOTO, "tag_number": tag_number}, _expiry())
    base = settings.public_base_url.rstrip("/")
    return f"{base}/api/v1/batches/images/photo-link?token={token}"


def verify_ai_excel_token(token: str) -> str | None:
    claims = decode_link_token(token)
    if not claims or claims.get("kind") != _KIND_AI_EXCEL:
        return None
    tag_number = claims.get("tag_number")
    return tag_number if isinstance(tag_number, str) and tag_number else None


def verify_photo_token(token: str) -> str | None:
    claims = decode_link_token(token)
    if not claims or claims.get("kind") != _KIND_PHOTO:
        return None
    tag_number = claims.get("tag_number")
    return tag_number if isinstance(tag_number, str) and tag_number else None
