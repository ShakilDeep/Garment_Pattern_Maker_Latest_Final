"""Stable identifiers for pattern elements (PM-02): editing an element never changes its id."""

import re
from collections.abc import Iterable
from dataclasses import dataclass

ID_FORMAT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")


@dataclass(frozen=True)
class ElementId:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not ID_FORMAT.fullmatch(self.value):
            raise ValueError(
                f"Invalid identifier {self.value!r}: use 1-64 letters, digits, '_', '.', ':' or '-'"
            )

    def __str__(self) -> str:
        return self.value


class PointId(ElementId):
    pass


class SegmentId(ElementId):
    pass


class AnnotationId(ElementId):
    pass


class PieceId(ElementId):
    pass


class GradeRuleId(ElementId):
    pass


def require_unique(ids: Iterable[object], kind: str) -> None:
    seen: set[str] = set()
    for identifier in ids:
        if not isinstance(identifier, ElementId):
            # ValueError, not TypeError: the API maps ValueError to 400.
            raise ValueError(f"Every {kind} id must be an ElementId, not {identifier!r}")  # noqa: TRY004
        if identifier.value in seen:
            raise ValueError(f"Duplicate {kind} id: {identifier}")
        seen.add(identifier.value)
