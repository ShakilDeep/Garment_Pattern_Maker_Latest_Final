"""Each drafted 1078375 piece against its PDS piece: cut size and area (build plan M3) and every sew edge.

The PDS gives a fold piece's bbox for the drawn half but its AREA for the whole cut piece, so the drafted
half is compared on size and doubled for area.
"""
from dataclasses import replace

from app.application.accuracy.model import Check, Source, near
from app.domain.blocks.shirt.allowances import seam_allowance
from app.domain.blocks.sketch.named_edges import path_length
from app.domain.geom.polyline_ops import area, length
from app.domain.pattern.piece import Piece
from app.domain.reference import GeomInfo
from app.infrastructure.pds.shirt_named import NamedPiece
from app.infrastructure.piece_validity import check_cut_geometry

SIZE_CM = 1.5  # build plan M3: width and length within 1.5 cm of the PDS piece
AREA_SHARE = 0.03  # build plan M3: area within 3 % of the PDS piece
EDGE_CM = 0.1  # docs/drafting/shirt.md Q4: a drafted curve follows the PDS within 0.1 cm
CM2_PER_M2 = 10_000
PLAN = Source("pds", "build plan M3 (1078375 L)")
EDGES = Source("pds", "docs/drafting/shirt.md Q4")


def _area_check(piece: Piece, cut_area_cm2: float, pds: GeomInfo) -> Check:
    drafted = cut_area_cm2 * (2 if piece.fold else 1) / CM2_PER_M2
    passed = abs(drafted - pds.area_m2) <= AREA_SHARE * pds.area_m2
    return Check(f"{piece.name} cut area", drafted, f"3 % of {pds.area_m2} m2", passed, PLAN, piece=piece.name)


def size_checks(piece: Piece, pds: GeomInfo) -> list[Check]:
    cut = check_cut_geometry(piece, seam_allowance(str(piece.id)))
    xs, ys = [p.x for p in cut], [p.y for p in cut]
    ring = [(p.x, p.y) for p in (*cut, cut[0])]
    spans = [near(f"{piece.name} length", max(xs) - min(xs), pds.size_x_cm, SIZE_CM, PLAN),
             near(f"{piece.name} width", max(ys) - min(ys), pds.size_y_cm, SIZE_CM, PLAN)]
    return [*(replace(check, piece=piece.name) for check in spans), _area_check(piece, area(ring), pds)]


def edge_checks(piece: Piece, named: NamedPiece) -> list[Check]:
    """Every sew edge as long as the PDS edge between the same named points."""
    checks = []
    for segment in piece.outline:
        start, end = str(segment.start), str(segment.end)
        pds_length = length(named.run(start, end))
        check = near(f"{piece.name} {start}:{end}", path_length(piece, (start, end)), pds_length, EDGE_CM, EDGES)
        checks.append(replace(check, piece=piece.name, edge=f"{start}:{end}"))
    return checks
