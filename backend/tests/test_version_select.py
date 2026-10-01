"""P0-05 / defect e: one grade-first version-selection rule shared with the frontend."""
import json
from pathlib import Path

import pytest
from test_ai_context import project

from app.application.assistant_context import build_context
from app.application.version_select import select_for_size

CASES = json.loads(
    (Path(__file__).resolve().parents[2] / "frontend/src/versionSelect.cases.json").read_text()
)["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_select_for_size_matches_the_shared_parity_table(case):
    selected = select_for_size(case["project"], case["size"])
    assert (selected or {}).get("id") == case["expected"]


def test_assistant_context_describes_the_grade_the_ui_shows():
    p = project()
    p["pattern"] = {"id": "base-l", "size": "L", "pieces": [], "validation": []}
    p["grades"] = [{"id": "grade-l", "size": "L", "pieces": [], "validation": []}]
    assert build_context(p, "L")["pattern"]["id"] == "grade-l"
