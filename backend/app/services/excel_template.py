"""Writer for the **Template Output** workbook.

A single `Asset Tag` sheet with 18 columns in fixed order (S.NO → INPUT
PHOTO), yellow Arial-10 header, frozen header row, and an autofilter across
the used range. The last two columns, AI OUTPUT EXCEL and INPUT PHOTO, are
clickable hyperlinks — driven off `record["ai_excel_url"]` /
`record["input_photo_url"]`, signed links built from the tag's own
tag_number by `app.services.download_links`, never off the row's other data,
so one tag's links can never point at another tag's files. A signed link
resolves the actual file at click time over HTTP, so it opens correctly
wherever the exported workbook is later opened — unlike a local filesystem
path, which is only ever valid on the machine that generated the file. A tag
with nothing to link to gets "Not available" text instead of a dead link.

Two conventions were read off the reference row and are reproduced faithfully:

* **Amber fill (#FFC000)** on a value cell whose AI quality mark is `Verify` —
  in the reference, EQPT HAZARDOUS CLASSIFICATION carried this.
* **Blue font (#0070C0)** on a value a reviewer supplied or corrected, where the
  AI had not read it cleanly — in the reference, MAKE (`JC VALVES`) carried
  this, and the REMARKS cell explained that only a logo was visible.

Blank means blank: where the AI reported `Not present on nameplate`, the
Template cell is left empty, exactly as the reference does for MODEL, PART NO,
WEIGHT and COUNTRY.
"""
from __future__ import annotations

import re
from copy import copy
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.fields import (
    FIELDS,
    QUALITY_VERIFY,
    REMARKS_FIELD,
    is_blank,
    quality_of,
    value_of,
)
from app.services.filename_parser import tag_number_from_filename

HEADER_FILL = PatternFill("solid", fgColor="FFFFFF00")
AMBER_FILL = PatternFill("solid", fgColor="FFFFC000")
#: ASSET TAG NUMBER cell when the photo's tag number disagrees with TAG NUMBER.
ORANGE_FILL = PatternFill("solid", fgColor="FFFFA500")
#: TAG NUMBER cell of a Batch Process consolidated row whose tag was a
#: duplicate (already extracted by an earlier batch) — record["duplicate"].
LIGHT_GREEN_FILL = PatternFill("solid", fgColor="FFC6EFCE")
REVIEWER_FONT_COLOR = "FF0070C0"
HYPERLINK_FONT_COLOR = "FF0563C1"

ARIAL_HEADER = Font(name="Arial", size=10, bold=True, color="FF000000")
ARIAL_BODY = Font(name="Arial", size=10)
ARIAL_BODY_REVIEWED = Font(name="Arial", size=10, color=REVIEWER_FONT_COLOR)
ARIAL_HYPERLINK = Font(name="Arial", size=10, color=HYPERLINK_FONT_COLOR, underline="single")

AI_OUTPUT_HEADER = "AI OUTPUT EXCEL"
INPUT_PHOTO_HEADER = "INPUT PHOTO"
ASSET_TAG_NUMBER_HEADER = "ASSET TAG NUMBER"
ADDITIONAL_INFO_PARAGRAPH_HEADER = "ADDITIONAL INFORMATION-PARAGRAPH"

#: Template-only columns inserted directly after a field's own column.
_EXTRA_COLUMN_AFTER: dict[str, str] = {
    "tag_number": ASSET_TAG_NUMBER_HEADER,
    "additional_information": ADDITIONAL_INFO_PARAGRAPH_HEADER,
}

#: FIELDS minus Equipment Description, which the Template workbook doesn't
#: show. The description is still extracted, stored and shown everywhere
#: else (AI Output workbook, UI, database, file names) — display only.
TEMPLATE_FIELDS: tuple = tuple(f for f in FIELDS if f.key != "description")

ASSET_TAG_HEADERS: tuple[str, ...] = (
    "S.NO",
    *(h for f in TEMPLATE_FIELDS for h in (
        (f.template_header, _EXTRA_COLUMN_AFTER[f.key]) if f.key in _EXTRA_COLUMN_AFTER
        else (f.template_header,)
    )),
    REMARKS_FIELD.template_header,
    AI_OUTPUT_HEADER,
    INPUT_PHOTO_HEADER,
)

