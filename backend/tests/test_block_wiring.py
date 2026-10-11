"""T128: the app drafts through the block registry; the profile choices are the installed blocks."""
import pytest

from app.application.pattern_workflow import build
from app.application.requirement_resolve import resolve
from app.application.requirements import requirements
from app.application.service import Service
from app.domain.blocks.registry import installed
from app.infrastructure.repository import Repository

ANSWERS = {"units": "cm", "profile": "demo_v1", "review": "confirmed", "placket": "workbook"}


@pytest.fixture(scope="module")
def ready(tmp_path_factory):
    service = Service(Repository(f"sqlite:///{tmp_path_factory.mktemp('blocks')}/b.db"))
    project = service.create("Blocks", demo=True)
    for key, value in ANSWERS.items():
        resolve(project, key, value)
    return project


def test_the_profile_requirement_offers_only_blocks_a_v5_project_can_draft(ready):
    item = next(i for i in requirements(ready, "L")["items"] if i["key"] == "profile")
    assert item["options"] == list(installed().project_ids()) == ["demo_v1", "shirt_v2"]


def test_a_named_v6_block_cannot_be_a_project_profile(ready):
    with pytest.raises(ValueError, match="Unsupported requirement resolution"):
        resolve(dict(ready, resolutions=dict(ready["resolutions"])), "profile", "shirt_1078375")


def test_resolving_an_uninstalled_profile_is_refused(ready):
    with pytest.raises(ValueError, match="Unsupported requirement resolution"):
        resolve(dict(ready, resolutions=dict(ready["resolutions"])), "profile", "tee_v9")


def test_a_project_drafts_with_its_block_and_valid_style_options(ready):
    pattern = build(dict(ready, style_options={"yoke": "split"}), "L")
    assert pattern["profile_metadata"]["id"] == "demo_v1" and len(pattern["pieces"]) == 8


def test_a_style_option_the_block_cannot_make_is_refused(ready):
    with pytest.raises(ValueError, match="Style option yoke is fixed at split for block demo_v1"):
        build(dict(ready, style_options={"yoke": "none"}), "L")
