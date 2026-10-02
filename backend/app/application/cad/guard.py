"""Validation guard (CAD-07): every changed piece of a command result is checked before anything is saved.

Chain of Responsibility: each piece goes through the validators in order and stops at the first that refuses
it. A piece counts as changed when its Memento digest or its seam allowance differs from the state before the
command, so unchanged pieces are never re-checked. All refusals are reported together as GEOMETRY_INVALID.
"""

from collections.abc import Iterator, Sequence

from app.application.cad.validators import CutOutlineValidator, OutlineValidator, PieceValidator
from app.application.errors import GeometryInvalid
from app.domain.pattern.piece import Piece
from app.domain.pattern.style import Style


def _changed(before: Style | None, after: Style) -> Iterator[tuple[str, Piece]]:
    """Pieces whose Memento digest or seam allowance changed; only sizes holding one of them are decoded."""
    new_allowance = {
        piece for piece in after.piece_ids
        if before is None or before.allowances.get(piece) != after.allowances.get(piece)
    }
    for size, stored in after.geometry.items():
        previous = None if before is None else before.geometry.get(size)
        if previous is stored and not new_allowance:
            continue
        old = () if previous is None else previous.piece_texts().digests
        new = stored.piece_texts().digests
        changed = {
            index for index, piece in enumerate(stored.piece_ids)
            if piece in new_allowance or index >= len(old) or old[index] != new[index]
        }
        if changed:
            pieces = after.view(size)
            yield from ((size, pieces[index]) for index in sorted(changed))


class Guard:
    def __init__(self, validators: Sequence[PieceValidator]) -> None:
        self.validators = tuple(validators)

    def check(self, before: Style | None, after: Style) -> None:
        """Raise GeometryInvalid listing every refused piece; `before=None` checks every piece."""
        violations = []
        for size, piece in _changed(before, after):
            message = self._first_refusal(piece, after)
            if message is not None:
                violations.append({"size": size, "piece_id": str(piece.id), "message": message})
        if violations:
            raise GeometryInvalid(violations)

    def _first_refusal(self, piece: Piece, style: Style) -> str | None:
        for validator in self.validators:
            message = validator.refusal(piece, style.allowances.get(piece.id))
            if message is not None:
                return message
        return None


def default_guard() -> Guard:
    return Guard((OutlineValidator(), CutOutlineValidator()))
