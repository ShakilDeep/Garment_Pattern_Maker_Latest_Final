"""Style options as transforms (Pipeline): each transform rewrites the drafted pattern for one option's value.

A pattern is whatever the block drafts: the V5 dict for the demo shirt, or a tuple of named V6 pieces
(T129). Concrete transforms (yoke split, placket, pocket bag, elastic casing) arrive with the named-point
blocks (T130 shirt, T133 pant); a transform decides itself what each value means, including "none".
"""
from collections.abc import Mapping
from typing import Protocol


class Transform[PatternT](Protocol):
    option_id: str

    def apply(self, pattern: PatternT, value: str) -> PatternT:
        """Return the pattern with this option's value applied (never mutate the input)."""
        ...


class TransformPipeline[PatternT]:
    def __init__(self, transforms: tuple[Transform[PatternT], ...]):
        self._transforms = transforms

    def apply(self, pattern: PatternT, choices: Mapping[str, str]) -> PatternT:
        for transform in self._transforms:
            if transform.option_id not in choices:
                raise ValueError(f"Transform for undeclared option {transform.option_id}")
            pattern = transform.apply(pattern, choices[transform.option_id])
        return pattern
