"""T142: a project chooses the client 1078375 block, accepts its reference values and drafts every size."""
import pytest

from app.application.cad.style_from_block import style_from_block
from app.application.project_style import project_style
from app.application.requirement_resolve import resolve
from app.application.requirements import requirements
from app.application.service import Service
from app.domain.blocks.registry import installed
from app.infrastructure.repository import Repository

BLOCK = "shirt_1078375"
ANSWERS = {"units": "cm", "review": "confirmed", "placket": "workbook", "profile": BLOCK}
SIZES = ["S", "M", "XL", "XXL", "3XL"]


@pytest.fixture
def chosen(tmp_path):
    service = Service(Repository(f"sqlite:///{tmp_path}/flow.db"))
    project = service.create("Client shirt", True)
    for key, value in ANSWERS.items():
        resolve(project, key, value)
    return service, project


def _blockers(project):
    return {item["key"] for item in requirements(project, "L")["blockers"]}


def test_choosing_the_block_asks_about_its_reference_values(chosen):
    item = next(i for i in requirements(chosen[1], "L")["items"] if i["key"] == "block_reference")
    assert item["options"] == ["accepted"] and item["blocking"] and item["status"] == "MISSING"
    assert "35 of 35" in item["why"] and "block_reference" in _blockers(chosen[1])
    assert not any(key.startswith("measurement:half_chest") for key in _blockers(chosen[1]))


def test_a_dict_profile_cannot_accept_block_reference_values(chosen):
    project = resolve(chosen[1], "profile", "shirt_v2")
    with pytest.raises(ValueError, match="Unsupported requirement resolution"):
        resolve(project, "block_reference", "accepted")


def test_accepted_reference_values_draft_and_grade_the_client_shirt(chosen):
    service, project = chosen
    resolve(project, "block_reference", "accepted")
    assert requirements(project, "L")["ready"]
    pattern = service.generate(project, "L")
    assert pattern["input_sources"] == dict.fromkeys(installed().get(BLOCK).required, "from_block")
    service.grade(project, SIZES)
    style, reference = project_style(service.repo.get(project["id"])), style_from_block(BLOCK)
    assert all(style.view(size) == reference.view(size) for size in reference.sizes)


def test_a_size_outside_the_reference_lists_every_input_as_missing(chosen):
    project = resolve(chosen[1], "block_reference", "accepted")
    keys = {item["key"] for item in requirements(project, "XS")["blockers"]}
    assert {f"measurement:{name}" for name in installed().get(BLOCK).required} <= keys
