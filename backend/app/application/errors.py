"""Application errors used as HTTP gates."""


class NotReady(ValueError):
    """A precondition is not met yet (409). `code` is the stable API error code when the cause is known."""

    code: str | None = None


class HistoryEmpty(NotReady):
    """Undo or redo with no step to take (409 NOTHING_TO_UNDO / NOTHING_TO_REDO)."""

    def __init__(self, direction):
        super().__init__(f'Nothing to {direction}')
        self.code = f'NOTHING_TO_{direction.upper()}'


class StyleConflict(Exception):
    """The style changed since it was loaded, or its id is taken (409 STYLE_CONFLICT)."""


class Unprocessable(ValueError):
    """Well-formed input the application refuses; `code` is the stable API error code (422)."""

    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.details = details


class ImportInvalid(Unprocessable):
    """A geometry import was rejected."""


class GeometryInvalid(Unprocessable):
    """A CAD command produced geometry the guard refused (422 GEOMETRY_INVALID); `details` lists each piece."""

    def __init__(self, violations):
        pieces = ', '.join(sorted({f"{v['piece_id']} ({v['size']})" for v in violations}))
        super().__init__('GEOMETRY_INVALID', f'The edit was not saved: invalid geometry in {pieces}', violations)
