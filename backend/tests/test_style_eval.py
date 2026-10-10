"""T132: the labelled-image check reports per family, and stays open below 30 images (doc 124)."""
from app.application.style_eval import MIN_PER_FAMILY, Labelled, evaluate
from app.domain.style_detect.proposal import parse_proposal


def _proposal(garment, **options):
    raw = {"garment": {"value": garment, "confidence": 1}}
    raw.update({key: {"value": value, "confidence": 1} for key, value in options.items()})
    return parse_proposal(raw, "gemini", "m")


PANT = Labelled("p.png", "pant", {"leg": "wide", "waistband": "elastic"})


def test_a_family_with_too_few_images_is_open_with_its_accuracy():
    report = evaluate([(PANT, _proposal("pant", leg="wide", waistband="elastic")),
                       (PANT, _proposal("pant", leg="straight", waistband="elastic")),
                       (PANT, _proposal("shirt"))])
    assert report["pant"] == {"images": 3, "correct": 1, "accuracy": 0.333, "gate": "open",
                              "misses": {"leg": 1, "garment": 1}}
    assert report["shirt"]["images"] == 0 and report["shirt"]["gate"] == "open"


def test_the_gate_passes_only_when_every_one_of_enough_images_is_right():
    good = [(PANT, _proposal("pant", leg="wide", waistband="elastic"))] * MIN_PER_FAMILY
    assert evaluate(good)["pant"]["gate"] == "pass"
    assert evaluate([*good, (PANT, _proposal("pant"))])["pant"]["gate"] == "fail"


def test_an_unlabelled_option_is_not_scored():
    shirt = Labelled("s.png", "shirt", {"sleeve": "short"})
    assert evaluate([(shirt, _proposal("shirt", sleeve="short", collar="band"))])["shirt"]["correct"] == 1
