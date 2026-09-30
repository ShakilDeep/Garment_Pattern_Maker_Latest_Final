from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
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


def test_api_passes_only_current_project_context(tmp_path):
    class ContextProvider(LocalAIProvider):
        def propose(self, prompt, size, *, context=None):
            assert context["project_id"] == pid
            assert "audit" not in context
            return super().propose(prompt, size, context=context)

    client = TestClient(create_app(f"sqlite:///{tmp_path}/context.db", ai_provider=ContextProvider()))
    pid = client.post("/api/v1/projects", json={"name": "Context"}).json()["id"]
    response = client.post(
        f"/api/v1/projects/{pid}/assistant/propose", json={"prompt": "Explain requirements"}
    )
    assert response.status_code == 200
    assert "Workbook units" in response.json()["parameters"]["answer"]
    before = client.get(f"/api/v1/projects/{pid}").json()
    invalid = client.post(
        f"/api/v1/projects/{pid}/assistant/propose",
        json={"prompt": "Explain selected piece", "piece_id": "from-another-project"},
    )
    assert invalid.status_code == 404
    assert client.get(f"/api/v1/projects/{pid}").json() == before


def test_selected_piece_and_stale_validation_are_explicit():
    p = project()
    p["pattern"] = {
        "id": "version",
        "size": "L",
        "stale": True,
        "pieces": [
            {
                "id": "sleeve",
                "name": "Sleeve",
                "width": 40,
                "height": 60,
                "quantity": 2,
                "seams": {"wrist": 25},
                "points": [[0, 0]],
            }
        ],
        "validation": [
            {"severity": "WARNING", "message": "Sleeve cap mismatch", "action": "Review cap ease"}
        ],
    }
    context = build_context(p, "L", "sleeve")
    assert "points" not in context["selected_piece"]
    answer = LocalAIProvider().propose("Explain this piece", "L", context=context)["parameters"]["answer"]
    assert "Sleeve" in answer and "40 × 60 cm" in answer
    assert "wrist: 25.00 cm" in answer
    assert "{'" not in answer
    answer = LocalAIProvider().propose("Explain validation", "L", context=context)["parameters"]["answer"]
    assert "stale" in answer and "Review cap ease" in answer
    with pytest.raises(KeyError):
        build_context(p, "M", "sleeve")


def test_context_and_answer_report_truncation():
    p = project()
    p["measurements"] = [
        {
            "key": f"custom{i}",
            "label": "Unknown",
            "source": "sheet.xlsx",
            "values": {"L": {"issue": "x" * 1000}},
        }
        for i in range(120)
    ]
    context = build_context(p, "L")
    assert len(context["measurement_labels"]) == 100
    assert len(context["source_issues"]) == 50
    assert context["truncated"] is True
    answer = LocalAIProvider().propose("Summarize source ambiguity", "L", context=context)["parameters"][
        "answer"
    ]
    assert len(answer) <= 4000
    assert "Summary shortened" in answer


@pytest.mark.parametrize(
    "label,expected",
    [
        ("shoulder breadth", "shoulder_point_to_point"),
        ("sleev length", "sleeve_length"),
        ("interstellar measurement", "No confident mapping"),
        ("chest circumference", "No confident mapping"),
    ],
)
def test_label_mapping_is_a_review_suggestion(label, expected):
    p = project()
    before = deepcopy(p)
    action = LocalAIProvider().propose(f'Map measurement label "{label}"', "L", context=build_context(p, "L"))
    assert expected in action["parameters"]["answer"]
    assert action["intent"] == "explain"
    assert "review" in action["parameters"]["answer"].lower()
    assert p == before
