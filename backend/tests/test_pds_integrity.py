"""T140: a PDS re-saved as UTF-8 text keeps valid XML but has a destroyed binary block; reject it."""

import pytest

from app.infrastructure.pds import read_pds
from app.infrastructure.pds.binary_integrity import MAX_REPLACEMENT_MARKS, check_binary_integrity

MARK = b"\xef\xbf\xbd"
STYLES = ("1078375", "1074664")


def _resaved_as_text(data: bytes) -> bytes:
    return data.decode("utf-8", errors="replace").encode("utf-8")


def _with_marks_after_xml(data: bytes, count: int) -> bytes:
    end = data.index(b"</STYLE>") + len(b"</STYLE>")
    return data[:end] + MARK * count + data[end:]


@pytest.mark.parametrize("style", STYLES, ids=STYLES)
def test_a_text_resaved_pds_is_rejected(pds_bytes, style):
    with pytest.raises(ValueError, match="PDS binary section is damaged: re-saved as text"):
        read_pds(_resaved_as_text(pds_bytes[style]))


@pytest.mark.parametrize("style", STYLES, ids=STYLES)
def test_untouched_client_files_pass(pds_bytes, style):
    check_binary_integrity(pds_bytes[style])
    assert read_pds(pds_bytes[style]).pieces


def test_marks_below_the_threshold_are_tolerated(pds_bytes):
    data = _with_marks_after_xml(pds_bytes["1078375"], MAX_REPLACEMENT_MARKS - 1)
    assert read_pds(data).base_size == "L"


def test_marks_at_the_threshold_are_rejected_with_the_count(pds_bytes):
    data = _with_marks_after_xml(pds_bytes["1078375"], MAX_REPLACEMENT_MARKS)
    with pytest.raises(ValueError, match=rf"\({MAX_REPLACEMENT_MARKS} replacement characters\)"):
        read_pds(data)


def test_marks_inside_the_xml_text_are_not_counted(pds_bytes):
    marks = MARK * (MAX_REPLACEMENT_MARKS * 3)
    data = pds_bytes["1078375"].replace(b"<DESCRIPTION>", b"<DESCRIPTION>" + marks, 1)
    assert data.index(marks) < data.index(b"</STYLE>")
    check_binary_integrity(data)


def test_bytes_without_a_style_section_keep_the_reader_message():
    with pytest.raises(ValueError, match="Not an Optitex PDS"):
        read_pds(MARK * MAX_REPLACEMENT_MARKS * 2)
