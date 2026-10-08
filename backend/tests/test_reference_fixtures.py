"""T125 (M0): the build-plan reference fixtures are present and byte-identical to the recorded sources."""

import hashlib
from io import BytesIO

import pytest
from conftest import REFERENCE_PATTERNS
from openpyxl import load_workbook

RECORDED_SHA256 = {
    "1078375.PDS": "3bb70849a5567db409c55b4a74588a7b2074df78e54d55ea1eb14342538ba347",
    "1074664.PDS": "deae727f203f70a9570d2668a2c858edd7a8c27fa38bcf2ab1b3ea5bd7ab7e1d",
    "CL1086464.xlsx": "34c8e8e9a9311905567c007c0538cffc1a6dd96dc5a302f1f4ddc68253596993",
}


@pytest.mark.parametrize(("name", "digest"), RECORDED_SHA256.items())
def test_fixture_is_unchanged(name, digest):
    assert hashlib.sha256((REFERENCE_PATTERNS / name).read_bytes()).hexdigest() == digest


def test_readme_records_the_same_hashes():
    readme = (REFERENCE_PATTERNS / "README.md").read_text(encoding="utf-8")
    assert all(f"`{name}`" in readme and digest in readme for name, digest in RECORDED_SHA256.items())


def test_pant_measurement_workbook_opens():
    workbook = load_workbook(BytesIO((REFERENCE_PATTERNS / "CL1086464.xlsx").read_bytes()), read_only=True)
    assert workbook.sheetnames
