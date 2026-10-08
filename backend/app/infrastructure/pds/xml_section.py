"""Locate and parse the readable XML section of an Optitex .PDS file.

A PDS is a binary container: a short header, an XML ``<STYLE>`` document and an undocumented
binary block. Only the bytes from ``<STYLE>`` to ``</STYLE>`` are parsed. A DOCTYPE is only
legal in the prolog, which this slice excludes, so no entity can be declared and an entity
reference fails to parse instead of expanding.
"""
from xml.etree import ElementTree

MAX_PDS_BYTES = 5_000_000
_START, _END = b"<STYLE>", b"</STYLE>"


def style_element(data: bytes) -> ElementTree.Element:
    if len(data) > MAX_PDS_BYTES:
        raise ValueError("PDS exceeds the 5 MB reader limit")
    start = data.find(_START)
    end = data.find(_END, start)
    if start < 0 or end < 0:
        raise ValueError("Not an Optitex PDS: no <STYLE> XML section")
    try:
        return ElementTree.fromstring(data[start:end + len(_END)])
    except ElementTree.ParseError as exc:
        raise ValueError(f"PDS XML is malformed: {exc}") from exc
