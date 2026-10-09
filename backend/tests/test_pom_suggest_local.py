"""T126c: the offline POM suggester proposes a key only when the name is clearly close to one synonym."""
from app.domain.pom_synonyms import canonical_keys
from app.infrastructure.pom_suggest_local import LocalPomSuggester
from app.ports.pom_suggester import PomQuery

KEYS = canonical_keys()


def _suggest(label, keys=KEYS, alt=None):
    return LocalPomSuggester().suggest([PomQuery(7, "Q1", label, alt)], keys)[0]


def test_a_misspelt_synonym_is_suggested_with_its_score():
    suggestion = _suggest("1/2 WAIST AT TOP EGDE")
    assert (suggestion.row, suggestion.key, suggestion.provider) == (7, "half_waist", "local")
    assert 0.82 <= suggestion.confidence < 1


def test_punctuation_and_case_do_not_matter():
    assert _suggest("inseam (along sm)").key == "inseam"


def test_the_alternative_language_name_is_also_compared():
    assert _suggest("MYSTERY", alt="1/2 BASEN.").key == "half_seat"


def test_an_unrelated_name_gets_no_key():
    suggestion = _suggest("MYSTERY POINT")
    assert suggestion.key is None
    assert "No confident" in suggestion.reason


def test_only_the_offered_keys_are_suggested():
    assert _suggest("1/2 WAIST AT TOP EGDE", keys=("half_seat", "inseam")).key is None


def test_an_empty_query_list_returns_nothing():
    assert LocalPomSuggester().suggest([], KEYS) == []
