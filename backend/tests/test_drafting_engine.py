"""T141a: every block drafts through one engine; a dict block's V5 draft is unchanged and its V6 pieces
are the adapter's."""
import json

import pytest
from fastapi.testclient import TestClient
from pom_workbooks import BOOK2

from app.api.main import create_app
from app.application.block_pieces import draft_block_pieces
from app.application.drafting_engine import Draft, draft
from app.domain.blocks.registry import installed
from app.domain.blocks.run import draft_pattern
from app.infrastructure.legacy_pattern_adapter import piece_from_v5
from app.infrastructure.parsers import parse_xlsx


@pytest.fixture(scope="module")
def values():
    rows = parse_xlsx(BOOK2.read_bytes(), "Book2(4).xlsx")
    return {row["key"]: row["values"]["L"]["value"] for row in rows
            if row["values"].get("L", {}).get("value") is not None and row["mapping_status"] != "unmapped"}


@pytest.mark.parametrize("block_id", ["demo_v1", "shirt_v2"])
def test_a_dict_block_draft_is_unchanged_and_carries_its_v6_pieces(values, block_id):
    block = installed().get(block_id)
    result = draft(block, values, "L", {})
    assert isinstance(result, Draft)
    expected = draft_pattern(block, values, "L", {})
    assert json.dumps(result.pattern, sort_keys=True) == json.dumps(expected, sort_keys=True)
    assert result.pieces == tuple(piece_from_v5(piece).piece for piece in expected["pieces"])
    assert draft_block_pieces(block, values, "L", {}) == result.pieces


def test_an_unknown_style_option_is_refused(values):
    with pytest.raises(ValueError, match="Block demo_v1 has no style option collar"):
        draft(installed().get("demo_v1"), values, "L", {"collar": "mandarin"})


def test_health_reports_the_real_default_profile(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/health.db")) as client:
        body = client.get("/health").json()
    assert body["profile"] == installed().demo().id == "shirt_v2"
