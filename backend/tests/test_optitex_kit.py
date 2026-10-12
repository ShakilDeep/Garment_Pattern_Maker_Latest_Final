"""T146 (shirt): the Optitex test kit builds the Export button's zip, its checksums and the tester's record form."""
import importlib.util
import zipfile
from hashlib import sha256
from pathlib import Path

import pytest

from app.infrastructure.aama.reader import read_aama

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
ZIP = "shirt_1078375_graded_aama.zip"
FILES = {ZIP, "README.txt", "base.dxf", "grade_rules.rul", "all_sizes.dxf", "SHA256SUMS.txt", "OPTITEX_RECORD.md"}
PIECES = ("FRT", "back", "back YK", "CLR", "BND TOP", "BND IN", "Sleeve")
SIZES = ("S", "M", "L", "XL", "XXL", "3XL")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def kit(tmp_path_factory):
    out = tmp_path_factory.mktemp("kit")
    return out, _load("optitex_kit").build_kit(out, "mm")


def test_the_kit_holds_the_zip_its_files_checksums_and_the_record_form(kit):
    out, zip_path = kit
    assert zip_path == out / ZIP and {path.name for path in out.iterdir()} == FILES
    assert sorted(zipfile.ZipFile(zip_path).namelist()) == ["README.txt", "all_sizes.dxf", "base.dxf",
                                                           "grade_rules.rul"]
    assert "Optitex import not yet verified" in (out / "README.txt").read_text()


def test_every_checksum_is_the_file_s_own(kit):
    out, _ = kit
    sums = dict(reversed(line.split("  ")) for line in (out / "SHA256SUMS.txt").read_text().splitlines())
    assert set(sums) == FILES - {"SHA256SUMS.txt", "OPTITEX_RECORD.md"}
    assert all(sums[name] == sha256((out / name).read_bytes()).hexdigest() for name in sums)


def test_the_base_dxf_is_the_client_shirt_in_metric(kit):
    out, _ = kit
    style = read_aama((out / "base.dxf").read_bytes())
    assert tuple(piece.name for piece in style.pieces) == PIECES and style.sample_size == "L"


def test_the_record_form_names_the_files_and_leaves_the_findings_blank(kit):
    out, zip_path = kit
    record = (out / "OPTITEX_RECORD.md").read_text()
    assert sha256(zip_path.read_bytes()).hexdigest() in record
    assert all(size in record for size in SIZES) and all(f"`{piece}`" in record for piece in PIECES)
    assert "Menu path used: ________" in record
    assert record.rstrip().endswith("Optitex import not yet verified.")


def test_an_inaccurate_project_builds_no_kit(tmp_path, monkeypatch):
    module = _load("optitex_kit")
    failed = {"status": "errors", "checks": [{"name": "S SUM_AREA", "gate": True, "passed": False}]}
    monkeypatch.setattr(module, "accuracy_report", lambda project: failed)
    with pytest.raises(SystemExit, match="Accuracy report is errors: S SUM_AREA"):
        module.build_kit(tmp_path / "kit", "mm")
    assert not (tmp_path / "kit").exists()
