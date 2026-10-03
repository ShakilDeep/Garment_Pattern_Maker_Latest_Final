"""Shared strip layout (cm) for the SVG and DXF exports; the DXF lays out drawn_pieces() to match the preview."""

STRIP_WIDTH = 160
MARGIN = 5
TOP = 12
PIECE_GAP = 8
ROW_GAP = 12
# The Pattern Preview (frontend/src/PatternCanvas.tsx) draws these pieces twice; the DXF export matches it.
PAIRED_IN_PREVIEW = frozenset({"Sleeve"})


def drawn_pieces(pieces: list[dict]) -> list[dict]:
    """The shapes the preview draws, in order: each paired piece is repeated right after itself."""
    return [copy for piece in pieces for copy in [piece] * (2 if piece["name"] in PAIRED_IN_PREVIEW else 1)]


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
