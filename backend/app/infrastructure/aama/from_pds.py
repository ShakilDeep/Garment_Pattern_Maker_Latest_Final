"""Adapter: an Optitex PDS ReferenceStyle (base size) -> InterchangeStyle for DXF-AAMA export (M2).

Outlines, sew lines, fold lines, notches, names, quantities and the style name are copied unchanged. PDS
notches are 0.7 cm slits starting on the sew line, and stay exactly there. A piece cut on the fold exports
its first half with the fold as its mirror line; a notch nearer the second half is mirrored onto the first
so none is lost. The PDS has no grain lines: grain is drawn parallel to the
Optitex marker length (X) and every piece says so in an annotation (user decision 2026-10-09).
"""
from app.domain.interchange import InterchangePiece, InterchangeStyle, Notch, Ring, Segment
from app.domain.reference import ReferencePiece, ReferenceStyle
from app.infrastructure.aama.geometry import distance_to_ring, reflect

ASSUMED_GRAIN = "Grain: parallel to the Optitex marker length (assumed; confirm in Optitex)"
GRAIN_SPAN = 0.6  # share of the piece's X extent the drawn grain line covers


def pds_to_interchange(style: ReferenceStyle) -> InterchangeStyle:
    pieces = tuple(_piece(piece, style.base_size) for piece in style.pieces)
    return InterchangeStyle(name=style.name, sample_size=style.base_size, pieces=pieces)


def _piece(piece: ReferencePiece, size: str) -> InterchangePiece:
    outline = piece.outline
    cut = outline.cut[0]
    mirror: Segment | None = None
    notches: tuple[Notch, ...] = outline.notches
    sew: tuple[Ring, ...] = outline.sew
    if piece.on_fold:
        fold = outline.folds[0]
        mirror = (fold[0], fold[-1])
        sew = outline.sew[:1]
        halves = [(ring, *outline.sew[index:index + 1]) for index, ring in enumerate(outline.cut)]
        notches = tuple(_onto_first_half(notch, halves, mirror) for notch in outline.notches)
    return InterchangePiece(
        name=piece.name, size=size, quantity=piece.quantity, cut=cut, sew=sew, mirror=mirror,
        notches=notches, grain=_grain(cut), annotations=(ASSUMED_GRAIN,))


def _onto_first_half(notch: Notch, halves: list[tuple[Ring, ...]], axis: Segment) -> Notch:
    """Keep a notch drawn on the first half; mirror one drawn on the second half onto the first."""
    def distance(rings: tuple[Ring, ...]) -> float:
        return min(distance_to_ring(point, ring) for ring in rings for point in notch)

    return notch if distance(halves[0]) <= distance(halves[1]) else tuple(reflect(p, axis) for p in notch)


def _grain(cut: Ring) -> Segment:
    xs, ys = [x for x, _ in cut], [y for _, y in cut]
    centre_x, centre_y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    half_span = (max(xs) - min(xs)) * GRAIN_SPAN / 2
    return (centre_x - half_span, centre_y), (centre_x + half_span, centre_y)
