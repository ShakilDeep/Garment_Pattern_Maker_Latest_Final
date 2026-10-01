"""P0-04 / defect d: grading a stored pattern version uses that version's own inputs."""
from test_integrity import _ready


def _chest(client, url):
    rows = client.get(url).json()["measurements"]
    return next(row for row in rows if row["key"] == "half_chest")


def _edit_chest(client, url, size, value):
    row = _chest(client, url)
    body = {"size": size, "changes": {row["key"]: value}}
    assert client.patch(f"{url}/measurements", json=body).status_code == 200
    assert client.post(f"{url}/requirements/review/resolve", json={"value": "confirmed"}).status_code == 200


def test_older_version_grades_from_its_own_measurements(tmp_path):
    client, url = _ready(tmp_path)
    old = client.post(f"{url}/patterns/generate", json={"size": "L", "allowance": 0}).json()
    before = client.post(f"{url}/patterns/{old['id']}/grade", json={"sizes": ["M"]}).json()
    _edit_chest(client, url, "M", _chest(client, url)["values"]["M"]["value"] + 4)
    assert client.post(f"{url}/patterns/generate", json={"size": "L", "allowance": 2}).status_code == 200
    after = client.post(f"{url}/patterns/{old['id']}/grade", json={"sizes": ["M"]})
    assert after.status_code == 200
    graded = after.json()[0]
    assert graded["input_hash"] == before[0]["input_hash"]
    assert graded["seam_allowance"] == 0
    assert graded["graded_from"] == old["id"]
    assert graded["sources"] == old["sources"]


def test_current_version_grading_still_uses_current_measurements(tmp_path):
    client, url = _ready(tmp_path)
    old = client.post(f"{url}/patterns/generate", json={"size": "L"}).json()
    before = client.post(f"{url}/patterns/{old['id']}/grade", json={"sizes": ["M"]}).json()
    _edit_chest(client, url, "M", _chest(client, url)["values"]["M"]["value"] + 4)
    current = client.post(f"{url}/patterns/generate", json={"size": "L"}).json()
    graded = client.post(f"{url}/patterns/{current['id']}/grade", json={"sizes": ["M"]}).json()
    assert graded[0]["input_hash"] != before[0]["input_hash"]


def test_grading_a_graded_size_is_rejected(tmp_path):
    client, url = _ready(tmp_path)
    client.post(f"{url}/patterns/generate", json={"size": "L"})
    grade = client.post(f"{url}/grade", json={"sizes": ["M"]}).json()[0]
    response = client.post(f"{url}/patterns/{grade['id']}/grade", json={"sizes": ["S"]})
    assert response.status_code == 400
    assert response.json()["code"] == "INPUT_INVALID"


def test_imported_inputs_are_dropped_and_legacy_history_versions_refuse_grading(tmp_path):
    client, url = _ready(tmp_path)
    generated = client.post(f"{url}/patterns/generate", json={"size": "L"}).json()
    forged = {**generated, "id": "imported-v1", "inputs": {"measurements": [], "resolutions": {}, "techpack": None}}
    body = {"schema_version": 1, "project": "Integrity", "pattern": forged}
    assert client.post(f"{url}/exports/import", json=body).status_code == 200
    assert "inputs" not in client.get(url).json()["pattern"]
    assert client.post(f"{url}/patterns/generate", json={"size": "L"}).status_code == 200
    response = client.post(f"{url}/patterns/imported-v1/grade", json={"sizes": ["M"]})
    assert response.status_code == 409
    assert "predates stored inputs" in response.json()["message"]


def test_grading_an_old_version_leaves_its_stored_inputs_untouched(tmp_path):
    client, url = _ready(tmp_path)
    old = client.post(f"{url}/patterns/generate", json={"size": "L"}).json()
    client.post(f"{url}/patterns/generate", json={"size": "L"})
    stored = client.get(url).json()["pattern_history"][-1]["inputs"]
    assert client.post(f"{url}/patterns/{old['id']}/grade", json={"sizes": ["S", "M"]}).status_code == 200
    assert client.get(url).json()["pattern_history"][-1]["inputs"] == stored
    assert set(stored) == {"measurements", "resolutions", "techpack"}


def test_stale_legacy_current_version_refuses_grading_from_current_inputs(tmp_path):
    client, url = _ready(tmp_path)
    generated = client.post(f"{url}/patterns/generate", json={"size": "L"}).json()
    body = {"schema_version": 1, "project": "Integrity", "pattern": {**generated, "id": "legacy-v1"}}
    assert client.post(f"{url}/exports/import", json=body).status_code == 200
    _edit_chest(client, url, "M", _chest(client, url)["values"]["M"]["value"] + 4)
    response = client.post(f"{url}/patterns/legacy-v1/grade", json={"sizes": ["M"]})
    assert response.status_code == 409
    assert "predates stored inputs" in response.json()["message"]


def test_grading_an_unknown_version_is_not_found(tmp_path):
    client, url = _ready(tmp_path)
    client.post(f"{url}/patterns/generate", json={"size": "L"})
    response = client.post(f"{url}/patterns/no-such-version/grade", json={"sizes": ["M"]})
    assert response.status_code == 404
