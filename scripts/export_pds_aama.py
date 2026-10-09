"""Write the M2 Optitex-gate files: each reference PDS's base outlines as DXF-AAMA (build plan M2, T127).

Usage: python scripts/export_pds_aama.py --out DIR [--unit mm|inch]
Give the files to a person with Optitex (File > Import > DXF AAMA/ASTM) to confirm piece names, fold
lines, grain and notches. Nothing is written into the repository unless DIR points there.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.infrastructure.aama.from_pds import pds_to_interchange
from app.infrastructure.aama.writer import write_aama
from app.infrastructure.pds import read_pds

REFERENCE_PATTERNS = ROOT / "fixtures" / "reference_patterns"
STYLES = ("1078375", "1074664")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="directory for the .dxf files")
    parser.add_argument("--unit", choices=("mm", "inch"), default="mm")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for number in STYLES:
        style = read_pds((REFERENCE_PATTERNS / f"{number}.PDS").read_bytes())
        target = args.out / f"{number}_{style.base_size}_aama.dxf"
        target.write_bytes(write_aama(pds_to_interchange(style), args.unit))
        print(f"{target}  ({len(style.pieces)} pieces, base {style.base_size})")


if __name__ == "__main__":
    main()
