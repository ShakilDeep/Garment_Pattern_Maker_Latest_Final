"""Score Gemini style detection on the labelled set in fixtures/style_labels (T132 gate, doc 124).

Usage: python scripts/eval_style_detect.py [--labels PATH]
Needs GEMINI_API_KEY. Prints images, correct, accuracy, gate (open/pass/fail) and misses per family.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from record_style_detect import _key

from app.application.style_eval import Labelled, evaluate
from app.domain.style_detect.schema import FAMILIES
from app.infrastructure.image_prep import prepare_image
from app.infrastructure.provider_factory import get_style_detector

LABELS = ROOT / "fixtures" / "style_labels" / "labels.json"


def _labels(path: Path) -> list[Labelled]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    bad = [row["file"] for row in rows if row["garment"] not in FAMILIES]
    if bad:
        raise SystemExit(f"Unknown garment for {bad[0]}; use {' or '.join(FAMILIES)}")
    return [Labelled(row["file"], row["garment"], row.get("options", {})) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--labels", type=Path, default=LABELS)
    args = parser.parse_args()
    labels = _labels(args.labels)
    detector = get_style_detector({"GEMINI_API_KEY": _key()}) if labels else None
    results = [(label, detector.detect(prepare_image((args.labels.parent / label.file).read_bytes(), 1)))
               for label in labels] if detector else []
    print(json.dumps(evaluate(results), indent=2))


if __name__ == "__main__":
    main()
