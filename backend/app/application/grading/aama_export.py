"""Graded DXF-AAMA export (T131, build plan M4): base DXF + .RUL, and every size drawn, in one zip.

- ``base.dxf``: the base size, each cut-line corner of a named point carrying its grade rule number
  (ASTM D6673: text "# <ID>" at the point, layer 5); points between are graded proportionally by the CAD.
- ``grade_rules.rul``: each rule's move of that corner from the base size, size by size.
- ``all_sizes.dxf``: every size's pieces drawn exactly, for checking the grade or nesting without rules.
Whether Optitex imports them as intended is the M4 manual gate, recorded only once someone with Optitex
has opened the files.
"""
import io
import zipfile

from app.application.grading.grade_rules import StyleRules, require_graded, rules_from_positions
from app.domain.interchange import InterchangeStyle
from app.domain.pattern.cut_corners import cut_corners
from app.domain.pattern.style import Style
from app.infrastructure.aama.from_style import piece_to_interchange
from app.infrastructure.aama.layers import unit_scale
from app.infrastructure.aama.rul import write_rul
from app.infrastructure.aama.writer import write_aama


def corner_rules(style: Style) -> StyleRules:
    """Grade rules of every named point's cut-line corner, matched by name across sizes."""
    require_graded(style)
    missing = [str(piece_id) for piece_id in style.piece_ids if piece_id not in style.allowances]
    if missing:
        raise ValueError(f"A graded export needs every piece's seam allowance; missing {', '.join(missing)}")
    sizes = {size: {(piece.id, name): corner for piece in style.view(size)
                    for name, corner in cut_corners(piece, style.allowances[piece.id]).items()}
             for size in style.sizes}
    return rules_from_positions(style.name, sizes, style.base_size)


def _base(style: Style, rules: StyleRules) -> InterchangeStyle:
    pieces = []
    for piece in style.view(style.base_size):
        allowance = style.allowances[piece.id]
        points = tuple(((corner.x, corner.y), rules.by_point[(piece.id, name)])
                       for name, corner in cut_corners(piece, allowance).items())
        pieces.append(piece_to_interchange(piece, style.base_size, allowance, points))
    return InterchangeStyle(style.name, style.base_size, tuple(pieces), grade_rule_table=rules.table.name)


def _all_sizes(style: Style) -> InterchangeStyle:
    pieces = tuple(piece_to_interchange(piece, size, style.allowances[piece.id])
                   for size in style.sizes for piece in style.view(size))
    return InterchangeStyle(style.name, style.base_size, pieces)


def graded_aama(style: Style, unit: str) -> bytes:
    unit_scale(unit)  # refuse an unknown unit before any drafting work
    rules = corner_rules(style)
    files: dict[str, bytes | str] = {
        "base.dxf": write_aama(_base(style, rules), unit),
        "grade_rules.rul": write_rul(rules.table, unit),
        "all_sizes.dxf": write_aama(_all_sizes(style), unit),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()
