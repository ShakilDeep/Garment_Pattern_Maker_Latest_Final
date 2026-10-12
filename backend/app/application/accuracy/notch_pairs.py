"""Notch pairs (spec §7 Finishing): every notch has a partner on the seam it sews to, at the same seam distance
within 0.1 cm.

A notch's seam is the block relation (``seams.RELATIONS``) whose named paths hold its edge; its partners are the
notches on the other side of that relation. Distances run from each side's first point; a side that starts at
the other end is measured back from its end. A notch the client PDS itself leaves unpaired is reported with the
block's reason and not gated; any other unpaired notch is an error.
"""
from collections.abc import Iterator, Mapping, Sequence
from itertools import pairwise

from shapely.geometry import LineString, Point

from app.application.accuracy.model import Check, Source
from app.domain.blocks.shirt.seams import Term
from app.domain.blocks.sketch.named_edges import edge
from app.domain.pattern.annotation import Notch
from app.domain.pattern.edges import edge_polyline
from app.domain.pattern.measure import segment_length
from app.domain.pattern.notch_position import notch_position
from app.domain.pattern.piece import Piece

PAIR_CM = 0.1
RULE = Source("setting", "spec §7: every notch has its pair at the same seam distance within 0.1 cm")
Side = tuple[Term, ...]
Placed = tuple[Piece, Notch, float]  # piece, notch, distance from its side's first point


def notch_distance(piece: Piece, notch: Notch) -> float:
    """How far along its own edge (from the edge's start) the notch sits, in cm."""
    segment = next(s for s in piece.outline if s.id == notch.segment)
    line = LineString([(p.x, p.y) for p in edge_polyline(segment, {p.id: p.position for p in piece.points})])
    at = notch_position(piece, notch)
    return float(line.project(Point(at.x, at.y)))


def _placed(side: Side, pieces: Mapping[str, Piece]) -> tuple[list[Placed], float]:
    """The notches on one side of a seam with their distances along it, and the side's length."""
    found, walked = [], 0.0
    for _, piece_id, path in side:
        piece = pieces[piece_id]
        for start, end in pairwise(path):
            segment = edge(piece, start, end)
            found += [(piece, n, walked + notch_distance(piece, n)) for n in piece.notches if n.segment == segment.id]
            walked += segment_length(piece, segment)
    return found, walked


def _sides(relations: Mapping[str, Side]) -> Iterator[tuple[Side, Side]]:
    for terms in relations.values():
        plus, minus = tuple(t for t in terms if t[0] > 0), tuple(t for t in terms if t[0] < 0)
        yield plus, minus
        yield minus, plus


def _check(placed: Placed, gaps: list[float], unpaired: Mapping[str, str]) -> Check:
    piece, notch, distance = placed
    name, edge_id = f"{notch.id} pair", str(notch.segment)
    if gaps:
        gap = min(gaps)
        return Check(name, gap, f"partner within {PAIR_CM} cm", gap <= PAIR_CM, RULE, piece=piece.name, edge=edge_id)
    reason = unpaired.get(str(notch.id))
    source = RULE if reason is None else Source("pds", reason)
    return Check(name, distance, "a partner notch on the joining seam", False, source, gate=reason is None,
                 piece=piece.name, edge=edge_id)


def notch_pair_checks(pieces: Sequence[Piece], relations: Mapping[str, Side],
                      unpaired: Mapping[str, str]) -> list[Check]:
    by_id = {str(piece.id): piece for piece in pieces}
    gaps: dict[tuple[str, str], list[float]] = {}
    placed: dict[tuple[str, str], Placed] = {}
    for own, other in _sides(relations):
        mine, _ = _placed(own, by_id)
        theirs, length = _placed(other, by_id)
        reverse = own[0][2][0] != other[0][2][0]  # the sides start at opposite ends of the seam
        for item in mine:
            key = (item[0].name, str(item[1].id))
            placed[key] = item
            gaps.setdefault(key, []).extend(abs(item[2] - (length - d if reverse else d)) for *_, d in theirs)
    for piece in pieces:  # a notch on no seam relation has no partner to find
        for notch in piece.notches:
            placed.setdefault((piece.name, str(notch.id)), (piece, notch, notch_distance(piece, notch)))
    return [_check(item, gaps.get(key, []), unpaired) for key, item in placed.items()]
