"""T128: finishing settings load from data, every value has a source, and bad data is refused."""
import copy

import pytest

from app.domain.finishing import FINISHING_FILE, allowance, finishing, parse_finishing


def test_the_seeded_values_are_the_client_pds_values():
    assert allowance("shirt", "hem").value_cm == 3.5
    assert allowance("shirt", "collar").value_cm == 1.3
    assert (allowance("shirt", "side_seam_front").value_cm, allowance("shirt", "side_seam_back").value_cm) == (0.8, 1.7)
    assert allowance("pant", "body_seam").value_cm == 1.0
    settings = finishing()
    assert settings.families["shirt"].notch_depth_cm == 0.7 and settings.families["pant"].fold_edge_cm == 0
    linen = settings.fabrics["linen_cl1086464"]
    assert (linen.warp_pct, linen.weft_pct) == (5.0, 5.0) and "CL1086464" in linen.source


REVIEW_STATUS = {"shirt": "confirmed", "pant": "needs_pattern_maker_review"}


def test_every_allowance_names_its_source_and_review_status():
    # Shirt roles were confirmed in the T129 review (docs/drafting/shirt.md Q8); pant roles still await review.
    for family_id, family in finishing().families.items():
        assert family.corner_source and family.allowances
        for item in family.allowances.values():
            assert item.source and item.status == REVIEW_STATUS[family_id], item.role
            assert item.evidence, item.role


def test_an_unknown_role_is_a_key_error_not_a_default():
    with pytest.raises(KeyError, match="shirt has no finishing allowance 'pocket'"):
        allowance("shirt", "pocket")
    with pytest.raises(KeyError, match="No finishing settings for family 'tee'"):
        allowance("tee", "hem")


def _raw():
    import json

    return json.loads(FINISHING_FILE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("mutate", "message"), [
    (lambda d: d["families"]["shirt"]["allowances"][0].update(value_cm=-1), "hem must not be negative"),
    (lambda d: d["families"]["shirt"]["allowances"][0].update(source=" "), "hem needs a source"),
    (lambda d: d["families"]["shirt"]["allowances"].append(copy.deepcopy(d["families"]["shirt"]["allowances"][0])),
     "shirt lists allowance hem twice"),
    (lambda d: d["families"]["shirt"]["notch"].update(depth_cm=0), "shirt notch depth must be positive"),
    (lambda d: d["fabrics"]["linen_cl1086464"].update(warp_pct=60), "linen_cl1086464 shrinkage must be 0-50 %"),
    (lambda d: d["fabrics"]["linen_cl1086464"].pop("weft_pct"), "linen_cl1086464 needs warp_pct and weft_pct"),
])
def test_invalid_settings_are_refused(mutate, message):
    data = _raw()
    mutate(data)
    with pytest.raises(ValueError, match=message):
        parse_finishing(data)
