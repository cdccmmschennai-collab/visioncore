"""Tests for the equipment-code segment extraction used to resolve a
tag-only upload's description (see app/services/equipment_codes.py).
"""
import pytest

from app.services.equipment_codes import extract_code


@pytest.mark.parametrize(
    "tag_number, code",
    [
        ("22-4203-BV-0119", "BV"),
        ("22-4202-TW-0019", "TW"),
        ("12-4020-BV-0074", "BV"),
        ("21-JDD-01", "JDD"),
        ("12-LJBF-1067", "LJBF"),
        ("PM-8981B", "PM"),   # "8981B" has digits, so isn't itself a code
    ],
)
def test_extract_code_finds_the_alphabetic_segment(tag_number, code):
    assert extract_code(tag_number) == code


@pytest.mark.parametrize(
    "tag_number",
    [
        "12-4020-0074",     # no alphabetic segment at all
        "P-1001",           # single-letter segment is too short to count
        "22-4203-ABCDEFG-0119",  # too long to plausibly be a code
        "",
    ],
)
def test_extract_code_returns_none_when_no_code_segment(tag_number):
    assert extract_code(tag_number) is None
