"""Named validators with shared corrective metadata for domain and UI consumers."""
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise

from app.domain.catalog import SIZES
from app.domain.tolerances import LENGTH_CM
from app.infrastructure.outline_quality import outline_quality
from app.infrastructure.pattern_checks import structural_checks
from app.infrastructure.placement_checks import placement_checks
from app.infrastructure.seam_checks import seam_checks


@dataclass(frozen=True)
class Validator:
    id: str
    check: Callable

    def run(self, value):
        return [enrich(issue, self.id) for issue in self.check(value)]


def enrich(issue, rule):
    return {
        'rule': rule,
        'action': 'Inspect the affected piece and source measurements; correct inputs and regenerate.',
        'target': 'Pattern Studio',
        **issue,
    }


PATTERN_VALIDATORS = (
    Validator('geometry.structure.v2', structural_checks),
    Validator('geometry.outline_quality.v1', outline_quality),
    Validator('shirt.seams_and_sources.v1', seam_checks),
    Validator('shirt.placement.v1', placement_checks),
)


def validate(pattern):
    return [issue for validator in PATTERN_VALIDATORS for issue in validator.run(pattern)]


def validate_grades(patterns):
    """Report decreases, without assuming customer-approved grading increments."""
    ordered = sorted(patterns, key=lambda p: list(SIZES).index(p['size']))
    issues = []
    for small, large in pairwise(ordered):
        by_id = {p['id']: p for p in large['pieces']}
        for piece in small['pieces']:
            other = by_id.get(piece['id'])
            if other is None:
                issues.append(enrich({'code': 'GRADING_INVENTORY', 'severity': 'ERROR',
                    'piece': piece['name'], 'message': f"{large['size']} is missing {piece['name']}"},
                    'grading.inventory.v1'))
                continue
            for dimension in ('width', 'height'):
                delta = other[dimension] - piece[dimension]
                issues.append(enrich({'code': 'GRADING_DIMENSION', 'severity': 'PASS' if delta >= -LENGTH_CM else 'WARNING',
                    'piece': piece['name'], 'actual': delta, 'expected': 0, 'tolerance': LENGTH_CM,
                    'message': f"{piece['name']} {dimension}, {small['size']} → {large['size']}: {delta:.3f} cm",
                    'action': 'Review the source size table; decreases may be intentional. Confirm before cutting.',
                    'target': 'Grading'}, 'grading.monotonic_dimensions.v1'))
    return issues
