"""Write the 1078375 block's data files from the client PDS (T130): measurements and shape constants.

Usage: python scripts/derive_shirt_1078375.py
Reads fixtures/reference_patterns/1078375.PDS and writes backend/app/domain/data/measurements_1078375_L.json,
shirt_1078375_shape.json and the graded sizes, measurements_1078375_graded.json (docs/grading/shirt.md).
tests/test_shirt_reference_data.py and test_shirt_grade_data.py fail if the files drift from the PDS.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.blocks.shirt.reference import GRADED_FILE, MEASUREMENTS_FILE
from app.domain.blocks.shirt.shape import SHAPE_FILE
from app.infrastructure.pds import read_pds
from app.infrastructure.pds.shirt_derive import derive
from app.infrastructure.pds.shirt_grade_derive import derive_graded

PDS = ROOT / "fixtures" / "reference_patterns" / "1078375.PDS"


def main() -> None:
    style = read_pds(PDS.read_bytes())
    measurements, shape = derive(style)
    for path, data in ((MEASUREMENTS_FILE, measurements), (SHAPE_FILE, shape)):
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    GRADED_FILE.write_text(json.dumps(derive_graded(style), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {GRADED_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
