"""T146 (shirt): a graded 1078375 project exports base DXF-AAMA + .RUL + all-sizes DXF + README (spec §7 Export)."""
import io
import zipfile
from hashlib import sha256

import ezdxf
import pytest
from fastapi.testclient import TestClient
from named_project import shirt_project

from app.api.main import create_app
from app.application.project_style import project_style
from app.domain.pattern.cut_corners import cut_corners
from app.infrastructure.aama.reader import read_aama
from app.infrastructure.aama.rul import read_rul
from app.infrastructure.piece_validity import check_cut_geometry

RUL_CM, DXF_CM = 0.01, 0.05  # spec §7: .RUL deltas within 0.01 cm, DXF re-read within 0.05 cm
LAYERS = {"1", "4", "5", "6", "7", "14"}


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    path = tmp_path_factory.mktemp("aama")
    _, project = shirt_project(path)
    client = TestClient(create_app(f"sqlite:///{path}/named.db"))
    response = client.get(f"/api/v1/projects/{project['id']}/exports/aama-graded?unit=mm")
    assert response.status_code == 200, response.text
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    files = {name: archive.read(name) for name in archive.namelist()}
    return client, project, response, files


def test_the_zip_holds_the_three_optitex_files_and_a_readme(exported):
    _, _, response, files = exported
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"].endswith('filename="shirt_1078375_graded_aama.zip"')
    assert sorted(files) == ["README.txt", "all_sizes.dxf", "base.dxf", "grade_rules.rul"]


def test_the_readme_says_the_import_is_not_yet_verified(exported):
    readme = exported[3]["README.txt"].decode()
    for text in ("Optitex import not yet verified", "S, M, L, XL, XXL, 3XL", "Base size: L", "METRIC (mm)",
                 "Accuracy report: ready", "Q4", "Q10", "Q12"):
        assert text in readme, text


def test_the_export_is_recorded_with_its_hash(exported):
    client, project, response, _ = exported
    record = client.get(f"/api/v1/projects/{project['id']}").json()["export_records"][-1]
    assert (record["kind"], record["size"], record["unit"]) == ("aama-graded", "L", "mm")
    assert record["sha256"] == sha256(response.content).hexdigest()


def test_the_base_dxf_has_the_spec_layers(exported):
    doc = ezdxf.read(io.StringIO(exported[3]["base.dxf"].decode()))
    layers = {entity.dxf.layer for block in doc.blocks if block.name.startswith("PIECE") for entity in block}
    assert LAYERS <= layers


def test_every_grade_point_plus_its_rul_delta_is_that_size_s_corner(exported):
    _, project, _, files = exported
    style, table = project_style(project), read_rul(files["grade_rules.rul"].decode())
    base = {p.name: p for p in read_aama(files["base.dxf"]).pieces}
    for index, size in enumerate(table.sizes):
        for piece in style.view(size):
            corners = cut_corners(piece, style.allowances[piece.id]).values()
            for ((x, y), rule), corner in zip(base[piece.name].grade_points, corners, strict=True):
                dx, dy = table.rules[rule - 1][index]
                assert max(abs(x + dx - corner.x), abs(y + dy - corner.y)) <= RUL_CM, (size, piece.name)


def test_the_all_sizes_dxf_re_reads_as_the_drafted_cut_lines(exported):
    _, project, _, files = exported
    style = project_style(project)
    pieces = iter(read_aama(files["all_sizes.dxf"]).pieces)
    for size in style.sizes:
        for piece in style.view(size):
            back, cut = next(pieces), check_cut_geometry(piece, style.allowances[piece.id])
            assert (back.name, back.size, len(back.cut)) == (piece.name, size, len(cut))
            assert max(max(abs(x - p.x), abs(y - p.y)) for (x, y), p in zip(back.cut, cut, strict=True)) <= DXF_CM
