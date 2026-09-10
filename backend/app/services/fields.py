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


def normalise_payload(
    raw: dict,
    tag_number: str,
    description: str,
    *,
    tag_number_quality: str = QUALITY_CONFIRMED,
    description_quality: str = QUALITY_CONFIRMED,
) -> dict:
    """Coerce anything Claude returned into the exact shape the app expects.

    Defensive by design: a model response is untrusted input. Missing keys are
    filled, unknown keys dropped, and quality marks constrained to the two
    legal values. `tag_number`/`description` are whatever the caller has
    already decided is final — the filename value, or the AI's own plate
    reading when the filename didn't have one or disagreed with it (see
    `reconcile_tag_number` and `reconcile_description` below) — never
    re-derived here. Each `*_quality` should be "Confirmed" when that final
    value stands unchallenged and "Verify" when there's any doubt about it
    (a mismatch the AI had to resolve, or a value the AI had to supply
    outright), so a reviewer knows exactly what to double check.
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
        # Claude is asked for month_of_manufacture as a zero-padded "MM"
        # string, but a JSON response can still carry it as a bare number
        # (e.g. 2 instead of "02") and str() alone would drop the padding.
        if f.key == "month_of_manufacture" and value.isdigit():
            value = value.zfill(2)
        out["fields"][f.key] = {"value": value or NOT_PRESENT, "quality": quality}

    # The caller's tag_number/description win for identity fields.
    out["fields"]["tag_number"] = {
        "value": tag_number,
        "quality": tag_number_quality if tag_number_quality in VALID_QUALITY else QUALITY_CONFIRMED,
    }
    out["fields"]["description"] = {
        "value": description,
        "quality": description_quality if description_quality in VALID_QUALITY else QUALITY_CONFIRMED,
    }

    out["remarks"] = str(raw.get("remarks", "") or "").strip()
    out["photo_status"] = str(raw.get("photo_status", "") or "").strip()
    out["qc_comment"] = str(raw.get("qc_comment", "") or "").strip()
    return out


def reconcile_tag_number(raw: dict, filename_tag_number: str) -> tuple[str, str]:
    """Prefer the tag number actually printed on the nameplate over the one
    parsed from the filename — but only when the AI found one on the plate
    and it disagrees with the filename. No independent read (or one that
    just confirms the filename) changes nothing.

    Returns (tag_number, quality), same criteria as `reconcile_description`:
    "Confirmed" when the filename's tag number stands unchallenged (Claude
    found nothing on the plate, or its reading agrees), "Verify" when
    Claude's independent plate reading disagrees — one of the two is wrong,
    so a reviewer needs to say which.
    """
    raw_fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
    entry = raw_fields.get("tag_number")
    photo_value = str(entry.get("value", "") or "").strip() if isinstance(entry, dict) else ""
    if is_blank(photo_value):
        return filename_tag_number, QUALITY_CONFIRMED
    if photo_value.upper() == filename_tag_number.strip().upper():
        return filename_tag_number, QUALITY_CONFIRMED
    return photo_value.upper(), QUALITY_VERIFY


#: Set when neither the upload nor a known equipment code could supply a
#: description and Claude's own read of the nameplate didn't either —
#: distinct from NOT_PRESENT, which means "this field isn't printed on the
#: plate", not "we don't know the equipment type at all".
UNRESOLVED_DESCRIPTION = "UNVERIFIED - CONFIRM EQUIPMENT DESCRIPTION"


def reconcile_description(raw: dict, upload_description: str) -> tuple[str, str]:
    """Fill in a tag-only upload's description from Claude's own reading of
    the equipment shown in the photo(s) — never overwrites an explicit,
    human/filename-supplied description.

    Returns (description, quality): "Confirmed" when the description came
    from the upload itself (typed, or resolved from a known equipment
    code), "Verify" when Claude had to determine it from the photo alone,
    so a reviewer knows to double check it.
    """
    if not is_blank(upload_description):
        return upload_description, QUALITY_CONFIRMED

    raw_fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
    entry = raw_fields.get("description")
    ai_value = str(entry.get("value", "") or "").strip() if isinstance(entry, dict) else ""
    if is_blank(ai_value):
        return UNRESOLVED_DESCRIPTION, QUALITY_VERIFY
    return ai_value.upper(), QUALITY_VERIFY


def value_of(payload: dict, key: str) -> str:
    return str(((payload.get("fields") or {}).get(key) or {}).get("value", "") or "")


def quality_of(payload: dict, key: str) -> str:
    q = str(((payload.get("fields") or {}).get(key) or {}).get("quality", "") or "")
    return q if q in VALID_QUALITY else QUALITY_VERIFY


def is_blank(value: str) -> bool:
    """True when a value carries no data for the Template sheet."""
    v = (value or "").strip()
    return not v or v.casefold() == NOT_PRESENT.casefold()
