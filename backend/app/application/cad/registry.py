"""Registry of command factories by name (PM-05): the bus creates every command through it."""

from collections.abc import Callable

from app.application.cad.command import Command, Params

type Factory[State] = Callable[[Params], Command[State]]


class Registry[State]:
    def __init__(self) -> None:
        self._factories: dict[str, Factory[State]] = {}

    def register(self, name: str, factory: Factory[State]) -> None:
        if name in self._factories:
            raise ValueError(f"The CAD command {name} is already registered")
        self._factories[name] = factory

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._factories)

    def create(self, name: str, params: Params) -> Command[State]:
        factory = self._factories.get(name)
        if factory is None:
            raise ValueError("Unsupported CAD command")
        return factory(params)
