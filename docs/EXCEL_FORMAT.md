# Workbook specification

Both writers were built by reading the supplied reference files cell-by-cell,
then diffing generated output back against them. The AI Output writer reproduces
its reference with **zero value and zero style differences**.

Source of truth for field order: `backend/app/services/fields.py`. Change the
`FIELDS` tuple there and both workbooks, the API contract, and the editable
table all follow.

---

## AI Output — `AI Output-<TAG>-<DESCRIPTION>.xlsx`

Written from `asset_tags.ai_payload` — Claude's untouched answer.

| | |
|---|---|
| Sheet name | `<TAG> - <DESCRIPTION>`, truncated to Excel's 31-char limit |
| Gridlines | Hidden |
| Column widths | A 27.0 · B 58.0 · C 16.0 · D 3.0 |

**Layout**

| Row | Content |
|---|---|
| 1 | `Full Technical Data Sheet — <DESCRIPTION>`, merged A1:C1, Calibri 14 bold `#1F3864`, height 26.1 |
| 2 | `Source: Nameplate photo(s) — <filenames>`, merged A2:C2, Calibri 10 italic `#595959`, height 27.95 |
| 3 | Blank |
| 4 | Header `Field` / `Extracted Value` / `Data Quality` — Calibri 11 bold white on `#14345A`, height 20.1 |
| 5–17 | One row per field, in `FIELDS` order |
| 18 | `Remarks` — no Data Quality cell, since a remark is a finding rather than a data field |
| 20 | `Data Quality Legend` |
| 21–22 | `Confirmed` and `Verify` swatches with their definitions, note merged across B:C |

**Cell styling**

- Field label (col A): Calibri 11 bold `#1F3864` on `#EEF2F7`
- Value (col B): Calibri 11, wrapped, top-aligned
- `Confirmed`: bold `#375623` on `#E2EFDA`
- `Verify`: bold `#7F4E00` on `#FFC000`
- Borders: thin `#B4C6E7` on all four sides of every table cell
- Row heights: 18.0, except Hazardous Area Classification 33.0 and Additional
  Information / Remarks 48.0

All colours are written as 8-digit ARGB (`FF` + RGB) because that is how the
reference file stores them; 6-digit values produce a byte-level mismatch.

---

## Template Output — `<TAG>-<DESCRIPTION>-Template.xlsx`

Written from `asset_tags.final_payload` — the reviewed values.

### Sheet `Asset Tags`

19 columns, fixed order:

```
S.NO · TAG NUMBER · EQUIPMENT DESCRIPTION · SIZE/DIMENSION · MAKE (ASSET) ·
MODEL · SERIAL NO · PART NO · WEIGHT · COUNTRY · YEAR OF MANUFACTURE YYYY ·
MONTH OF MANUFACTURE MM · EQPT HAZARDOUS CLASSIFICATION ·
ADDITIONAL INFORMATION · REMARKS 
```

- Header: Arial 10 bold on yellow `#FFFF00`, centred, wrapped, height 59.25
- Body: Arial 10, row height 25.5
- `freeze_panes = "A2"`, autofilter across `A1:S<last>`
- `S.NO` is zero-padded to four digits (`0001`) and centred
- Column widths copied from the reference, keyed by header text

**Three conventions carried over from the reference row**

1. **Blank means blank.** Where the AI reported `Not present on nameplate`, the
   Template cell is left empty — matching the reference, which leaves MODEL,
   PART NO, WEIGHT and COUNTRY blank while the AI sheet spells out the finding.
2. **Amber `#FFC000` fill** on any populated value whose quality mark is
   `Verify`. In the reference this was EQPT HAZARDOUS CLASSIFICATION.
3. **Blue `#0070C0` font** where a reviewer supplied or corrected a value that
   differs from `ai_payload`. In the reference this was MAKE = `JC VALVES`,
   with the REMARKS cell noting that only a brand logo was visible.

Convention 3 is why `ai_payload` is never overwritten: the comparison between
the two payloads is what drives the colour.

**Path columns.** `INPUT PHOTOS` and `OUTPUT WITH IMAGES` hold network paths in
the reference. Set `TEMPLATE_INPUT_PATH_PREFIX` and
`TEMPLATE_OUTPUT_PATH_PREFIX` in `.env` to match your share; leave them blank to
write bare filenames instead.

### Sheet `SUMMARY`

The QC scorecard, same 15 headers and same six category rows as the reference
(`AS IS DATA`, `DATA MISMATCH / ACTUAL DATA`, `MISSING DATA`, `EXTRA DATA NOT IN
PHOTO`, `AVAILABLE IN OUTPUT FILE NOT IN OUTPUT TEMPLATE`, `VERIFY(MARKED BY
AI)`), plus `OVERALL ACCURACY%`.

In the reference these percentages are hand-counted by a reviewer. Here the
denominators are the real field count for the batch and the numerators come from
the AI's own quality marks, so the sheet opens pre-populated. Values are written
as **formulas** (`=10/10*100`), never as computed literals, so a reviewer can
edit the counts and the sheet recalculates.

---

## Verifying a change

After editing either writer, re-run the diff against the reference:

```bash
cd backend
python -c "
from app.services.excel_ai import build_ai_workbook
# ... build a payload, compare cell-by-cell against the reference file
"
```

Check three things every time: cell **values**, cell **styles** (fill ARGB, font
colour, bold, size, name, alignment), and **row heights / column widths**. A
value-only diff will pass while the sheet looks wrong.
