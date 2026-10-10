"""Write the M4 Optitex-gate files for the graded 1078375 shirt (build plan M4, T131).

Usage: python scripts/export_shirt_graded.py --out DIR [--unit mm|inch]
Writes base.dxf (base size L with grade points), grade_rules.rul and all_sizes.dxf. Give them to a person
with Optitex (File > Import > DXF AAMA/ASTM, with the .RUL) to confirm all six sizes grade and nest.
Nothing is written into the repository unless DIR points there.
"""
import argparse
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.application.cad.style_from_block import style_from_block
from app.application.grading.aama_export import graded_aama


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="directory for the files")
    parser.add_argument("--unit", choices=("mm", "inch"), default="mm")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    archive = zipfile.ZipFile(io.BytesIO(graded_aama(style_from_block("shirt_1078375"), args.unit)))
    for name in archive.namelist():
        target = args.out / f"1078375_{name}"
        target.write_bytes(archive.read(name))
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
