"""Group the marker-view SVG elements of a PDS into one outline per piece.

Optitex draws pieces in PIECE order: each cut polygon is followed by its own sew, fold and notch
paths, and a piece cut on the fold is drawn as two mirrored halves followed by the fold line.
"""
from collections.abc import Iterator, Sequence
from xml.etree.ElementTree import Element

from app.domain.reference import PieceOutline, Polyline
from app.infrastructure.pds.svg_paths import Mark, classify, cut_ring, polyline


def _parts(svg: Element) -> list[dict[Mark, list[Polyline]]]:
    """One part per cut polygon, holding that polygon and the marks drawn after it."""
    parts: list[dict[Mark, list[Polyline]]] = []
    for element in svg:
        mark = classify(element)
        if mark is Mark.CUT:
            parts.append({Mark.CUT: [cut_ring(element)], Mark.SEW: [], Mark.FOLD: [], Mark.NOTCH: []})
        elif mark is not Mark.CLOTH:
            if not parts:
                raise ValueError("PDS SVG has a mark before any cut outline")
            parts[-1][mark].extend(polyline(path) for path in element.iter("path"))
    return parts


def _merge(parts: Sequence[dict[Mark, list[Polyline]]]) -> PieceOutline:
    def joined(mark: Mark) -> tuple[Polyline, ...]:
        return tuple(line for part in parts for line in part[mark])

    return PieceOutline(joined(Mark.CUT), joined(Mark.SEW), joined(Mark.FOLD), joined(Mark.NOTCH))


def piece_outlines(svg: Element, on_fold: Sequence[bool]) -> Iterator[PieceOutline]:
    """Yield an outline per piece, consuming two cut halves for each piece cut on the fold."""
    parts = _parts(svg)
    needed = sum(2 if folded else 1 for folded in on_fold)
    if len(parts) != needed:
        raise ValueError(f"PDS SVG has {len(parts)} cut outlines; the PIECE list needs {needed}")
    start = 0
    for folded in on_fold:
        count = 2 if folded else 1
        yield _merge(parts[start:start + count])
        start += count
