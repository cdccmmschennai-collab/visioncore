"""Tests for the <TAG>-<DESCRIPTION> filename/folder-name parser."""
import pytest

from app.services.filename_parser import parse_filename, parse_folder_name


@pytest.mark.parametrize(
    "filename, tag_number, description",
    [
        # The original reference format: description hyphen-separated from
        # a clean 4-segment tag.
        ("12-4020-BV-0074-BALL VALVE.jpg", "12-4020-BV-0074", "BALL VALVE"),
        # A 4-letter tag code segment must not be mistaken for the start of
        # the description just because it's alphabetic and 4+ characters.
        (
            "12-lJBF-1067-FIRE AND GAS JUNCTION BOX.jpg",
            "12-LJBF-1067",
            "FIRE AND GAS JUNCTION BOX",
        ),
        # Comma directly after the tag's numeric tail, no space around it.
        (
            "12-4021-TE-1001,TEMPERATURE ELEMENT.jpg",
            "12-4021-TE-1001",
            "TEMPERATURE ELEMENT",
        ),
        # Underscore directly after the tag's numeric tail.
        (
            "12-4021-TIT-1001_ELECTRONIC TEMPERATURE TRANSMITTER.jpg",
            "12-4021-TIT-1001",
            "ELECTRONIC TEMPERATURE TRANSMITTER",
        ),
        # Underscore used *within* the description as a plain space
        # substitute must still work (the original documented case).
        ("12-4020-BV-0074-BALL_VALVE.jpg", "12-4020-BV-0074", "BALL VALVE"),
        # A comma *inside* the description (not at the tag boundary) is kept
        # literally, matching the reference workbook convention.
        ("12-4020-BV-0074-VALVE,GATE.jpg", "12-4020-BV-0074", "VALVE,GATE"),
        # Three-segment tag with a single trailing one-word description.
        ("21-JDD-01-PUMP.jpg", "21-JDD-01", "PUMP"),
        # A browser-appended "(1)" duplicate suffix is stripped.
        ("12-4020-BV-0074-BALL VALVE (1).jpg", "12-4020-BV-0074", "BALL VALVE"),
        # Bare space directly after the tag's numeric tail — no hyphen,
        # comma or underscore at all between tag and description.
        (
            "12-lJBF-1067 FIRE AND GAS JUNCTION BOX.jpg",
            "12-LJBF-1067",
            "FIRE AND GAS JUNCTION BOX",
        ),
        # Same space-separator case with a 3-segment tag and single-word
        # description, to confirm it's not just a 4-segment/multi-word thing.
        ("21-JDD-01 PUMP.jpg", "21-JDD-01", "PUMP"),
        # Tag's trailing revision-letter fragment ("8981B") sits right before
        # the space that separates it from the description — must not be
        # sheared off into the description ("PM" / "8981B MOTOR,PUMP").
        ("PM-8981B MOTOR,PUMP.jpg", "PM-8981B", "MOTOR,PUMP"),
        ("PM-1234A VALVE.jpg", "PM-1234A", "VALVE"),
        ("P-1001 MOTOR.jpg", "P-1001", "MOTOR"),
        # Tag number only, no description segment at all: the tag's own
        # embedded equipment code ("BV") supplies the description.
        ("12-4020-BV-0074.jpg", "12-4020-BV-0074", "BALL VALVE"),
        ("22-4203-BV-0119.jpg", "22-4203-BV-0119", "BALL VALVE"),
        ("22-4203-GV-0119.jpg", "22-4203-GV-0119", "GATE VALVE"),
        ("22-4203-GLV-0119.jpg", "22-4203-GLV-0119", "GLOBE VALVE"),
        ("22-4203-BFV-0119.jpg", "22-4203-BFV-0119", "BUTTERFLY VALVE"),
        ("22-4203-PMP-0119.jpg", "22-4203-PMP-0119", "PUMP"),
        ("22-4203-MTR-0119.jpg", "22-4203-MTR-0119", "MOTOR"),
        ("22-4203-CMP-0119.jpg", "22-4203-CMP-0119", "COMPRESSOR"),
        ("22-4203-PG-0119.jpg", "22-4203-PG-0119", "PRESSURE GAUGE"),
    ],
)
def test_parse_filename_valid(filename, tag_number, description):
    result = parse_filename(filename)
    assert result.ok, result.reason
    assert result.tag_number == tag_number
    assert result.description == description


@pytest.mark.parametrize(
    "filename",
    [
        "BALLVALVE.jpg",            # no separator at all
        "12-4020-XY-0074.jpg",      # no description, unrecognized code
        "notes.txt",                # unsupported extension
        "12--0074-BALL VALVE.jpg",  # empty segment
        "",                         # empty filename
        ".jpg",                     # extension only, no stem
        "   .jpg",                  # whitespace-only stem
        "12-4020-BV-0074-.jpg",     # trailing separator, no description text
    ],
)
def test_parse_filename_invalid(filename):
    """Malformed input must fail safely with a reason, never raise."""
    result = parse_filename(filename)
    assert not result.ok
    assert result.reason


def test_parse_folder_name_matches_filename_convention():
    """Folder uploads use the same split logic, applied to the folder name."""
    result = parse_folder_name("12-4021-TE-1001,TEMPERATURE ELEMENT")
    assert result.ok
    assert result.tag_number == "12-4021-TE-1001"
    assert result.description == "TEMPERATURE ELEMENT"


def test_parse_folder_name_space_separator():
    result = parse_folder_name("12-lJBF-1067 FIRE AND GAS JUNCTION BOX")
    assert result.ok
    assert result.tag_number == "12-LJBF-1067"
    assert result.description == "FIRE AND GAS JUNCTION BOX"


def test_parse_folder_name_tag_only_infers_description_from_equipment_code():
    result = parse_folder_name("22-4203-BV-0119")
    assert result.ok
    assert result.tag_number == "22-4203-BV-0119"
    assert result.description == "BALL VALVE"


@pytest.mark.parametrize(
    "garbage",
    [
        "????.jpg",
        "🔥🔥🔥.jpg",
        "-----.jpg",
        ",,,,.jpg",
        "____.jpg",
        "12-4020-BV-0074-" + "X" * 500 + ".jpg",  # pathologically long description
    ],
)
def test_parse_filename_never_raises(garbage):
    """Unrecognizable or pathological input must fail safely, never throw."""
    result = parse_filename(garbage)
    assert isinstance(result.ok, bool)
