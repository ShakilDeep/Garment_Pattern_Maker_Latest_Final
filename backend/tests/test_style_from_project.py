"""P1-07: a style is made only from a project's current pattern and the grades drafted from it."""

from copy import deepcopy

import pytest
from test_cad_legacy import generated  # noqa: F401 - module fixture: a project with a generated L pattern

from app.application.cad.style_from_project import style_from_project
from app.application.errors import NotReady
from app.domain.pattern.ids import PieceId


def _graded(pattern, size, **changes):
    return {**deepcopy(pattern), "size": size, "graded_from": None, **changes}


def test_current_grades_become_sizes_and_others_are_left_out(generated):  # noqa: F811
    project = deepcopy(generated[1])
    pattern = project["pattern"]
    project["grades"] = [
        _graded(pattern, "M"),
        _graded(pattern, "XL", graded_from=pattern["id"]),
        _graded(pattern, "S", graded_from="an-older-version"),
        _graded(pattern, "XXL", stale=True),
    ]
    style = style_from_project(project)
    assert list(style.geometry) == ["M", "L", "XL"] and style.base_size == "L"
    assert style.sizes == ("S", "M", "L", "XL", "XXL", "3XL")
    width = pattern["seam_allowance"]
    assert {a.default_width for a in style.allowances.values()} == {width}
    assert set(style.allowances) == set(style.piece_ids) and PieceId("p0") not in style.piece_ids


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda p: p.update(archived=True), "archived"),
        (lambda p: p.update(pattern=None), "Generate a current pattern"),
        (lambda p: p["pattern"].update(stale=True), "Generate a current pattern"),
    ],
)
def test_projects_without_a_current_pattern_are_refused(generated, change, message):  # noqa: F811
    project = deepcopy(generated[1])
    change(project)
    with pytest.raises(NotReady, match=message):
        style_from_project(project)
