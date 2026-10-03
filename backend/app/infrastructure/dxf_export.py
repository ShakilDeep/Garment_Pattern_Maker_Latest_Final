"""AutoCAD DXF export: every piece at true 1:1 scale, with $INSUNITS naming the drawing unit.

Each piece is a BLOCK (cut line, sew line, grainline, notches, label) inserted at the same strip offset the SVG
uses. The drawing shows the same shapes as the app's Pattern Preview: a paired piece (the Sleeve) is one BLOCK
inserted twice. Model coordinates are cm with y down; DXF is y up, so y is negated (pieces read upright in AutoCAD).
A 10 cm CALIBRATION square lets the user check scale with DIST.
"""
from io import StringIO

import ezdxf
from ezdxf import units as dxf_units

from app.domain.units import from_cm
from app.infrastructure.piece_layout import STRIP_WIDTH, TOP, drawn_pieces, strip_layout

INSUNITS = {"cm": dxf_units.CM, "mm": dxf_units.MM, "inch": dxf_units.IN}
LAYERS = {"CUT": 7, "SEW": 8, "GRAIN": 3, "NOTCH": 1, "LABEL": 5, "CALIBRATION": 6}
DECIMAL_UNITS = 2  # $LUNITS: decimal
DISPLAY_PRECISION = 4  # $LUPREC: DIST shows 4 decimals (0.0001 mm / cm / inch)
TEXT_HEIGHT_CM = 2.5
CALIBRATION_SIDE_CM = 10
CALIBRATION_GAP_CM = 10


def export_dxf(pattern: dict, unit: str) -> bytes:
    if unit not in INSUNITS:
        raise ValueError(f"Unsupported unit {unit!r}; use cm, mm or inch")
    doc = ezdxf.new("R2010")
    doc.units = INSUNITS[unit]
    doc.header["$MEASUREMENT"] = 0 if unit == "inch" else 1
    doc.header["$LUNITS"] = DECIMAL_UNITS
    doc.header["$LUPREC"] = DISPLAY_PRECISION
    for name, color in LAYERS.items():
        doc.layers.add(name, color=color)
    msp = doc.modelspace()

    def at(x: float, y: float) -> tuple[float, float]:
        return from_cm(x, unit), -from_cm(y, unit)

    placed, _ = strip_layout(drawn_pieces(pattern["pieces"]))
    for piece, x, y in placed:
        if piece["id"] not in doc.blocks:
            _piece_block(doc, piece, pattern["size"], at)
        msp.add_blockref(piece["id"], at(x, y))
    _calibration_square(msp, at)
    stream = StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def _piece_block(doc, piece: dict, size: str, at) -> None:
    block = doc.blocks.new(name=piece["id"])
    cut = piece.get("cut_points", piece["points"])
    block.add_lwpolyline([at(*p) for p in cut], close=True, dxfattribs={"layer": "CUT"})
    if "cut_points" in piece:
        block.add_lwpolyline([at(*p) for p in piece["points"]], close=True, dxfattribs={"layer": "SEW"})
    start, end = piece["grainline"]
    block.add_line(at(*start), at(*end), dxfattribs={"layer": "GRAIN"})
    for notch in piece.get("notches", []):
        block.add_point(at(*notch), dxfattribs={"layer": "NOTCH"})
    label = f'{piece["name"]} / {size} / Cut {piece["quantity"]}'
    block.add_text(label, height=_scaled_height(at), dxfattribs={"layer": "LABEL"}).set_placement(at(0, -2))


def _calibration_square(msp, at) -> None:
    left, top = STRIP_WIDTH + CALIBRATION_GAP_CM, TOP
    side = CALIBRATION_SIDE_CM
    corners = [(left, top), (left + side, top), (left + side, top + side), (left, top + side)]
    msp.add_lwpolyline([at(*c) for c in corners], close=True, dxfattribs={"layer": "CALIBRATION"})
    msp.add_text("10 cm test square", height=_scaled_height(at),
                 dxfattribs={"layer": "CALIBRATION"}).set_placement(at(left, top - 2))


def _scaled_height(at) -> float:
    return at(TEXT_HEIGHT_CM, 0)[0]
