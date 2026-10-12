"""T143: a project's accuracy report, every drafted size against the client PDS, with its From-block list."""
import pytest
from named_project import GRADED, shirt_project
from test_integrity import _ready

from app.application.accuracy.project_report import accuracy_report
from app.application.errors import NotReady
from app.application.service import Service
from app.domain.blocks.registry import installed
from app.infrastructure.repository import Repository

SUM_AREA = {"S": 1.2965, "M": 1.3607, "L": 1.4262, "XL": 1.5216, "XXL": 1.5993, "3XL": 1.6781}  # spec §7


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    _, project = shirt_project(tmp_path_factory.mktemp("graded"))
    return accuracy_report(project)


def by_name(report: dict) -> dict:
    return {check["name"]: check for check in report["checks"]}


def test_the_client_block_is_ready_to_export_in_every_size(report):
    failed = [c["name"] for c in report["checks"] if c["gate"] and not c["passed"]]
    assert not failed, failed
    assert (report["status"], report["error_count"], report["profile"]) == ("ready", 0, "shirt_1078375")
    assert report["sizes_checked"] == list(SUM_AREA) and report["sizes_not_drafted"] == []
    assert report["optitex"] == "Optitex import not yet verified"


def test_each_size_total_is_checked_against_its_pds_number(report):
    checks = by_name(report)
    for size, total in SUM_AREA.items():
        check = checks[f"{size} SUM_AREA"]
        assert check["limit"] == f"3 % of {total} m2" and check["size"] == size
        assert check["source"]["kind"] == "pds"


def test_every_check_names_where_its_limit_comes_from(report):
    kinds = {check["source"]["kind"] for check in report["checks"]}
    assert kinds == {"pds", "setting"}  # no chart entries are confirmed for 1078375 yet
    assert all(check["source"]["ref"] for check in report["checks"])
    checks = by_name(report)
    assert checks["L FRT gap"]["piece"] == "FRT" and checks["L FRT HPS:SP"]["edge"] == "HPS:SP"


def test_allowances_and_notch_pairs_are_checked(report):
    checks = by_name(report)
    for size in SUM_AREA:
        assert checks[f"{size} FRT side_hem:FE_hem allowance"]["passed"]
    assert not checks["L shoulder_notch pair"]["gate"] and not checks["L crown_notch pair"]["gate"]


def test_the_from_block_list_names_every_input_in_every_size(report):
    inputs = installed().get("shirt_1078375").required
    assert [item["input"] for item in report["from_block"]] == sorted(inputs)
    assert all(item["sizes"] == list(SUM_AREA) for item in report["from_block"])


def test_sizes_not_yet_graded_are_listed(tmp_path):
    _, project = shirt_project(tmp_path, graded=False)
    report = accuracy_report(project)
    assert report["sizes_checked"] == ["L"] and report["sizes_not_drafted"] == GRADED
    assert report["status"] == "ready"


def test_a_profile_without_a_reference_is_reported_not_checked(tmp_path):
    client, url = _ready(tmp_path)
    client.post(f"{url}/patterns/generate", json={"size": "L"})
    report = client.get(f"{url}/accuracy").json()
    assert (report["status"], report["profile"], report["checks"]) == ("no_reference", "demo_v1", [])
    assert report["error_count"] == 0


def test_no_current_pattern_has_no_report(tmp_path):
    service = Service(Repository(f"sqlite:///{tmp_path}/x.db"))
    with pytest.raises(NotReady, match="Generate a current pattern"):
        accuracy_report(service.create("Empty", True))
