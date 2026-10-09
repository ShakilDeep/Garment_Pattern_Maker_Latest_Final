"""T127 (M2): the PDS base outlines export as DXF-AAMA (R12) and read back within 0.5 % of each PDS area."""
from io import StringIO

import ezdxf
import pytest

from app.infrastructure.aama.from_pds import ASSUMED_GRAIN, pds_to_interchange
from app.infrastructure.aama.geometry import piece_area_m2
from app.infrastructure.aama.reader import read_aama
from app.infrastructure.aama.writer import write_aama

AREA_TOLERANCE = 0.005  # build plan M2: within 0.5 %
STYLES = ("1078375", "1074664")
REQUIRED_LAYERS = {"1", "4", "6", "7", "14"}
NOTCHES = {"back YK": 1, "Sleeve": 1, "PKT-IN": 2, "FACING": 2}


@pytest.fixture(scope="module")
def exported(pds_styles):
    return {key: write_aama(pds_to_interchange(style), "mm") for key, style in pds_styles.items()}


def _layers_in_blocks(data: bytes) -> set[str]:
    doc = ezdxf.read(StringIO(data.decode("utf-8")))
    assert doc.dxfversion == "AC1009"  # R12, as AAMA readers expect
    names = {insert.dxf.name for insert in doc.modelspace().query("INSERT")}
    return {entity.dxf.layer for name in names for entity in doc.blocks[name]}


def test_the_aama_layers_of_the_build_plan_are_present(exported):
    layers = set().union(*(_layers_in_blocks(data) for data in exported.values()))
    assert REQUIRED_LAYERS <= layers


@pytest.mark.parametrize("style_number", STYLES)
def test_every_piece_area_is_within_half_a_percent_of_the_pds_area(pds_styles, exported, style_number):
    source, read = pds_styles[style_number], read_aama(exported[style_number])
    assert [piece.name for piece in read.pieces] == [piece.name for piece in source.pieces]
    for original, piece in zip(source.pieces, read.pieces, strict=True):
        expected = original.geometry[source.base_size].area_m2
        assert piece_area_m2(piece) == pytest.approx(expected, rel=AREA_TOLERANCE), piece.name


@pytest.mark.parametrize("style_number", STYLES)
def test_piece_text_and_marks_round_trip(pds_styles, exported, style_number):
    source, read = pds_styles[style_number], read_aama(exported[style_number])
    assert (read.name, read.sample_size, read.grade_rule_table) == (source.name, source.base_size, None)
    for original, piece in zip(source.pieces, read.pieces, strict=True):
        assert (piece.quantity, piece.size) == (original.quantity, source.base_size)
        assert (piece.mirror is not None) == original.on_fold, piece.name
        assert piece.grain is not None and ASSUMED_GRAIN in piece.annotations, piece.name
        assert len(piece.sew) == (1 if original.outline.sew else 0), piece.name
        assert len(piece.notches) == NOTCHES.get(piece.name, 0), piece.name


@pytest.mark.parametrize("style_number", STYLES)
def test_metric_files_are_in_millimetres_and_exact(pds_styles, exported, style_number):
    source, read = pds_styles[style_number], read_aama(exported[style_number])
    assert "UNITS: METRIC" in exported[style_number].decode()
    for original, piece in zip(source.pieces, read.pieces, strict=True):
        flat = [c for point in piece.cut for c in point]
        assert flat == pytest.approx([c for point in original.outline.cut[0] for c in point], abs=1e-6)


@pytest.mark.parametrize("style_number", STYLES)
def test_every_notch_starts_on_its_exported_sew_line_as_in_the_pds(exported, style_number):
    from app.infrastructure.aama.geometry import distance_to_ring

    for piece in read_aama(exported[style_number]).pieces:  # PDS notches: 0.7 cm slits from the sew line
        for notch in piece.notches:
            assert min(distance_to_ring(point, ring) for ring in piece.sew for point in notch) <= 0.05, piece.name
