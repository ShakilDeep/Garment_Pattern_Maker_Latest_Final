"""The client reference each block is checked against (T143): its Optitex .PDS, read once per process.

The files are the byte-for-byte fixtures in ``fixtures/reference_patterns`` (hashes pinned by the tests),
shipped in the image beside ``backend/``. ``read_pds`` refuses a copy whose binary block was destroyed.
"""
from functools import cache
from pathlib import Path

from app.domain.reference import ReferenceStyle
from app.infrastructure.pds.reader import read_pds

REFERENCE_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "reference_patterns"
REFERENCES = {"shirt_1078375": "1078375.PDS"}  # block id -> client PDS; blocks not listed have none


@cache
def reference_for(block_id: str) -> ReferenceStyle | None:
    name = REFERENCES.get(block_id)
    return None if name is None else read_pds((REFERENCE_DIR / name).read_bytes())
