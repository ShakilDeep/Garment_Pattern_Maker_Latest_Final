from copy import deepcopy

from app.application.assistant_context import build_context
from app.infrastructure.ai_provider import LocalAIProvider


def project():
    return {
        "id": "project-a",
        "name": "Private",
        "resolutions": {},
        "measurements": [],
        "techpack": None,
        "pattern": None,
        "grades": [],
        "audit": [{"secret": "private"}],
    }


def test_context_is_bounded_and_detached_from_project():
    p = project()
    p["measurements"] = [
        {
            "key": "custom",
            "label": "Unknown",
            "source": "sheet.xlsx",
            "values": {"L": {"value": None, "issue": "no cached value"}},
        }
    ]
    before = deepcopy(p)
    context = build_context(p, "L")
    assert context["project_id"] == "project-a"
    assert "audit" not in context and "name" not in context
    assert context["source_issues"][0]["source"] == "sheet.xlsx"
    context["requirements"][0]["why"] = "changed"
    assert p == before


def test_local_explanation_uses_actual_requirements():
    p = project()
    action = LocalAIProvider().propose("Why is a requirement unresolved?", "L", context=build_context(p, "L"))
    assert "Workbook units" in action["parameters"]["answer"]
    assert "Confirm" in action["parameters"]["answer"]
    assert action["intent"] == "explain"
    assert action["requires_confirmation"] is False


def test_ambiguity_summary_includes_source_and_preserves_values():
    p = project()
    p["measurements"] = [
        {
            "key": "sleeve_length",
            "label": "Sleeve",
            "source": "sheet.xlsx",
            "values": {"L": {"value": None, "issue": "no cached value"}},
        }
    ]
    before = deepcopy(p)
    action = LocalAIProvider().propose("Summarize document ambiguity", "L", context=build_context(p, "L"))
    assert "sheet.xlsx" in action["parameters"]["answer"]
    assert "no cached value" in action["parameters"]["answer"]
    assert p == before


def test_validation_context_never_uses_another_size():
    p = project()
    p["pattern"] = {
        "id": "pattern-l",
        "size": "L",
        "pieces": [],
        "validation": [{"severity": "ERROR", "message": "Wrong size warning"}],
    }
    action = LocalAIProvider().propose("Explain validation warnings", "M", context=build_context(p, "M"))
    assert "No pattern" in action["parameters"]["answer"]
    assert "Wrong size warning" not in action["parameters"]["answer"]
