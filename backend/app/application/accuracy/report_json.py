"""The accuracy report as JSON (spec §9, backend part): one row per check, a status header, the From-block list."""
from collections.abc import Sequence
from dataclasses import asdict

from app.application.accuracy.model import Check
from app.application.accuracy.suites import profile_of
from app.application.block_inputs import FROM_BLOCK
from app.domain.pattern.style import Style

OPTITEX = "Optitex import not yet verified"  # until a person records the import in markdown/MASTER.md
READY, ERRORS, NO_REFERENCE = "ready", "errors", "no_reference"


def from_block(project: dict, sizes: Sequence[str]) -> list[dict]:
    """Every input drafted from the reference block rather than the chart, with the sizes it was used in."""
    used: dict[str, set[str]] = {}
    for pattern in (project.get("pattern"), *project.get("grades", [])):
        for name, source in ((pattern or {}).get("input_sources") or {}).items():
            if source == FROM_BLOCK:
                used.setdefault(name, set()).add(pattern["size"])
    return [{"input": name, "sizes": [size for size in sizes if size in used[name]]} for name in sorted(used)]


def report_json(project: dict, style: Style, reference: str | None, checks: Sequence[Check]) -> dict:
    drafted = [size for size in style.sizes if style.has_geometry(size)]
    errors = sum(check.gate and not check.passed for check in checks)
    status = NO_REFERENCE if reference is None else ERRORS if errors else READY
    return {
        "profile": profile_of(project), "reference": reference, "status": status,
        "error_count": errors, "sizes_checked": drafted if reference else [],
        "sizes_not_drafted": [size for size in style.sizes if size not in drafted],
        "checks": [asdict(check) for check in checks], "from_block": from_block(project, style.sizes),
        "optitex": OPTITEX,
    }
