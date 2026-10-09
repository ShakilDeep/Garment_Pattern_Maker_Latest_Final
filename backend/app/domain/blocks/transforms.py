"""Style options as transforms (Pipeline): each transform rewrites the drafted pattern for one option's value.

Concrete transforms (yoke split, placket, pocket bag, elastic casing) arrive with the named-point blocks
(T130 shirt, T133 pant); a transform decides itself what each value means, including "none".
"""
from collections.abc import Mapping
from typing import Protocol


class Transform(Protocol):
    option_id: str

    def apply(self, pattern: dict, value: str) -> dict:
        """Return the pattern with this option's value applied (never mutate the input)."""
        ...


class TransformPipeline:
    def __init__(self, transforms: tuple[Transform, ...]):
        self._transforms = transforms

    def apply(self, pattern: dict, choices: Mapping[str, str]) -> dict:
        for transform in self._transforms:
            if transform.option_id not in choices:
                raise ValueError(f"Transform for undeclared option {transform.option_id}")
            pattern = transform.apply(pattern, choices[transform.option_id])
        return pattern
