"""T141c: a named-block project keeps every graded size in its stored style, which the Optitex export reads.

ShirtBlock becomes selectable from a chart in T142; until then this test supplies the block's own
PDS-derived graded measurements in place of the chart lookup. Everything else is the real path.
"""
import io
import zipfile

import pytest

from app.application import pattern_workflow
from app.application.cad.style_from_block import style_from_block
from app.application.cad.style_service import StyleService
from app.application.errors import NotReady
from app.application.grading.aama_export import graded_aama
from app.application.project_style import project_style
from app.application.service import Service
from app.domain.blocks.registry import installed
from app.infrastructure.repository import Repository
from app.infrastructure.style_repository import StyleRepository

BLOCK = "shirt_1078375"
SIZES = ["S", "M", "XL", "XXL", "3XL"]
EXPORT_FILES = {"base.dxf", "grade_rules.rul", "all_sizes.dxf"}


@pytest.fixture
def named(tmp_path, monkeypatch):
    block = installed().get(BLOCK)
    monkeypatch.setattr(pattern_workflow, "requirements", lambda p, size: {"ready": True, "blockers": []})
    monkeypatch.setattr(pattern_workflow, "drafting_values", lambda p, size: dict(block.graded_measurements(size)))
    service = Service(Repository(f"sqlite:///{tmp_path}/named.db"))
    project = service.create("Named shirt", True)
    project["resolutions"] = {"units": "cm", "review": "confirmed", "profile": BLOCK, "placket": "workbook"}
    service.generate(project, "L")
    return service, service.repo.get(project["id"])


def test_generate_stores_the_drafted_base_size(named):
    style = project_style(named[1])
    assert style.base_size == "L" and list(style.geometry) == ["L"]
    assert style.view("L") == style_from_block(BLOCK).view("L")


def test_grading_fills_every_size_with_the_blocks_own_drafts(named):
    service, project = named
    service.grade(project, SIZES)
    style = project_style(service.repo.get(project["id"]))
    reference = style_from_block(BLOCK)
    assert set(style.geometry) == set(reference.sizes)
    assert all(style.view(size) == reference.view(size) for size in reference.sizes)
    assert style.allowances == reference.allowances


def test_the_graded_project_exports_base_rules_and_all_sizes(named):
    service, project = named
    service.grade(project, SIZES)
    styles = StyleService(StyleRepository(service.repo.engine), service.repo)
    record = styles.create_from_project(project["id"])
    with zipfile.ZipFile(io.BytesIO(graded_aama(record.style, "mm"))) as archive:
        assert set(archive.namelist()) == EXPORT_FILES


def test_an_ungraded_project_cannot_export_grade_rules(named):
    with pytest.raises(ValueError, match="Grade rules need every size drafted; missing S, M, XL, XXL, 3XL"):
        graded_aama(project_style(named[1]), "mm")


def test_regrading_replaces_the_earlier_grades(named):
    service, project = named
    service.grade(project, SIZES)
    service.grade(service.repo.get(project["id"]), ["M"])
    assert sorted(project_style(service.repo.get(project["id"])).geometry) == ["L", "M"]


def test_grading_without_a_drafted_base_is_refused(named):
    service, project = named
    service.clear_pattern(project)
    with pytest.raises(NotReady, match="Generate a current pattern before grading"):
        service.grade(service.repo.get(project["id"]), ["M"])


def test_grading_no_sizes_leaves_only_the_base(named):
    service, project = named
    service.grade(project, SIZES)
    service.grade(service.repo.get(project["id"]), [])
    assert list(project_style(service.repo.get(project["id"])).geometry) == ["L"]
