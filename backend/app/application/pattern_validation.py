"""Validation by geometry source (T141b): V5 drafts keep their V5 checks; a named block's V6 pieces are
checked by the same validators the CAD guard runs, reported in the V5 issue format the readiness and
review flows already read.
"""
from app.application.cad.validators import CutOutlineValidator, OutlineValidator
from app.application.drafting_engine import Draft
from app.infrastructure.geometry_adapter import validate

GEOMETRY_INVALID = "GEOMETRY_INVALID"
_CHAIN = (OutlineValidator(), CutOutlineValidator())


def _issue(piece_name: str, message: str) -> dict:
    return {"severity": "ERROR", "code": GEOMETRY_INVALID, "piece": piece_name, "message": message,
            "action": "Correct the block measurements or edit the piece in Pattern Studio"}


def validate_draft(draft: Draft) -> list[dict]:
    if not draft.allowances:
        return validate(draft.pattern)
    issues = []
    for piece in draft.pieces:
        refusal = next(
            (r for v in _CHAIN if (r := v.refusal(piece, draft.allowances[piece.id])) is not None), None
        )
        if refusal is not None:
            issues.append(_issue(piece.name, refusal))
    return issues
