"""T126c: the user confirms a POM mapping (or marks the row not used); suggestions never change rows."""
import pytest

from app.application.assistant_contracts import AssistantFailure
from app.application.pattern_inputs import drafting_values
from app.application.pom_mapping_confirm import confirm
from app.application.pom_suggestions import suggest_mappings
from app.ports.pom_suggester import PomSuggestError, PomSuggestion


def _project():
    return {"measurements": [
        {"key": "half_waist", "code": "A1", "original_label": "1/2 WAIST", "mapping_status": "synonym",
         "mapped_from": "1/2 WAIST", "row": 2, "values": {"S": {"value": 35}}},
        {"key": "Z9", "code": "Z9", "original_label": "1/2 HIPS", "mapping_status": "unmapped",
         "mapped_from": None, "row": 3, "values": {"S": {"value": 48}}},
    ]}


class Fake:
    name = "fake"

    def __init__(self, key="half_seat", error=None):
        self.key, self.error, self.calls = key, error, []

    def suggest(self, queries, keys):
        self.calls.append((list(queries), list(keys)))
        if self.error:
            raise self.error
        return [PomSuggestion(q.row, self.key, 0.9, "gemini", "hips = seat") for q in queries]


def test_confirming_a_key_maps_the_row_and_it_reaches_drafting():
    project = confirm(_project(), 3, "half_seat")
    row = project["measurements"][1]
    assert (row["key"], row["mapping_status"], row["mapped_from"]) == ("half_seat", "confirmed", "user")
    assert drafting_values(project, "S") == {"half_waist": 35, "half_seat": 48}


def test_accepting_a_stored_suggestion_records_its_provider_and_drops_it():
    project = _project()
    suggest_mappings(project, Fake())
    row = confirm(project, 3, "half_seat")["measurements"][1]
    assert row["mapped_from"] == "ai:gemini"
    assert project["mapping_suggestions"] == {}


def test_a_row_marked_not_used_never_reaches_drafting():
    project = confirm(_project(), 3, None)
    assert project["measurements"][1]["mapping_status"] == "not_used"
    assert drafting_values(project, "S") == {"half_waist": 35}


@pytest.mark.parametrize(("row", "key", "error", "text"), [
    (3, "half_waist", ValueError, "already mapped to row 2"),
    (3, "not_a_key", ValueError, "Unknown canonical measurement"),
    (42, "half_seat", KeyError, "42"),
])
def test_bad_confirmations_change_nothing(row, key, error, text):
    project = _project()
    with pytest.raises(error, match=text):
        confirm(project, row, key)
    assert project == _project()


def test_suggestions_are_stored_but_rows_are_unchanged_and_taken_keys_not_offered():
    project, fake = _project(), Fake()
    suggestions = suggest_mappings(project, fake)
    assert [(s["row"], s["key"], s["provider"]) for s in suggestions] == [(3, "half_seat", "gemini")]
    assert project["measurements"] == _project()["measurements"]
    assert project["mapping_suggestions"]["3"]["key"] == "half_seat"
    queries, keys = fake.calls[0]
    assert [q.label for q in queries] == ["1/2 HIPS"] and "half_waist" not in keys


def test_no_unmapped_rows_means_no_provider_call():
    project, fake = confirm(_project(), 3, None), Fake()
    assert suggest_mappings(project, fake) == [] and fake.calls == []


@pytest.mark.parametrize(("unavailable", "status"), [(True, 503), (False, 502)])
def test_provider_errors_become_assistant_failures(unavailable, status):
    fake = Fake(error=PomSuggestError("gemini", unavailable=unavailable))
    with pytest.raises(AssistantFailure) as raised:
        suggest_mappings(_project(), fake)
    assert raised.value.status_code == status
