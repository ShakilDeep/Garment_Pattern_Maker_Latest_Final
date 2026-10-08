"""T125 (M0): malformed or tampered PDS input fails with a specific ValueError, never a partial style."""

import re

import pytest

from app.infrastructure.pds import read_pds
from app.infrastructure.pds.xml_section import MAX_PDS_BYTES

CUT_POLYGON = re.compile(rb'<polygon fill="#FFBE46"[^>]*/>\s*')


def _shirt(pds_bytes):
    return pds_bytes["1078375"]


def test_bytes_without_a_style_section_are_rejected():
    with pytest.raises(ValueError, match="Not an Optitex PDS"):
        read_pds(b"\x00\x01binary only")


def test_truncated_xml_is_rejected(pds_bytes):
    data = _shirt(pds_bytes)
    cut = data.index(b"<PIECE>")
    with pytest.raises(ValueError, match="PDS XML is malformed"):
        read_pds(data[:cut] + b"<PIECE><NAME>FRT" + data[data.index(b"</STYLE>"):])


def test_entity_references_are_not_expanded(pds_bytes):
    data = _shirt(pds_bytes).replace(b"<NAME>FRT</NAME>", b"<NAME>&boom;</NAME>", 1)
    with pytest.raises(ValueError, match="PDS XML is malformed"):
        read_pds(data)


def test_missing_base_size_names_the_field(pds_bytes):
    data = _shirt(pds_bytes).replace(b"<BASE_SIZE>L</BASE_SIZE>", b"", 1)
    with pytest.raises(ValueError, match="PDS field missing: SIZES_TABLE/BASE_SIZE"):
        read_pds(data)


def test_base_size_must_be_a_listed_size(pds_bytes):
    data = _shirt(pds_bytes).replace(b"<BASE_SIZE>L</BASE_SIZE>", b"<BASE_SIZE>4XL</BASE_SIZE>", 1)
    with pytest.raises(ValueError, match="base size 4XL is not in the size table"):
        read_pds(data)


def test_a_missing_cut_outline_is_a_count_mismatch(pds_bytes):
    data = _shirt(pds_bytes)
    last = list(CUT_POLYGON.finditer(data))[-1]
    data = data[:last.start()] + data[last.end():]
    with pytest.raises(ValueError, match="SVG has 11 cut outlines; the PIECE list needs 12"):
        read_pds(data)


def test_outlines_out_of_piece_order_are_rejected(pds_bytes):
    data = _shirt(pds_bytes)
    first, second = (match.group(0) for match in list(CUT_POLYGON.finditer(data))[:2])
    swapped = data.replace(first, b"<swap/>", 1).replace(second, first, 1).replace(b"<swap/>", second, 1)
    with pytest.raises(ValueError, match="SVG outline order does not match the PIECE list"):
        read_pds(swapped)


def test_unsupported_path_commands_are_rejected(pds_bytes):
    data = _shirt(pds_bytes).replace(b'd="M-183,8066 L7436,8066"', b'd="M-183,8066 C1,2 3,4 5,6"', 1)
    with pytest.raises(ValueError, match="Unsupported SVG path data"):
        read_pds(data)


def test_oversized_input_is_rejected_before_parsing():
    with pytest.raises(ValueError, match="PDS exceeds the 5 MB reader limit"):
        read_pds(b"<STYLE>" + b" " * MAX_PDS_BYTES + b"</STYLE>")


def test_a_mark_before_any_cut_outline_is_rejected(pds_bytes):
    data = CUT_POLYGON.sub(b"", _shirt(pds_bytes), count=1)
    with pytest.raises(ValueError, match="PDS SVG has a mark before any cut outline"):
        read_pds(data)


def test_unknown_svg_colours_are_rejected_not_dropped(pds_bytes):
    data = _shirt(pds_bytes).replace(b"fill:#FF6633", b"fill:#123456", 1)
    with pytest.raises(ValueError, match="Unsupported PDS SVG g colour #123456"):
        read_pds(data)


@pytest.mark.parametrize(("old", "new", "message"), [
    (b'SIZE_X="78.8880" ', b"", "PDS field missing: GEOM_INFO/@SIZE_X"),
    (b"<QUANTITY>2</QUANTITY>", b"<QUANTITY>2.5</QUANTITY>", "QUANTITY must be a whole number"),
    (b'd="M-183,8066 L7436,8066"', b'd="M-183,8066"', "PDS SVG path has fewer than 2 points"),
])
def test_incomplete_fields_name_the_problem(pds_bytes, old, new, message):
    with pytest.raises(ValueError, match=message):
        read_pds(_shirt(pds_bytes).replace(old, new, 1))
