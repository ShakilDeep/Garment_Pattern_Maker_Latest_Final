"""DXF-AAMA/ASTM D6673 writer: an R12 drawing with one BLOCK per piece on the numbered AAMA layers.

Coordinates are written exactly as given, only scaled from cm to the file unit (mm or inch). Pieces are
inserted left to right with a gap; inside its BLOCK every piece keeps its own coordinates.
"""
from io import StringIO

import ezdxf

from app.domain.interchange import InterchangePiece, InterchangeStyle, Point
from app.infrastructure.aama.corners import split_vertices
from app.infrastructure.aama.layers import AAMA_VERSION, AamaLayer, unit_scale

PIECE_GAP_CM = 5.0
TEXT_HEIGHT_CM = 1.0
TEXT_LINE_CM = 1.5


def write_aama(style: InterchangeStyle, unit: str) -> bytes:
    flag, scale = unit_scale(unit)
    doc = ezdxf.new("R12")
    for layer in AamaLayer:
        doc.layers.add(layer.dxf)
    msp = doc.modelspace()
    header = [AAMA_VERSION, f"PRODUCT: {style.name}", f"SAMPLE SIZE: {style.sample_size}", f"UNITS: {flag}"]
    if style.grade_rule_table:
        header.append(f"GRADE RULE TABLE: {style.grade_rule_table}")
    _texts(msp, header, AamaLayer.CUT, (0.0, -TEXT_LINE_CM), scale)
    offset = 0.0
    for number, piece in enumerate(style.pieces, start=1):
        name = f"PIECE{number}"
        _piece_block(doc.blocks.new(name=name), piece, style.name, scale)
        xs = [x for x, _ in piece.cut]
        msp.add_blockref(name, ((offset - min(xs)) * scale, 0.0))
        offset += max(xs) - min(xs) + PIECE_GAP_CM
    stream = StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def _piece_block(block, piece: InterchangePiece, style_name: str, scale: float) -> None:
    def at(point: Point) -> tuple[float, float]:
        return point[0] * scale, point[1] * scale

    def attrs(layer: AamaLayer) -> dict:
        return {"layer": layer.dxf}

    block.add_polyline2d([at(p) for p in piece.cut], close=True, dxfattribs=attrs(AamaLayer.CUT))
    turns, curves = split_vertices(piece.cut)
    for layer, points in ((AamaLayer.TURN, turns), (AamaLayer.CURVE, curves)):
        for point in points:
            block.add_point(at(point), dxfattribs=attrs(layer))
    for notch in piece.notches:
        if len(notch) == 1:
            block.add_point(at(notch[0]), dxfattribs=attrs(AamaLayer.NOTCH))
        else:
            block.add_line(at(notch[0]), at(notch[-1]), dxfattribs=attrs(AamaLayer.NOTCH))
    for layer, segment in ((AamaLayer.MIRROR, piece.mirror), (AamaLayer.GRAIN, piece.grain)):
        if segment is not None:
            block.add_line(at(segment[0]), at(segment[1]), dxfattribs=attrs(layer))
    for drill in piece.drills:
        block.add_point(at(drill), dxfattribs=attrs(AamaLayer.DRILL))
    for ring in piece.sew:
        block.add_polyline2d([at(p) for p in ring], close=True, dxfattribs=attrs(AamaLayer.SEW))
    lines = [f"Piece Name: {piece.name}", f"Size: {piece.size}", f"Quantity: {piece.quantity}",
             f"Style Name: {style_name}"] + ([f"Category: {piece.category}"] if piece.category else [])
    low = (min(x for x, _ in piece.cut), min(y for _, y in piece.cut))
    _texts(block, lines, AamaLayer.CUT, (low[0], low[1] - TEXT_LINE_CM), scale)
    _texts(block, list(piece.annotations), AamaLayer.ANNOTATION,
           (low[0], low[1] - TEXT_LINE_CM * (len(lines) + 1)), scale)
    for point, rule in piece.grade_points:  # ASTM D6673: "# <ID>" at the grade point, on layer 5
        block.add_text(f"# {rule}", height=TEXT_HEIGHT_CM * scale,
                       dxfattribs={"layer": AamaLayer.GRADE_REFERENCE.dxf}).set_placement(at(point))


def _texts(layout, lines: list[str], layer: AamaLayer, start: Point, scale: float) -> None:
    for index, line in enumerate(lines):
        position = (start[0] * scale, (start[1] - index * TEXT_LINE_CM) * scale)
        layout.add_text(line, height=TEXT_HEIGHT_CM * scale,
                        dxfattribs={"layer": layer.dxf}).set_placement(position)
