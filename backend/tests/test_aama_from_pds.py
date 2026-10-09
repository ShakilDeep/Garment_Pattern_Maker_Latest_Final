"""T127: fold pieces export their first half; a notch drawn on the second half is mirrored, not lost."""
from types import MappingProxyType

from app.domain.reference import PieceOutline, ReferencePiece, ReferenceStyle
from app.infrastructure.aama.from_pds import GRAIN_SPAN, pds_to_interchange

LEFT = ((-10.0, 0.0), (0.0, 0.0), (0.0, 20.0), (-10.0, 20.0))
RIGHT = ((0.0, 0.0), (10.0, 0.0), (10.0, 20.0), (0.0, 20.0))
SEW_LEFT = ((-9.0, 1.0), (0.0, 1.0), (0.0, 19.0), (-9.0, 19.0))
SEW_RIGHT = ((0.0, 1.0), (9.0, 1.0), (9.0, 19.0), (0.0, 19.0))
ON_LEFT = ((-9.0, 10.0), (-8.3, 10.0))
ON_RIGHT = ((9.0, 5.0), (8.3, 5.0))


def _style(on_fold=True):
    outline = PieceOutline(cut=(LEFT, RIGHT) if on_fold else (LEFT,),
                           sew=(SEW_LEFT, SEW_RIGHT) if on_fold else (SEW_LEFT,),
                           folds=(((0.0, 0.0), (0.0, 20.0)),) if on_fold else (),
                           notches=(ON_LEFT, ON_RIGHT) if on_fold else (ON_LEFT,))
    piece = ReferencePiece(name="Back", code="", quantity=1, on_fold=on_fold, rotation_deg=0.0, opposite="None",
                           geometry=MappingProxyType({}), outline=outline)
    return ReferenceStyle(name="S1", optitex_version="21", sizes=("M",), base_size="M",
                          totals=MappingProxyType({}), pieces=(piece,))


def test_a_fold_piece_keeps_half_one_and_mirrors_the_second_halfs_notch():
    piece = pds_to_interchange(_style()).pieces[0]
    assert (piece.cut, piece.sew, piece.mirror) == (LEFT, (SEW_LEFT,), ((0.0, 0.0), (0.0, 20.0)))
    assert piece.notches == (ON_LEFT, ((-9.0, 5.0), (-8.3, 5.0)))


def test_a_piece_not_on_the_fold_passes_through_unchanged():
    piece = pds_to_interchange(_style(on_fold=False)).pieces[0]
    assert (piece.cut, piece.sew, piece.mirror, piece.notches) == (LEFT, (SEW_LEFT,), None, (ON_LEFT,))


def test_grain_runs_along_x_through_the_centre_and_is_marked_assumed():
    piece = pds_to_interchange(_style()).pieces[0]
    assert piece.grain == ((-5.0 - 5.0 * GRAIN_SPAN, 10.0), (-5.0 + 5.0 * GRAIN_SPAN, 10.0))
    assert piece.annotations and "assumed" in piece.annotations[0]
