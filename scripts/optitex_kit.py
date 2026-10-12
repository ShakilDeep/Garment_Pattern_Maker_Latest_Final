"""Build the Optitex test kit for the graded 1078375 shirt (T146): exactly what the app's Export button gives.

Usage: python scripts/optitex_kit.py --out DIR [--unit mm|inch]
A throwaway project (temporary database) is drafted from the client block's accepted reference values and
graded S-3XL, as the app does. If its accuracy report is not ready, nothing is written. Otherwise DIR gets the
zip, its four files, SHA256SUMS.txt and OPTITEX_RECORD.md, the form the person with Optitex fills in.
Optitex import not yet verified: only that filled-in record, copied into markdown/MASTER.md, can change it.
"""
import argparse
import io
import sys
import tempfile
import zipfile
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from optitex_record import KitFacts, record_form

from app.application.accuracy.project_report import accuracy_report
from app.application.grading.project_aama import project_graded_aama
from app.application.project_style import project_style
from app.application.requirement_resolve import resolve
from app.application.service import Service
from app.infrastructure.aama.reader import read_aama
from app.infrastructure.repository import Repository

ANSWERS = {"units": "cm", "review": "confirmed", "placket": "workbook", "profile": "shirt_1078375",
           "block_reference": "accepted"}
BASE, GRADED = "L", ["S", "M", "XL", "XXL", "3XL"]


def _project(path: Path) -> dict:
    repository = Repository(f"sqlite:///{path}/kit.db")
    try:
        service = Service(repository)
        project = service.create("Optitex test 1078375", True)
        for key, value in ANSWERS.items():
            resolve(project, key, value)
        service.generate(project, BASE)
        service.grade(service.repo.get(project["id"]), GRADED)
        return service.repo.get(project["id"])
    finally:
        repository.engine.dispose()


def _require_ready(project: dict) -> None:
    report = accuracy_report(project)
    if report["status"] != "ready":
        failed = ", ".join(c["name"] for c in report["checks"] if c["gate"] and not c["passed"])
        raise SystemExit(f"Accuracy report is {report['status']}: {failed}")


def _write(out: Path, data: bytes, zip_name: str) -> dict[str, str]:
    """The zip and its members, side by side; returns each file's sha256."""
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = {zip_name: data} | {name: archive.read(name) for name in archive.namelist()}
    for name, content in files.items():
        (out / name).write_bytes(content)
    return {name: sha256(content).hexdigest() for name, content in sorted(files.items())}


def build_kit(out: Path, unit: str) -> Path:
    with tempfile.TemporaryDirectory() as temporary:
        project = _project(Path(temporary))
    _require_ready(project)
    data, zip_name = project_graded_aama(project, unit)
    sums = _write(out, data, zip_name)
    (out / "SHA256SUMS.txt").write_text("".join(f"{digest}  {name}\n" for name, digest in sums.items()))
    base = read_aama((out / "base.dxf").read_bytes())
    style = project_style(project)
    sizes = () if style is None else style.sizes
    facts = KitFacts(zip_name, sums, sizes, tuple(piece.name for piece in base.pieces))
    (out / "OPTITEX_RECORD.md").write_text(record_form(facts))
    return out / zip_name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="directory for the kit")
    parser.add_argument("--unit", choices=("mm", "inch"), default="mm")
    args = parser.parse_args()
    zip_path = build_kit(args.out, args.unit)
    for path in sorted(zip_path.parent.iterdir()):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
