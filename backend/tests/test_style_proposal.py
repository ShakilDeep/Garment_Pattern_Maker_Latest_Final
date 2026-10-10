"""T132: a model's style proposal is untrusted; only known values survive and the user's choice is checked."""
import pytest

from app.domain.style_detect.proposal import parse_proposal, validate_choices


def _guess(value, confidence=0.9):
    return {"value": value, "confidence": confidence}


SHIRT = {"garment": _guess("shirt"), "fit": _guess("regular", 0.6), "collar": _guess("shirt_collar"),
         "placket": _guess("full"), "yoke": _guess("yes"), "sleeve": _guess("short", 1.4),
         "pockets": _guess("none", -2), "leg": _guess("wide"), "invented": _guess("x")}


def test_a_shirt_keeps_its_own_options_and_clamps_confidence():
    proposal = parse_proposal(SHIRT, "gemini", "gemini-test")
    assert (proposal.garment.value, proposal.fit.value, proposal.provider) == ("shirt", "regular", "gemini")
    options = {guess.id: (guess.value, guess.confidence) for guess in proposal.options}
    assert options == {"collar": ("shirt_collar", 0.9), "placket": ("full", 0.9), "yoke": ("yes", 0.9),
                       "sleeve": ("short", 1.0), "pockets": ("none", 0.0)}


def test_a_missing_option_is_unknown_not_guessed():
    proposal = parse_proposal({"garment": _guess("pant")}, "gemini", "m")
    assert {guess.id: guess.value for guess in proposal.options} == {
        "leg": "unknown", "waistband": "unknown", "pockets": "unknown"}
    assert proposal.fit.confidence == 0.0


@pytest.mark.parametrize("raw", [
    [], {"garment": _guess("dress")}, {"garment": "shirt"}, {"garment": _guess("shirt", "high")},
    {"garment": _guess("shirt", True)}, {"garment": _guess("shirt"), "collar": _guess(3.5)},
])
def test_invalid_output_is_rejected(raw):
    with pytest.raises(ValueError):
        parse_proposal(raw, "gemini", "m")


def test_the_users_choice_is_filled_and_ordered():
    assert validate_choices("pant", "relaxed", {"waistband": "elastic_drawcord", "leg": "wide"}) == {
        "garment": "pant", "fit": "relaxed",
        "options": {"leg": "wide", "waistband": "elastic_drawcord", "pockets": "unknown"}}


@pytest.mark.parametrize(("garment", "fit", "options", "message"), [
    ("unknown", "regular", {}, "garment"),
    ("shirt", "baggy", {}, "fit"),
    ("shirt", "regular", {"leg": "wide"}, "leg"),
    ("shirt", "regular", {"sleeve": "three_quarter"}, "sleeve"),
])
def test_an_invalid_choice_names_the_option(garment, fit, options, message):
    with pytest.raises(ValueError, match=message):
        validate_choices(garment, fit, options)
