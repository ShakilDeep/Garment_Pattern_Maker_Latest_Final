"""Shared strip layout (cm) so the SVG and DXF exports place every piece at the same offset."""

STRIP_WIDTH = 160
MARGIN = 5
TOP = 12
PIECE_GAP = 8
ROW_GAP = 12


def strip_layout(pieces: list[dict]) -> tuple[list[tuple[dict, float, float]], float]:
    """Each piece with its (x, y) offset, left to right in rows, plus the total strip height."""
    placed: list[tuple[dict, float, float]] = []
    x: float = MARGIN
    y: float = TOP
    row_h: float = 0
    for piece in pieces:
        if x + piece["width"] > STRIP_WIDTH:
            x, y, row_h = MARGIN, y + row_h + ROW_GAP, 0
        placed.append((piece, x, y))
        x += piece["width"] + PIECE_GAP
        row_h = max(row_h, piece["height"])
    return placed, y + row_h + PIECE_GAP