#: Widths lifted from the reference workbook, keyed by header text so they
#: survive any future column reordering in FIELDS.
COLUMN_WIDTHS: dict[str, float] = {
    "S.NO": 5.55, "TAG NUMBER": 17.11, ASSET_TAG_NUMBER_HEADER: 17.11, "EQUIPMENT DESCRIPTION": 41.33,
    "SIZE/DIMENSION": 19.0, "MAKE (ASSET)": 88.66, "MODEL": 44.33,
    "SERIAL NO": 37.33, "PART NO": 9.33, "WEIGHT": 8.44, "COUNTRY": 10.44,
    "YEAR OF MANUFACTURE YYYY": 29.33, "MONTH OF MANUFACTURE MM": 29.89,
    "EQPT HAZARDOUS CLASSIFICATION": 104.33, "ADDITIONAL INFORMATION": 255.66,
    ADDITIONAL_INFO_PARAGRAPH_HEADER: 255.66,
    "REMARKS": 132.89, AI_OUTPUT_HEADER: 18.0, INPUT_PHOTO_HEADER: 16.0,
}

WRAP_HEADERS = {
    "EQPT HAZARDOUS CLASSIFICATION", "ADDITIONAL INFORMATION",
    ADDITIONAL_INFO_PARAGRAPH_HEADER, "REMARKS",
}

#: additional_information is stored (and shown everywhere else — the AI
#: Output workbook, the UI, the database) as "LABEL: value" pairs joined by
#: ", " per the extraction prompt's own rule 6 (see claude_extractor.py). A
#: comma-space immediately followed by what reads as the *next* pair's own
#: "LABEL:" marks that boundary; only that comma-space is broken onto a new
#: line, so a comma that's just punctuation inside a value (not before a
#: label) is left alone.
_ADDITIONAL_INFO_PAIR_BREAK = re.compile(r",\s+(?=[A-Z0-9][A-Z0-9 /&\-]*:)")


def _format_additional_information(value: str) -> str:
    """Template workbook display only — one "LABEL: value" pair per Excel
    line break within the same cell, instead of one dense comma-joined line.
    The AI Output workbook, the database, and the app UI keep the original
    comma-joined string untouched.
    """
    return _ADDITIONAL_INFO_PAIR_BREAK.sub("\n", value)


def _format_additional_information_paragraph(value: str) -> str:
    """Template workbook display only — the same additional_information as
    one continuous paragraph: the stored comma-joined "LABEL: value" pairs
    with any line breaks or runs of whitespace collapsed to single spaces.
    """
    return " ".join(value.split())


def _format_size_dimension(value: str) -> str:
    """Template workbook display only — the inch mark (") spelled out as
    "inch" (`6"` -> "6 inch", `24" x 6"` -> "24 inch x 6 inch"), since a raw
    `"` can render oddly once exported. The AI Output workbook, the
    database, and the app UI keep the original `"` mark untouched.
    """
    return value.replace('"', " inch")


def _filename_tag_number(record: dict) -> str:
    """TAG NUMBER as parsed from the input photo's filename
    (`22-4203-BV-0105-BALL VALVE.jpg` -> `22-4203-BV-0105`). "" when the
    caller passed no filename or it doesn't parse.
    """
    return tag_number_from_filename(record.get("input_filename"))


def _asset_tag_number(ai_payload: dict) -> str:
    """ASSET TAG NUMBER — the tag number the AI read off the photo, never the
    filename's. Tags extracted before `photo_tag_number` was stored only
    reveal it when it disagreed with the filename (quality "Verify"); a
    "Confirmed" legacy value can't be told apart from a filename fallback,
    so it is left empty.
    """
    if "photo_tag_number" in ai_payload:
        return str(ai_payload.get("photo_tag_number") or "").strip()
    if ai_payload and quality_of(ai_payload, "tag_number") == QUALITY_VERIFY:
        value = value_of(ai_payload, "tag_number").strip()
        return "" if is_blank(value) else value
    return ""


