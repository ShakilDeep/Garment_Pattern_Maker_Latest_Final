"""P1-05: a Style round-trips through canonical JSON; per-size pieces are decoded only when viewed."""

import json

import pytest
from test_style import _pieces, _style

from app.domain.pattern.serialize import piece_to_data
from app.domain.pattern.style_codec import style_from_json, style_to_json


def _graded():
    return _style().with_pieces("4", _pieces("back", "front"))


def test_round_trip_is_exact_canonical_and_idempotent():
    text = style_to_json(_graded())
    restored = style_from_json(text)
    assert restored == _graded()
    assert restored.view("4") == _graded().view("4")
    assert style_to_json(restored) == text
    assert json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"), allow_nan=False) == text


def _with_broken_size(size):
    document = json.loads(style_to_json(_graded()))
    entry = next(e for e in document["geometry"] if e["size"] == size)
    entry["pieces"][1]["outline"][0]["end"] = "zz"
    return json.dumps(document)


def test_loading_defers_piece_checks_until_a_size_is_viewed():
    style = style_from_json(_with_broken_size("4"))
    assert [p.name for p in style.view("4½")] == ["Back", "Front"]
    with pytest.raises(ValueError, match="Size 4: .*Unknown point"):
        style.view("4")
    with pytest.raises(ValueError, match="Size 4: "):
        style.validate_all()
    assert _style().validate_all() is None


def test_an_unviewed_size_serializes_exactly_as_loaded():
    text = style_to_json(style_from_json(_with_broken_size("4")))
    assert json.loads(text) == json.loads(_with_broken_size("4"))


def _document(**changes):
    return json.dumps({**json.loads(style_to_json(_graded())), **changes})


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[]", "must be an object"),
        ("{", "not valid JSON"),
        ('{"schema_version": NaN}', "not valid JSON"),
        (_document(schema_version=2), "Unsupported style schema version 2"),
        (_document(sizes=None), "Size labels"),
        (_document(geometry=[{"size": "4"}]), "missing field 'pieces'"),
        (_document(geometry=[{"size": "4½", "pieces": [{"name": "x"}]}]), "missing field 'id'"),
        (_document(geometry=[{"size": "4½", "pieces": [{"id": "bad id"}]}]), "Invalid identifier"),
        (_document(geometry=[{"size": "4½", "pieces": []}] * 2), "4½ has geometry more than once"),
        (_document(geometry=[{"size": "4½", "pieces": [{"id": "back", "x": 1}]}]).replace(
            '"x": 1}', '"x": 1e400}'), "out of range"),
    ],
)
def test_malformed_documents_raise_value_errors(text, message):
    with pytest.raises(ValueError, match=message):
        style_from_json(text)


def test_sizes_must_agree_on_the_piece_list_at_load():
    document = json.loads(style_to_json(_graded()))
    document["geometry"][0]["pieces"] = [piece_to_data(_pieces("back")[0])]
    with pytest.raises(ValueError, match="same pieces"):
        style_from_json(json.dumps(document))


def test_viewing_a_loaded_size_normalizes_it_to_the_canonical_memento():
    document = json.loads(style_to_json(_graded()))
    back = document["geometry"][1]["pieces"][0]
    back["junk"] = {"ignored": True}
    back["points"][0]["x"] = 1e-9
    loaded = style_from_json(json.dumps(document))
    assert loaded != _graded()
    loaded.validate_all()
    assert loaded == _graded() and style_to_json(loaded) == style_to_json(_graded())
