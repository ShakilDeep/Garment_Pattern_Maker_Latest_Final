"""T141a: a project keeps one stored V6 style in step with its pattern on every save."""
from copy import deepcopy

import pytest

from app.api.models.project import Project
from app.application.cad.style_from_project import style_from_project
from app.application.cad.style_service import StyleService
from app.application.commands import execute
from app.application.project_style import project_style
from app.application.service import Service
from app.infrastructure.repository import Repository
from app.infrastructure.style_repository import StyleRepository

RESOLVED = {"units": "cm", "review": "confirmed", "profile": "demo_v1", "placket": "workbook"}


@pytest.fixture
def service(tmp_path):
    return Service(Repository(f"sqlite:///{tmp_path}/style.db"))


@pytest.fixture
def generated(service):
    project = service.create("Project style", True)
    project["resolutions"] = dict(RESOLVED)
    service.generate(project, "L")
    return service.repo.get(project["id"])


def _same_geometry(stored, expected):
    return (stored.sizes, stored.base_size, list(stored.geometry), stored.allowances) == (
        expected.sizes, expected.base_size, list(expected.geometry), expected.allowances
    ) and all(stored.view(size) == expected.view(size) for size in expected.geometry)


def test_generate_stores_the_style_of_the_current_pattern(generated):
    stored = project_style(generated)
    assert stored is not None and _same_geometry(stored, style_from_project(generated))


def test_grading_adds_every_graded_size(service, generated):
    service.grade(generated, ["S", "M"])
    project = service.repo.get(generated["id"])
    assert list(project_style(project).geometry) == ["S", "M", "L"]


def test_a_v5_edit_updates_the_stored_style(service, generated):
    before = project_style(generated)
    edited = execute(service, generated, "allowance", 1.0)
    after = project_style(service.repo.get(edited["id"]))
    assert {a.default_width for a in after.allowances.values()} == {1.0} != {
        a.default_width for a in before.allowances.values()}


@pytest.mark.parametrize("change", ["clear", "stale"])
def test_no_current_pattern_means_no_stored_style(service, generated, change):
    if change == "clear":
        service.clear_pattern(generated)
    else:
        service.invalidate(generated)
        service.repo.save(generated, "measurements_changed")
    assert project_style(service.repo.get(generated["id"])) is None


def test_cad_copies_come_from_the_stored_style_each_with_its_own_id(service, generated):
    styles = StyleService(StyleRepository(service.repo.engine), service.repo)
    first, second = (styles.create_from_project(generated["id"]).style for _ in range(2))
    assert first.id != second.id and _same_geometry(first, project_style(generated))


def test_the_style_text_never_reaches_the_api(generated):
    assert generated["style"] and "style" not in Project.model_validate(generated).model_dump()


def test_a_corrupt_stored_style_is_an_error_not_silently_ignored(generated):
    broken = {**deepcopy(generated), "style": "{not json"}
    with pytest.raises(ValueError):
        project_style(broken)
