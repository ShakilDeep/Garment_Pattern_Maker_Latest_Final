"""Survey the 1078375 shirt PDS base-size sew lines as the evidence for docs/drafting/shirt.md (T129).

Usage: python scripts/survey_pds_shirt.py
For each piece: every edge between turn points (the AAMA corner rule) with its ends, length and chord, and
for curved runs the best single cubic Bézier (handles as offsets from their own end point) and its largest
sample distance. A run that one cubic cannot follow within TOLERANCE_CM is also fitted as two cubics, split
where a notch meets it (else at its middle sample). Then fold lines and notches. Read-only.
"""
import sys
from itertools import pairwise
from math import hypot
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.geom.bezier_fit import fit_cubic
from app.domain.geom.primitives import Point2D
from app.infrastructure.aama.corners import split_vertices
from app.infrastructure.pds import read_pds

PDS = ROOT / "fixtures" / "reference_patterns" / "1078375.PDS"
TOLERANCE_CM = 0.05  # split report trigger only; the agreed fit tolerance is 0.1 (shirt.md Q4)
STRAIGHT_CM = 0.005  # a run whose samples all lie this close to its chord is a straight line

Point = tuple[float, float]


def _fmt(point: Point) -> str:
    return f"({point[0]:.2f}, {point[1]:.2f})"


def _runs(ring: tuple[Point, ...]) -> list[list[Point]]:
    """The closed sew ring cut at its turn points into runs from corner to corner."""
    points = list(ring[:-1] if ring[0] == ring[-1] else ring)
    turns, _ = split_vertices(tuple(points))
    starts = sorted({points.index(turn) for turn in turns})
    return [points[a:b + 1] if a < b else points[a:] + points[:b + 1] for a, b in zip(starts, starts[1:] + starts[:1])]


def _off_chord(run: list[Point]) -> float:
    (ax, ay), (bx, by) = run[0], run[-1]
    if (chord := hypot(bx - ax, by - ay)) == 0:
        return 0.0
    return max(abs((bx - ax) * (ay - y) - (ax - x) * (by - ay)) / chord for x, y in run)


def _cubic(run: list[Point]) -> str:
    fit = fit_cubic([Point2D(*point) for point in run])
    s, e = fit.start_handle, fit.end_handle
    return f"handles ({s.x:+.3f}, {s.y:+.3f}) / ({e.x:+.3f}, {e.y:+.3f}), max dev {fit.max_deviation:.3f}"


def _split(run: list[Point], notches: list[Point]) -> tuple[list[Point], list[Point]]:
    """Split at the foot of the nearest notch within 0.05 cm of the run, else at the middle sample."""
    feet = []
    for index, ((ax, ay), (bx, by)) in enumerate(pairwise(run)):
        for nx, ny in notches:
            t = max(0.0, min(1.0, ((nx - ax) * (bx - ax) + (ny - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
            foot = (ax + t * (bx - ax), ay + t * (by - ay))
            feet.append((hypot(foot[0] - nx, foot[1] - ny), index, foot))
    gap, index, foot = min(feet, default=(1.0, 0, run[0]))
    if gap > TOLERANCE_CM:
        middle = len(run) // 2
        return run[:middle + 1], run[middle:]
    return [*run[:index + 1], foot], [foot, *run[index + 1:]]


def _edge(run: list[Point], notches: list[Point]) -> str:
    length = sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in pairwise(run))
    chord = hypot(run[-1][0] - run[0][0], run[-1][1] - run[0][1])
    head = f"  {_fmt(run[0])} -> {_fmt(run[-1])}  length {length:.3f}  chord {chord:.3f}  samples {len(run)}"
    if len(run) == 2 or _off_chord(run) <= STRAIGHT_CM:
        return f"{head}  LINE"
    single = fit_cubic([Point2D(*point) for point in run])
    lines = [f"{head}  CUBIC {_cubic(run)}"]
    if single.max_deviation > TOLERANCE_CM and len(run) > 4:
        first, second = _split(run, notches)
        lines.append(f"    split at {_fmt(second[0])}: {_cubic(first)}  then {_cubic(second)}")
    return "\n".join(lines)


def main() -> None:
    style = read_pds(PDS.read_bytes())
    print(f"{style.name}  base {style.base_size}  sizes {' '.join(style.sizes)}  (sew line, cm, y up)")
    for piece in style.pieces:
        base = piece.geometry[style.base_size]
        print(f"\n== {piece.name}  x{piece.quantity}  fold={piece.on_fold}  bbox {base.size_x_cm} x "
              f"{base.size_y_cm}  area {base.area_m2} m2  sew perimeter {base.sew_perimeter_cm}")
        notches = [notch[0] for notch in piece.outline.notches]
        for run in _runs(piece.outline.sew[0]):
            print(_edge(run, notches))
        for fold in piece.outline.folds:
            print(f"  fold {_fmt(fold[0])} -> {_fmt(fold[-1])}")
        for notch in piece.outline.notches:
            print(f"  notch {_fmt(notch[0])} -> {_fmt(notch[-1])}")


if __name__ == "__main__":
    main()
