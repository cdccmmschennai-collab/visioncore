"""The canonical field schema shared by Claude, the UI table, and both workbooks.

One list drives everything: the JSON keys Claude must return, the row order of
the AI Output sheet, and the column order of the Template's `Asset Tags` sheet.
Change the order here and every artefact follows — there is no second place to
keep in sync.
"""
from dataclasses import dataclass

# Sentinel Claude returns when a field simply is not printed on the nameplate.
# The AI Output workbook prints it verbatim (it is a finding); the Template
# workbook leaves the cell blank (it is a data field with no data).
NOT_PRESENT = "Not present on nameplate"

QUALITY_CONFIRMED = "Confirmed"
QUALITY_VERIFY = "Verify"
VALID_QUALITY = (QUALITY_CONFIRMED, QUALITY_VERIFY)


@dataclass(frozen=True)
class FieldDef:
    key: str            # JSON / API key
    ai_label: str       # column A label in the AI Output sheet
    template_header: str  # header in the Template `Asset Tags` sheet
    ui_label: str       # label in the editable table
    multiline: bool = False   # renders as a textarea in the UI


#: Order is significant — do not sort.
FIELDS: tuple[FieldDef, ...] = (
    FieldDef("tag_number", "Tag Number", "TAG NUMBER", "Tag Number"),
    FieldDef("description", "Equipment Description", "EQUIPMENT DESCRIPTION", "Equipment Description"),
    FieldDef("size_dimension", "Size / Dimension", "SIZE/DIMENSION", "Size / Dimension"),
    FieldDef("make", "Manufacturer / Make", "MAKE (ASSET)", "Manufacturer / Make"),
    FieldDef("model", "Model", "MODEL", "Model"),
    FieldDef("serial_no", "Serial No.", "SERIAL NO", "Serial No."),
    FieldDef("part_no", "Part No.", "PART NO", "Part No."),
    FieldDef("weight", "Weight", "WEIGHT", "Weight"),
    FieldDef("country", "Country", "COUNTRY", "Country"),
    FieldDef("year_of_manufacture", "Year of Manufacture", "YEAR OF MANUFACTURE YYYY", "Year of Manufacture"),
    FieldDef("month_of_manufacture", "Month of Manufacture", "MONTH OF MANUFACTURE MM", "Month of Manufacture"),
    FieldDef("hazardous_classification", "Hazardous Area Classification", "EQPT HAZARDOUS CLASSIFICATION", "Hazardous Area Classification", multiline=True),
    FieldDef("additional_information", "Additional Information", "ADDITIONAL INFORMATION", "Additional Information", multiline=True),
)

#: Free-text narrative row. It has no Data Quality mark in the reference file,
#: so it is handled separately from FIELDS everywhere.
REMARKS_FIELD = FieldDef("remarks", "Remarks", "REMARKS", "Remarks", multiline=True)

#: Template-only QC columns. Claude does not populate these; a reviewer does.
PHOTO_STATUS_FIELD = FieldDef("photo_status", "", "PHOTO STATUS", "Photo Status")
QC_COMMENT_FIELD = FieldDef("qc_comment", "", "QC COMMENT", "QC Comment", multiline=True)

FIELD_KEYS: tuple[str, ...] = tuple(f.key for f in FIELDS)
ALL_EDITABLE_KEYS: tuple[str, ...] = FIELD_KEYS + (
    REMARKS_FIELD.key,
    PHOTO_STATUS_FIELD.key,
    QC_COMMENT_FIELD.key,
)

FIELD_BY_KEY: dict[str, FieldDef] = {f.key: f for f in FIELDS}


def empty_payload(tag_number: str = "", description: str = "") -> dict:
    """A payload with every key present, so the UI never renders undefined."""
    payload: dict = {
        "fields": {
            f.key: {"value": "", "quality": QUALITY_VERIFY} for f in FIELDS
        },
        "remarks": "",
        "photo_status": "",
        "qc_comment": "",
    }
    payload["fields"]["tag_number"] = {"value": tag_number, "quality": QUALITY_CONFIRMED}
    payload["fields"]["description"] = {"value": description, "quality": QUALITY_CONFIRMED}
    return payload


def normalise_payload(raw: dict, tag_number: str, description: str) -> dict:
    """Coerce anything Claude returned into the exact shape the app expects.

    Defensive by design: a model response is untrusted input. Missing keys are
    filled, unknown keys dropped, and quality marks constrained to the two
    legal values. Tag number and description always come from the filename —
    they are ground truth from the folder structure, not something to infer.
    """
    out = empty_payload(tag_number, description)
    raw_fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}

    for f in FIELDS:
        entry = raw_fields.get(f.key)
        if isinstance(entry, dict):
            value = str(entry.get("value", "") or "").strip()
            quality = str(entry.get("quality", "") or "").strip().title()
        elif isinstance(entry, str):
            value, quality = entry.strip(), QUALITY_VERIFY
        else:
            value, quality = "", QUALITY_VERIFY

        if quality not in VALID_QUALITY:
            quality = QUALITY_VERIFY
        out["fields"][f.key] = {"value": value or NOT_PRESENT, "quality": quality}

    # Filename wins for identity fields.
    out["fields"]["tag_number"] = {"value": tag_number, "quality": QUALITY_CONFIRMED}
    out["fields"]["description"] = {"value": description, "quality": QUALITY_CONFIRMED}

    out["remarks"] = str(raw.get("remarks", "") or "").strip()
    out["photo_status"] = str(raw.get("photo_status", "") or "").strip()
    out["qc_comment"] = str(raw.get("qc_comment", "") or "").strip()
    return out


def value_of(payload: dict, key: str) -> str:
    return str(((payload.get("fields") or {}).get(key) or {}).get("value", "") or "")


def quality_of(payload: dict, key: str) -> str:
    q = str(((payload.get("fields") or {}).get(key) or {}).get("quality", "") or "")
    return q if q in VALID_QUALITY else QUALITY_VERIFY


def is_blank(value: str) -> bool:
    """True when a value carries no data for the Template sheet."""
    v = (value or "").strip()
    return not v or v.casefold() == NOT_PRESENT.casefold()
