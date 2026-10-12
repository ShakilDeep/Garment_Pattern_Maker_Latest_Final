"""T143: the app reads its accuracy reference (the client PDS) at runtime, once per process."""
from app.infrastructure.pds.reference_store import reference_for

SIZES = ("S", "M", "L", "XL", "XXL", "3XL")


def test_the_1078375_block_reads_the_client_shirt_pds():
    reference = reference_for("shirt_1078375")
    assert reference is not None
    assert (reference.base_size, reference.sizes) == ("L", SIZES)
    assert reference.totals["L"].area_m2 == 1.4262


def test_a_profile_without_a_client_reference_has_none():
    assert reference_for("demo_v1") is None
    assert reference_for("shirt_v2") is None


def test_the_reference_is_read_once():
    assert reference_for("shirt_1078375") is reference_for("shirt_1078375")
