"""T131 (build plan M4): graded 1078375 export: base DXF-AAMA + .RUL and an all-sizes DXF, read back."""
import io
import zipfile

import ezdxf
import pytest

from app.application.cad.style_from_block import style_from_block
from app.application.grading.aama_export import graded_aama
from app.domain.pattern.cut_corners import cut_corners
from app.domain.pattern.measure import ring_area
from app.infrastructure.aama.reader import read_aama
from app.infrastructure.aama.rul import read_rul
from app.infrastructure.piece_validity import check_cut_geometry

ROUND_TRIP_CM = 0.05  # build plan: re-read DXF equals internal geometry within 0.05 cm
AREA_SHARE = 0.005


@pytest.fixture(scope="module")
def style():
    return style_from_block("shirt_1078375")


@pytest.fixture(scope="module")
def files(style):
    archive = zipfile.ZipFile(io.BytesIO(graded_aama(style, "mm")))
    return {name: archive.read(name) for name in archive.namelist()}


def test_the_archive_holds_the_base_dxf_the_rul_and_the_all_sizes_dxf(files):
    assert sorted(files) == ["all_sizes.dxf", "base.dxf", "grade_rules.rul"]


def test_the_base_dxf_has_the_aama_layers_and_names_its_rule_table(files):
    doc = ezdxf.read(io.StringIO(files["base.dxf"].decode()))
    layers = {entity.dxf.layer for block in doc.blocks if block.name.startswith("PIECE") for entity in block}
    assert {"1", "2", "3", "4", "5", "6", "7", "14"} <= layers
    style = read_aama(files["base.dxf"])
    assert style.sample_size == "L" and style.grade_rule_table == read_rul(files["grade_rules.rul"].decode()).name
    assert [p.name for p in style.pieces] == ["FRT", "back", "back YK", "CLR", "BND TOP", "BND IN", "Sleeve"]


def test_every_grade_point_plus_its_rule_lands_on_that_size_s_cut_corner(files, style):
    table = read_rul(files["grade_rules.rul"].decode())
    assert table.sizes == style.sizes and table.sample_size == "L"
    base = {p.name: p for p in read_aama(files["base.dxf"]).pieces}
    for size_index, size in enumerate(style.sizes):
        for piece in style.view(size):
            corners = list(cut_corners(piece, style.allowances[piece.id]).values())
            exported = base[piece.name].grade_points
            assert len(exported) == len(corners), piece.name
            for ((x, y), rule), corner in zip(exported, corners, strict=True):
                dx, dy = table.rules[rule - 1][size_index]
                assert abs(x + dx - corner.x) <= ROUND_TRIP_CM and abs(y + dy - corner.y) <= ROUND_TRIP_CM


def test_the_all_sizes_dxf_has_every_size_s_cut_lines(files, style):
    pieces = read_aama(files["all_sizes.dxf"]).pieces
    assert len(pieces) == 7 * len(style.sizes)
    for read_back, drafted in zip(pieces, (p for size in style.sizes for p in style.view(size)), strict=True):
        area = ring_area(check_cut_geometry(drafted, style.allowances[drafted.id]))
        exported = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(read_back.cut, (*read_back.cut[1:],
                                                                                    read_back.cut[0])))) / 2
        assert exported == pytest.approx(area, rel=AREA_SHARE), (read_back.size, read_back.name)


def test_a_bad_unit_or_an_ungraded_style_is_refused(style):
    from app.domain.pattern.style import Style

    with pytest.raises(ValueError, match="Unsupported AAMA unit 'cm'"):
        graded_aama(style, "cm")
    with pytest.raises(ValueError, match="Grade rules need every size drafted"):
        graded_aama(Style(style.id, style.name, style.sizes, "L", {"L": style.geometry["L"]}), "mm")
    with pytest.raises(ValueError, match="needs every piece's seam allowance; missing FRT, back"):
        graded_aama(Style(style.id, style.name, style.sizes, "L", style.geometry), "mm")
