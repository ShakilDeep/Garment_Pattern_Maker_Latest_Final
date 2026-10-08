"""The POM synonym table: canonical measurement keys, their known names, and buyers' exact codes.

The table is data (``data/pom_synonyms.json``), loaded once. A name may point at one key only.
"""
import json
from collections.abc import Mapping, Sequence
from functools import cache
from pathlib import Path
from types import MappingProxyType

from app.domain.pom_labels import normalize

_TABLE = Path(__file__).with_name("data") / "pom_synonyms.json"


def check_unique(keys: Mapping[str, Sequence[str]]) -> dict[str, str]:
    """Normalized name -> key; raises when one name would map to two keys."""
    index: dict[str, str] = {}
    for key, names in keys.items():
        for name in map(normalize, names):
            if index.setdefault(name, key) != key:
                raise ValueError(f"Synonym {name} maps to both {index[name]} and {key}")
    return index


@cache
def _table() -> dict:  # read once per process; the table is static data
    return json.loads(_TABLE.read_text(encoding="utf-8"))


@cache
def _index() -> Mapping[str, str]:
    return MappingProxyType(check_unique(_table()["keys"]))


def canonical_keys() -> tuple[str, ...]:
    return tuple(_table()["keys"])


@cache
def source_codes() -> Mapping[str, str]:
    """Every buyer's exact source code -> key (codes are unique across buyers)."""
    merged: dict[str, str] = {}
    for buyer, codes in _table()["codes"].items():
        for code, key in codes.items():
            if merged.setdefault(code, key) != key:
                raise ValueError(f"Source code {code} of {buyer} maps to both {merged[code]} and {key}")
    return MappingProxyType(merged)


def lookup(name: object) -> str | None:
    return _index().get(normalize(name))
