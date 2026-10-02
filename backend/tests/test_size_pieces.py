"""P1-05: SizePieces and the Style aggregate are immutable; a SizePieces has one source with matching ids."""

import pytest
from test_style import _pieces, _style

from app.domain.pattern.ids import PieceId
from app.domain.pattern.size_pieces import SizePieces


def test_size_pieces_and_styles_cannot_be_changed_in_place():
    style = _style()
    with pytest.raises(AttributeError):
        style.geometry["4½"].piece_ids = (PieceId("other"),)  # type: ignore[misc]
    with pytest.raises(TypeError):
        style.geometry["4"] = SizePieces.from_pieces(())  # type: ignore[index]
    with pytest.raises(TypeError, match="unhashable"):
        hash(style)


def test_size_pieces_needs_exactly_one_source_and_matching_ids():
    with pytest.raises(ValueError, match="either pieces or their JSON text"):
        SizePieces(None, None, ())
    with pytest.raises(ValueError, match="ids must be the ids of its pieces"):
        SizePieces(_pieces("back"), None, (PieceId("front"),))
