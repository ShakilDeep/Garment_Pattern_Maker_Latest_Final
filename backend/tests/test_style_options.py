"""T128: style options are declared per block, validated, and applied as transforms in order."""
import pytest

from app.domain.blocks.base import StyleOption
from app.domain.blocks.options import resolve_choices
from app.domain.blocks.run import draft_pattern
from app.domain.blocks.transforms import TransformPipeline

YOKE = StyleOption("yoke", "Back yoke", ("split", "none"), "split")
SLEEVE = StyleOption("sleeve", "Sleeve", ("short",), "short", fixed=True)
POCKET = StyleOption("pocket", "Pocket", ("none", "patch"), "none")


class Mark:
    """Fake transform: records that it ran by appending its option and value."""

    def __init__(self, option_id):
        self.option_id = option_id

    def apply(self, pattern, value):
        return {**pattern, "log": [*pattern.get("log", []), f"{self.option_id}={value}"]}


class Block:
    id, version, family, calibration = "fake", "1", "shirt", "demo"
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    options = (YOKE, SLEEVE, POCKET)
    transforms = (Mark("pocket"), Mark("yoke"))

    def draft(self, measurements, size, choices):
        return {"size": size, "choices": dict(choices)}


def test_defaults_fill_every_option():
    assert resolve_choices(Block(), {}) == {"yoke": "split", "sleeve": "short", "pocket": "none"}
    assert resolve_choices(Block(), {"yoke": "none"})["yoke"] == "none"


@pytest.mark.parametrize(("requested", "message"), [
    ({"collar": "band"}, "Block fake has no style option collar"),
    ({"yoke": "double"}, "Style option yoke cannot be double; choose split or none"),
    ({"sleeve": "long"}, "Style option sleeve is fixed at short for block fake"),
])
def test_invalid_choices_are_rejected(requested, message):
    with pytest.raises(ValueError, match=message):
        resolve_choices(Block(), requested)


def test_transforms_run_in_declared_order_with_the_chosen_values():
    pattern = draft_pattern(Block(), {}, "M", {"pocket": "patch"})
    assert pattern["choices"] == {"yoke": "split", "sleeve": "short", "pocket": "patch"}
    assert pattern["log"] == ["pocket=patch", "yoke=split"]


def test_a_transform_without_a_declared_option_is_a_programming_error():
    with pytest.raises(ValueError, match="Transform for undeclared option collar"):
        TransformPipeline((Mark("collar"),)).apply({}, {"yoke": "split"})


def test_an_empty_pipeline_returns_the_pattern_unchanged():
    pattern = {"size": "M"}
    assert TransformPipeline(()).apply(pattern, {}) is pattern
