"""DXF-AAMA/ASTM D6673 reader: R12 drawing -> InterchangeStyle in cm on the 1e-6 model grid.

Only what the file states is read; a file this reader cannot interpret faithfully raises ValueError
naming what is missing, rather than returning a partial pattern.
"""
from io import StringIO

import ezdxf

from app.domain.interchange import InterchangePiece, InterchangeStyle, Point
from app.infrastructure.aama.layers import AAMA_VERSION, MODEL_DECIMALS, AamaLayer, cm_per_unit

R12 = "AC1009"


def read_aama(data: bytes) -> InterchangeStyle:
    try:
        doc = ezdxf.read(StringIO(data.decode("utf-8")))
    except (ezdxf.DXFError, UnicodeDecodeError):
        raise ValueError("The file is not a readable DXF") from None
    if doc.dxfversion != R12:
        raise ValueError(f"A DXF-AAMA file must be DXF R12, not {doc.dxfversion}")
    header = _key_values(doc.modelspace())
    if AAMA_VERSION.split(":")[0] not in header:
        raise ValueError("The DXF has no AAMA header (ANSI/AAMA VERSION)")
    if "UNITS" not in header:
        raise ValueError("The AAMA header has no UNITS (METRIC or ENGLISH)")
    scale = cm_per_unit(header["UNITS"])
    pieces = tuple(_piece(doc.blocks[insert.dxf.name], scale)
                   for insert in doc.modelspace().query("INSERT"))
    return InterchangeStyle(name=header.get("PRODUCT", ""), sample_size=header.get("SAMPLE SIZE", ""),
                            pieces=pieces, grade_rule_table=header.get("GRADE RULE TABLE"))


def _key_values(layout) -> dict[str, str]:
    pairs = (text.dxf.text.split(":", 1) for text in layout.query(f'TEXT[layer=="{AamaLayer.CUT.dxf}"]'))
    return {key.strip(): value.strip() for key, value in (pair for pair in pairs if len(pair) == 2)}


def _piece(block, scale: float) -> InterchangePiece:
    text = _key_values(block)
    name = text.get("Piece Name", block.name)

    def cm(location) -> Point:
        return round(location[0] * scale, MODEL_DECIMALS) + 0.0, round(location[1] * scale, MODEL_DECIMALS) + 0.0

    def rings(layer: AamaLayer) -> tuple[tuple[Point, ...], ...]:
        return tuple(tuple(cm(v.dxf.location) for v in line.vertices)
                     for line in block.query(f'POLYLINE[layer=="{layer.dxf}"]'))

    def segment(layer: AamaLayer):
        lines = block.query(f'LINE[layer=="{layer.dxf}"]')
        return (cm(lines[0].dxf.start), cm(lines[0].dxf.end)) if len(lines) else None

    cut = rings(AamaLayer.CUT)
    if not cut:
        raise ValueError(f"Piece {name} has no layer-1 cut line")
    notch_layer = f'[layer=="{AamaLayer.NOTCH.dxf}"]'
    notches = tuple((cm(p.dxf.location),) for p in block.query("POINT" + notch_layer)) + tuple(
        (cm(line.dxf.start), cm(line.dxf.end)) for line in block.query("LINE" + notch_layer))
    annotations = tuple(t.dxf.text for t in block.query(f'TEXT[layer=="{AamaLayer.ANNOTATION.dxf}"]'))
    return InterchangePiece(
        name=name, size=text.get("Size", ""), quantity=int(text.get("Quantity", "1")), cut=cut[0],
        sew=rings(AamaLayer.SEW), mirror=segment(AamaLayer.MIRROR), notches=notches,
        grain=segment(AamaLayer.GRAIN), category=text.get("Category"), annotations=annotations)
