"""T132: one fixed table drives the Gemini schema, the parser and the confirmation; it holds no numbers."""
from app.domain.style_detect.schema import ALL_SPECS, FAMILIES, UNKNOWN, options_for, response_schema


def test_every_option_offers_unknown_last_and_no_measurement():
    for spec in ALL_SPECS:
        assert spec.choices[-1] == UNKNOWN and len(set(spec.choices)) == len(spec.choices)
        assert not any(any(ch.isdigit() for ch in choice) for choice in spec.choices), spec.id


def test_the_response_schema_mirrors_the_table():
    schema = response_schema()
    assert schema["required"] == [spec.id for spec in ALL_SPECS]
    for spec in ALL_SPECS:
        item = schema["properties"][spec.id]
        assert item["properties"]["value"]["enum"] == list(spec.choices)
        assert item["required"] == ["value", "confidence"]


def test_options_are_split_by_family():
    shirt = {spec.id for spec in options_for("shirt")}
    pant = {spec.id for spec in options_for("pant")}
    assert {"collar", "placket", "yoke", "sleeve", "pockets"} == shirt
    assert {"leg", "waistband", "pockets"} == pant
    assert {spec.id for spec in options_for(UNKNOWN)} == shirt | pant
    assert FAMILIES == ("shirt", "pant")
