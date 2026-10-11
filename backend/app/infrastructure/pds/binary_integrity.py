"""Reject an Optitex .PDS whose binary block was destroyed by a text re-save (T140).

Saving a PDS as UTF-8 text turns every invalid byte into U+FFFD (``EF BF BD``). The XML
``<STYLE>`` section survives, so the XML reader alone would accept the file. The client's
genuine files have no such sequence outside the XML; a re-saved one has thousands. Random
binary produces one about once per 16.7 million offsets, so a threshold of 16 cannot misfire
on a genuine file. Text inside the XML is not counted.
"""

REPLACEMENT_MARK = b"\xef\xbf\xbd"
MAX_REPLACEMENT_MARKS = 16
_START, _END = b"<STYLE>", b"</STYLE>"


def check_binary_integrity(data: bytes) -> None:
    start = data.find(_START)
    end = data.find(_END, start)
    if start < 0 or end < 0:
        return  # no XML section: style_element reports "Not an Optitex PDS"
    marks = data.count(REPLACEMENT_MARK, 0, start) + data.count(REPLACEMENT_MARK, end + len(_END))
    if marks >= MAX_REPLACEMENT_MARKS:
        raise ValueError(f"PDS binary section is damaged: re-saved as text ({marks} replacement characters)")
