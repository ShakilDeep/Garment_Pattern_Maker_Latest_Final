"""Assistant context: selected-piece, truncation and label-mapping explanations."""
from copy import deepcopy

import pytest
from test_ai_context import project

from app.application.assistant_context import build_context
from app.infrastructure.ai_provider import LocalAIProvider


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
