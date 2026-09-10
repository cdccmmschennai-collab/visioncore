"""Tests for Template workbook display-only formatting:
- Additional Information: each "LABEL: value" pair on its own line within
  the same cell.
- Size / Dimension: the inch mark (") spelled out as "inch".
Both are Template workbook only — the AI Output workbook, the database and
the UI all keep the original raw string untouched.
"""
from io import BytesIO

from openpyxl import load_workbook

from app.services.excel_template import (
    _format_additional_information,
    _format_size_dimension,
    build_template_workbook,
)
from app.services.fields import empty_payload, value_of


def test_format_additional_information_breaks_each_pair_onto_its_own_line():
    raw = (
        "TYPE/RATING: 1500# RTJ X 6000# NPT F, BODY MOC: ASTM A350 GR LF2 CL.1, "
        "TRIM MOC: ASTM A182 GR F316/F316L"
    )
    assert _format_additional_information(raw) == (
        "TYPE/RATING: 1500# RTJ X 6000# NPT F\n"
        "BODY MOC: ASTM A350 GR LF2 CL.1\n"
        "TRIM MOC: ASTM A182 GR F316/F316L"
    )


def test_format_additional_information_leaves_a_single_pair_unchanged():
    assert _format_additional_information("TYPE/RATING: 1500# RTJ") == "TYPE/RATING: 1500# RTJ"


def test_format_additional_information_ignores_a_comma_that_is_not_a_pair_boundary():
    """A comma inside a value's own text (not immediately followed by a new
    "LABEL:") must not be split — only real pair boundaries are."""
    raw = "STANDARD: ASME B16.5, API 600 combined rating"
    assert _format_additional_information(raw) == raw


def test_build_template_workbook_writes_line_breaks_and_keeps_wrap_text():
    payload = empty_payload("12-TAG-0001", "BALL VALVE")
    payload["fields"]["additional_information"] = {
        "value": (
            "TYPE/RATING: 1500# RTJ X 6000# NPT F, BODY MOC: ASTM A350 GR LF2 CL.1, "
            "TRIM MOC: ASTM A182 GR F316/F316L"
        ),
        "quality": "Confirmed",
    }

    content = build_template_workbook([{"payload": payload, "ai_payload": {}}])
    wb = load_workbook(BytesIO(content))
    ws = wb.active

    header_row = [c.value for c in ws[1]]
    col = header_row.index("ADDITIONAL INFORMATION") + 1
    cell = ws.cell(row=2, column=col)

    assert cell.value == (
        "TYPE/RATING: 1500# RTJ X 6000# NPT F\n"
        "BODY MOC: ASTM A350 GR LF2 CL.1\n"
        "TRIM MOC: ASTM A182 GR F316/F316L"
    )
    assert cell.alignment.wrap_text is True


def test_format_size_dimension_spells_out_the_inch_mark():
    assert _format_size_dimension('6"') == "6 inch"
    assert _format_size_dimension('12"') == "12 inch"
    assert _format_size_dimension('24" x 6"') == "24 inch x 6 inch"


def test_format_size_dimension_leaves_a_value_without_the_mark_unchanged():
    assert _format_size_dimension("3/4 150RF") == "3/4 150RF"


def test_build_template_workbook_spells_out_inch_mark_in_size_column_only():
    payload = empty_payload("12-TAG-0001", "BALL VALVE")
    payload["fields"]["size_dimension"] = {"value": '24" x 6"', "quality": "Confirmed"}
    ai_payload = {"fields": {"size_dimension": {"value": '24" x 6"', "quality": "Confirmed"}}}

    content = build_template_workbook([{"payload": payload, "ai_payload": ai_payload}])
    wb = load_workbook(BytesIO(content))
    ws = wb.active

    header_row = [c.value for c in ws[1]]
    col = header_row.index("SIZE/DIMENSION") + 1
    assert ws.cell(row=2, column=col).value == "24 inch x 6 inch"

    # The underlying payload the database/UI/AI Output workbook see is untouched.
    assert value_of(payload, "size_dimension") == '24" x 6"'
