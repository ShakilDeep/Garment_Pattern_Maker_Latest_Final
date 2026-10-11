"""Which chart POM gives each block input (T142): data a pattern maker confirms, never a guessed rule.

A block's inputs (for 1078375, sew-line distances between named points) are not the finished-garment POMs
a buyer chart lists. An entry links one input to one chart POM; only a `confirmed` entry with evidence is
used. A block without a map file has no entries, so its inputs come from elsewhere or stay missing.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from app.domain.blocks.base import BlockInfo

MAPS_DIR = Path(__file__).parents[1] / "data" / "chart_maps"
PROPOSED, CONFIRMED = "proposed", "confirmed"


@dataclass(frozen=True)
class ChartMapEntry:
    input: str
    pom: str
    status: str
    evidence: str


def _entry(raw: dict, block: BlockInfo) -> ChartMapEntry:
    entry = ChartMapEntry(str(raw["input"]), str(raw["pom"]), str(raw["status"]), str(raw.get("evidence", "")))
    where = f"Chart map for {block.id}: {entry.input}"
    if entry.input not in block.required:
        raise ValueError(f"{where} is not an input of the block")
    if entry.status not in (PROPOSED, CONFIRMED):
        raise ValueError(f"{where} status must be {PROPOSED} or {CONFIRMED}")
    if entry.status == CONFIRMED and not entry.evidence.strip():
        raise ValueError(f"{where} is confirmed without evidence")
    return entry


def parse_chart_map(data: dict, block: BlockInfo) -> tuple[ChartMapEntry, ...]:
    if data.get("block") != block.id:
        raise ValueError(f"Chart map is for {data.get('block')}, not {block.id}")
    return tuple(_entry(raw, block) for raw in data.get("entries", []))


def chart_map(block: BlockInfo) -> tuple[ChartMapEntry, ...]:
    path = MAPS_DIR / f"{block.id}.json"
    if not path.is_file():
        return ()
    return parse_chart_map(json.loads(path.read_text(encoding="utf-8")), block)
