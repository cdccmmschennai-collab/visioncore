"""Tests for the tag_number/description reconciliation criteria shared
between claude_extractor's two identity fields: Confirmed when the final
value stands unchallenged, Verify when there's any doubt about it.
"""
from app.services.fields import (
    UNRESOLVED_DESCRIPTION,
    QUALITY_CONFIRMED,
    QUALITY_VERIFY,
    reconcile_description,
    reconcile_tag_number,
)


def _raw(field: str, value: str, quality: str = "Confirmed") -> dict:
    return {"fields": {field: {"value": value, "quality": quality}}}


def test_reconcile_tag_number_confirmed_when_plate_has_no_reading():
    tag_number, quality = reconcile_tag_number({"fields": {}}, "12-TAG-0001")
    assert tag_number == "12-TAG-0001"
    assert quality == QUALITY_CONFIRMED


def test_reconcile_tag_number_confirmed_when_plate_agrees():
    raw = _raw("tag_number", "12-tag-0001")   # case-insensitive match
    tag_number, quality = reconcile_tag_number(raw, "12-TAG-0001")
    assert tag_number == "12-TAG-0001"
    assert quality == QUALITY_CONFIRMED


def test_reconcile_tag_number_verify_on_mismatch():
    raw = _raw("tag_number", "12-TAG-9999")
    tag_number, quality = reconcile_tag_number(raw, "12-TAG-0001")
    assert tag_number == "12-TAG-9999"
    assert quality == QUALITY_VERIFY


def test_reconcile_description_confirmed_when_upload_supplied_it():
    description, quality = reconcile_description({"fields": {}}, "BALL VALVE")
    assert description == "BALL VALVE"
    assert quality == QUALITY_CONFIRMED


def test_reconcile_description_confirmed_ignores_ai_disagreement():
    """Unlike tag_number, an explicit description is never second-guessed —
    it's the intended equipment name, not an independently checkable fact."""
    raw = _raw("description", "GATE VALVE")
    description, quality = reconcile_description(raw, "BALL VALVE")
    assert description == "BALL VALVE"
    assert quality == QUALITY_CONFIRMED


def test_reconcile_description_verify_when_ai_supplies_it():
    raw = _raw("description", "BALL VALVE", quality="Verify")
    description, quality = reconcile_description(raw, "")
    assert description == "BALL VALVE"
    assert quality == QUALITY_VERIFY


def test_reconcile_description_unresolved_when_neither_has_it():
    description, quality = reconcile_description({"fields": {}}, "")
    assert description == UNRESOLVED_DESCRIPTION
    assert quality == QUALITY_VERIFY
