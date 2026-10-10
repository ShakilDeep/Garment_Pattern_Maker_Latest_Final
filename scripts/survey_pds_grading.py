"""Survey the 1078375 PDS per-size piece numbers as the evidence for docs/grading/shirt.md (T131).

Usage: python scripts/survey_pds_grading.py
For each piece: cut length (x) and width (y), area, perimeter and sew perimeter per size, then each size's
step from the size before it. The PDS has no grade rules; these steps are all it says about grading.
Read-only: nothing is written.
"""
import sys
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.infrastructure.pds import read_pds

PDS = ROOT / "fixtures" / "reference_patterns" / "1078375.PDS"
FIELDS = (("length", "size_x_cm"), ("width", "size_y_cm"), ("area m2", "area_m2"), ("perimeter", "perimeter_cm"),
          ("sew perim", "sew_perimeter_cm"))


def _row(label: str, values: list[float]) -> str:
    return f"  {label:<10}" + "".join(f"{value:>10.4f}" for value in values)


def main() -> None:
    style = read_pds(PDS.read_bytes())
    sizes = style.sizes
    print(f"{style.name}  base {style.base_size}  (cut line unless 'sew'; cm and m2)")
    print(f"  {'SUM_AREA':<10}" + "".join(f"{style.totals[s].area_m2:>10.4f}" for s in sizes))
    print(f"  {'size':<10}" + "".join(f"{s:>10}" for s in sizes))
    for piece in style.pieces:
        print(f"\n== {piece.name}  x{piece.quantity}  fold={piece.on_fold}")
        for label, field in FIELDS:
            values = [getattr(piece.geometry[s], field) for s in sizes]
            print(_row(label, values))
            print(_row("  step", [0.0, *(b - a for a, b in pairwise(values))]))


if __name__ == "__main__":
    main()
