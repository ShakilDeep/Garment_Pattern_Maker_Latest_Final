"""Application errors used as HTTP gates."""


class NotReady(ValueError):
    pass


class ImportInvalid(ValueError):
    """A geometry import was rejected; `code` is the stable API error code (422)."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
