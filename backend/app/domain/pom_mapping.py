"""Map one POM row to a canonical key with a chain of matchers (Chain of Responsibility).

Order: the buyer's exact source code, then the name, then the alternative-language name. A key that an
earlier row already took is never reused, so a duplicate surfaces as unmapped instead of overwriting.
AI suggestions are not part of this chain: they are proposals that need the user's confirmation.
"""
from collections.abc import Callable
from collections.abc import Set as AbstractSet

from app.domain.pom_labels import normalize
from app.domain.pom_synonyms import lookup, source_codes

Match = tuple[str, str, str] | None
UNMAPPED = "unmapped"
NOT_USED = "not_used"  # the user said the row is not needed
UNMATCHED = frozenset({UNMAPPED, NOT_USED})  # statuses whose key is only the source code
Matcher = Callable[[str, str, str | None], Match]


def by_source_code(code: str, name: str, alt_name: str | None) -> Match:
    key = source_codes().get(code)
    return (key, "catalog", code) if key else None


def by_name(code: str, name: str, alt_name: str | None) -> Match:
    for candidate in (name, alt_name):
        key = lookup(candidate) if candidate else None
        if key:
            return key, "synonym", normalize(candidate)
    return None


MATCHERS: tuple[Matcher, ...] = (by_source_code, by_name)


def map_row(code: str, name: str, alt_name: str | None, taken: AbstractSet[str]) -> tuple[str, str, str | None]:
    """(key, mapping_status, mapped_from); an unmapped row keeps its source code as its key."""
    for matcher in MATCHERS:
        match = matcher(code, name, alt_name)
        if match:
            return match if match[0] not in taken else (code, UNMAPPED, None)
    return code, UNMAPPED, None