def _write_asset_tags_header(ws: Worksheet) -> None:
    for col, header in enumerate(ASSET_TAG_HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = ARIAL_HEADER
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[cell.column_letter].width = COLUMN_WIDTHS.get(header, 18.0)
    ws.row_dimensions[1].height = 59.25
    ws.freeze_panes = "A2"


def _write_asset_tag_row(ws: Worksheet, row_idx: int, serial: int, record: dict) -> None:
    """`record` carries the final payload (plus the AI's original for diffing)."""
    payload = record["payload"]
    ai_payload = record.get("ai_payload") or {}

    sno = ws.cell(row=row_idx, column=1, value=f"{serial:04d}")
    sno.font = ARIAL_BODY
    sno.alignment = Alignment(horizontal="center", vertical="center")

    col = 2
    for field in TEMPLATE_FIELDS:
        value = value_of(payload, field.key)
        display = "" if is_blank(value) else value
        filename_tag = _filename_tag_number(record) if field.key == "tag_number" else ""
        if filename_tag:
            display = filename_tag
        if field.key == "additional_information" and display:
            display = _format_additional_information(display)
        elif field.key == "size_dimension" and display:
            display = _format_size_dimension(display)
        cell = ws.cell(row=row_idx, column=col, value=display or None)

        # Force text format so Excel never renders "02" as the number 2.
        if field.key in ("year_of_manufacture", "month_of_manufacture"):
            cell.number_format = "@"

        # Blue where a reviewer supplied or changed the value the AI returned.
        ai_value = value_of(ai_payload, field.key) if ai_payload else value
        reviewer_supplied = bool(display) and ai_value.strip() != value.strip()
        cell.font = ARIAL_BODY_REVIEWED if reviewer_supplied else ARIAL_BODY

        # Amber where the AI flagged the reading as needing field verification.
        # Never on TAG NUMBER — it's taken from the filename, not read.
        if display and field.key != "tag_number" and quality_of(payload, field.key) == QUALITY_VERIFY:
            cell.fill = AMBER_FILL
        if field.key == "tag_number" and record.get("duplicate"):
            cell.fill = LIGHT_GREEN_FILL

        if field.template_header in WRAP_HEADERS:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")
        col += 1

        if field.key == "tag_number":
            asset_tag = _asset_tag_number(ai_payload)
            asset_cell = ws.cell(row=row_idx, column=col, value=asset_tag or None)
            asset_cell.font = ARIAL_BODY
            asset_cell.alignment = Alignment(horizontal="left", vertical="center")
            if asset_tag and display and asset_tag.strip().upper() != display.strip().upper():
                asset_cell.fill = ORANGE_FILL
            col += 1
        elif field.key == "additional_information":
            # Same value, same font/fill as ADDITIONAL INFORMATION — only the
            # layout differs (one paragraph instead of one pair per line).
            paragraph = _format_additional_information_paragraph(value) if display else ""
            para_cell = ws.cell(row=row_idx, column=col, value=paragraph or None)
            para_cell.font = copy(cell.font)
            para_cell.fill = copy(cell.fill)
            para_cell.alignment = Alignment(vertical="top", wrap_text=True)
            col += 1

    remarks = ws.cell(row=row_idx, column=col, value=str(payload.get("remarks", "") or "") or None)
    remarks.font = ARIAL_BODY
    remarks.alignment = Alignment(vertical="top", wrap_text=True)
    col += 1

    _write_hyperlink_cell(ws, row_idx, col, record.get("ai_excel_url"), "View AI Output")
    col += 1
    _write_hyperlink_cell(ws, row_idx, col, record.get("input_photo_url"), "View Photo")

    ws.row_dimensions[row_idx].height = 25.5


def _write_hyperlink_cell(ws: Worksheet, row_idx: int, col: int, url: str | None,
                          link_text: str) -> None:
    """Write a clickable, friendly-text hyperlink, or 'Not available' for a tag
    with no corresponding file (e.g. a tag with no photo attached).

    `url` is a ready-made signed link from app.services.download_links, built
    from the tag's own tag_number — never a raw filesystem path, so it opens
    correctly regardless of which machine later opens this workbook.
    """
    cell = ws.cell(row=row_idx, column=col)
    if url:
        cell.value = link_text
        cell.hyperlink = url
        cell.font = ARIAL_HYPERLINK
    else:
        cell.value = "Not available"
        cell.font = ARIAL_BODY
    cell.alignment = Alignment(horizontal="center", vertical="center")


def build_template_workbook(records: list[dict]) -> bytes:
    """`records` is a list of dicts with keys: payload, ai_payload, and
    optionally input_filename (source of the TAG NUMBER column) and
    duplicate (True highlights that row's TAG NUMBER cell light green).
    One row per record — a single tag for a per-tag download, or every tag in a
    batch for the batch-level download.
    """
    wb = Workbook()

    ws = wb.active
    ws.title = "Asset Tag"
    _write_asset_tags_header(ws)
    for offset, record in enumerate(records):
        _write_asset_tag_row(ws, row_idx=2 + offset, serial=offset + 1, record=record)

    last_row = max(2, 1 + len(records))
    ws.auto_filter.ref = f"A1:{get_column_letter(len(ASSET_TAG_HEADERS))}{last_row}"

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
