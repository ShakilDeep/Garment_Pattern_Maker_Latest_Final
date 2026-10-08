import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.infrastructure.parsers import parse_xlsx


@pytest.fixture(scope="module")
def rows():
    root = Path(__file__).resolve().parents[2]
    return parse_xlsx((root / "references/Book2(4).xlsx").read_bytes(), "Book2(4).xlsx")


@pytest.fixture(scope="module")
def golden():
    root = Path(__file__).resolve().parents[2]
    return json.loads((root / "fixtures/demo_v1_metrics.json").read_text())


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    """A project with a pattern, two grades and a mixed marker, plus its JSON export."""
    from test_integrity import _ready

    client, url = _ready(tmp_path_factory.mktemp("import"))
    assert client.post(f"{url}/patterns/generate", json={"size": "L"}).status_code == 200
    assert client.post(f"{url}/grade", json={"sizes": ["S", "M"]}).status_code == 200
    assert client.post(f"{url}/markers/generate", json={"width": 150, "quantities": {"S": 1, "M": 1}}).status_code == 200
    return client, url, client.get(f"{url}/exports/json").json()


@pytest.fixture
def import_mutated(exported):
    """POST the export back after `mutate(body)`; raw JSON so NaN and huge integers reach the server."""
    client, url, payload = exported

    def post(mutate):
        body = deepcopy(payload)
        mutate(body)
        return client.post(f"{url}/exports/import", content=json.dumps(body),
                           headers={"content-type": "application/json"})
    return post


REFERENCE_PATTERNS = Path(__file__).resolve().parents[2] / "fixtures" / "reference_patterns"


@pytest.fixture(scope="session")
def pds_bytes():
    """Raw bytes of the build-plan Optitex PDS fixtures, keyed by style number."""
    return {style: (REFERENCE_PATTERNS / f"{style}.PDS").read_bytes() for style in ("1078375", "1074664")}


@pytest.fixture(scope="session")
def pds_styles(pds_bytes):
    from app.infrastructure.pds import read_pds

    return {style: read_pds(data) for style, data in pds_bytes.items()}
