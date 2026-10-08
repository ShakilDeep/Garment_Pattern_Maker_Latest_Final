"""Facade: read an Optitex .PDS file's XML section into a ``ReferenceStyle`` (read-only; PDS is never written)."""
from app.domain.reference import PieceOutline, ReferencePiece, ReferenceStyle
from app.infrastructure.pds.metadata import piece_fields, piece_geometry, size_table, text
from app.infrastructure.pds.outline_geometry import bounds_cm
from app.infrastructure.pds.svg_outlines import piece_outlines
from app.infrastructure.pds.xml_section import style_element

ORDER_TOLERANCE_CM = 0.5
SVG_PATH = "MARKER/VIEW/svg"


def _check_order(piece: ReferencePiece, base_size: str) -> None:
    """The SVG has no piece ids, so each outline must match its PIECE's base-size bounding box."""
    base = piece.geometry.get(base_size)
    if base is None:
        raise ValueError(f"PDS piece {piece.name} has no {base_size} geometry")
    min_x, min_y, max_x, max_y = bounds_cm(piece.outline)
    if (abs(max_x - min_x - base.size_x_cm) > ORDER_TOLERANCE_CM
            or abs(max_y - min_y - base.size_y_cm) > ORDER_TOLERANCE_CM):
        raise ValueError(f"PDS SVG outline order does not match the PIECE list at {piece.name}")


def read_pds(data: bytes) -> ReferenceStyle:
    style = style_element(data)
    sizes, base_size, totals = size_table(style)
    elements = style.findall("PIECE")
    fields = [piece_fields(element) for element in elements]
    svg = style.find(SVG_PATH)
    if svg is None:
        raise ValueError(f"PDS field missing: {SVG_PATH}")
    outlines: list[PieceOutline] = list(piece_outlines(svg, [field["on_fold"] for field in fields]))
    pieces = tuple(
        ReferencePiece(**field, geometry=piece_geometry(element), outline=outline)
        for field, element, outline in zip(fields, elements, outlines, strict=True)
    )
    for piece in pieces:
        _check_order(piece, base_size)
    return ReferenceStyle(
        name=text(style, "NAME"),
        optitex_version=text(style, "OPTITEX"),
        sizes=sizes,
        base_size=base_size,
        totals=totals,
        pieces=pieces,
    )
