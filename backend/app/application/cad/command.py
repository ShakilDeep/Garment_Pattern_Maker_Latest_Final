"""Command (PM-05): one validated edit, `apply(state) -> new state`. States are never changed in place."""

from collections.abc import Mapping
from typing import Protocol

Params = Mapping[str, object]


class Command[State](Protocol):
    @property
    def name(self) -> str: ...

    def apply(self, state: State) -> State: ...


def require_params(params: Params, names: tuple[str, ...]) -> None:
    """Exactly these parameters: a missing or unknown one raises ValueError (400) naming it."""
    missing = [name for name in names if name not in params]
    if missing:
        raise ValueError(f"The command is missing parameter {missing[0]}")
    unknown = sorted(str(name) for name in params if name not in names)
    if unknown:
        raise ValueError(f"The command has unknown parameter {unknown[0]}")
