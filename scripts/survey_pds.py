"""Survey a reference Optitex PDS's base-size sew lines: the evidence for docs/drafting/<garment>.md.

Usage: python scripts/survey_pds.py [--style 1078375|1074664]
For each piece: every edge between turn points (the AAMA corner rule) with its ends, length and chord, and
for curved runs the best single cubic Bézier (handles as offsets from their own end point) and its largest
sample distance (scripts/pds_survey_edges.py). Then fold lines and notches. Read-only.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pds_survey_edges import edge, fmt, runs

from app.infrastructure.pds import read_pds

REFERENCE_PATTERNS = ROOT / "fixtures" / "reference_patterns"
STYLES = ("1078375", "1074664")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--style", choices=STYLES, default="1078375")
    style = read_pds((REFERENCE_PATTERNS / f"{parser.parse_args().style}.PDS").read_bytes())
    print(f"{style.name}  base {style.base_size}  sizes {' '.join(style.sizes)}  (sew line, cm, y up)")
    for piece in style.pieces:
        base = piece.geometry[style.base_size]
        print(f"\n== {piece.name}  x{piece.quantity}  fold={piece.on_fold}  bbox {base.size_x_cm} x "
              f"{base.size_y_cm}  area {base.area_m2} m2  sew perimeter {base.sew_perimeter_cm}")
        notches = [notch[0] for notch in piece.outline.notches]
        if not piece.outline.sew:
            print("  no sew line (cut only)")
        for ring in piece.outline.sew[:1]:
            for run in runs(ring):
                print(edge(run, notches))
        for fold in piece.outline.folds:
            print(f"  fold {fmt(fold[0])} -> {fmt(fold[-1])}")
        for notch in piece.outline.notches:
            print(f"  notch {fmt(notch[0])} -> {fmt(notch[-1])}")


if __name__ == "__main__":
    main()
