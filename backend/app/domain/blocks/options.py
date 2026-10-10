"""Validate a style's requested option values against the block's declared options; fill the defaults."""
from collections.abc import Mapping

from app.domain.blocks.base import BlockInfo


def resolve_choices(block: BlockInfo, requested: Mapping[str, str]) -> dict[str, str]:
    declared = {option.id: option for option in block.options}
    unknown = [key for key in requested if key not in declared]
    if unknown:
        raise ValueError(f"Block {block.id} has no style option {unknown[0]}")
    choices: dict[str, str] = {}
    for option in block.options:
        value = requested.get(option.id, option.default)
        if option.fixed and value != option.default:
            raise ValueError(f"Style option {option.id} is fixed at {option.default} for block {block.id}")
        if value not in option.choices:
            raise ValueError(f"Style option {option.id} cannot be {value}; choose {' or '.join(option.choices)}")
        choices[option.id] = value
    return choices
