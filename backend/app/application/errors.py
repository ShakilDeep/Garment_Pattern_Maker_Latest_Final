"""Application errors used as HTTP gates."""


class NotReady(ValueError):
    pass


class Unprocessable(ValueError):
    """Well-formed input the application refuses; `code` is the stable API error code (422)."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class ImportInvalid(Unprocessable):
    """A geometry import was rejected."""
