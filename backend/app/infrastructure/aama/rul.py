"""AAMA .RUL grade-rule file: header, then per rule one ``dx, dy`` line per size, then END.

Deltas are cm in the model and mm (METRIC) or inch (ENGLISH) in the file. Inch values carry two extra
decimals so a round trip stays on the 1e-6 cm model grid. Real rules arrive with graded export (T131).
"""
from app.domain.interchange import GradeRuleTable, Point
from app.infrastructure.aama.layers import AAMA_VERSION, MODEL_DECIMALS, cm_per_unit, unit_scale

DECIMALS = {"METRIC": 6, "ENGLISH": 8}
REQUIRED = ("GRADE RULE TABLE", "SIZE LIST", "SAMPLE SIZE", "UNITS")


def write_rul(table: GradeRuleTable, unit: str) -> str:
    flag, scale = unit_scale(unit)
    if any(not size or any(c.isspace() for c in size) for size in table.sizes):
        raise ValueError("RUL size names cannot be empty or contain spaces")
    places = DECIMALS[flag]
    lines = [AAMA_VERSION, f"GRADE RULE TABLE: {table.name}", f"NUMBER OF SIZES: {len(table.sizes)}",
             f"SIZE LIST: {' '.join(table.sizes)}", f"SAMPLE SIZE: {table.sample_size}", f"UNITS: {flag}"]
    for number, deltas in enumerate(table.rules, start=1):
        lines.append(f"RULE: DELTA {number}")
        lines.extend(f"{dx * scale + 0.0:.{places}f}, {dy * scale + 0.0:.{places}f}" for dx, dy in deltas)
    lines.append("END")
    return "\n".join(lines) + "\n"


def read_rul(text: str) -> GradeRuleTable:
    fields: dict[str, str] = {}
    rules: list[list[Point]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line == "END":
            continue
        if line.startswith("RULE:"):
            rules.append([])
        elif rules:
            rules[-1].append(_delta(line))
        elif ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    for key in REQUIRED:
        if key not in fields:
            raise ValueError(f"RUL field missing: {key}")
    scale = cm_per_unit(fields["UNITS"])
    sizes = tuple(fields["SIZE LIST"].split())
    declared = fields.get("NUMBER OF SIZES")
    if declared is not None and declared != str(len(sizes)):
        raise ValueError(f"RUL declares {declared} sizes but lists {len(sizes)}")
    return GradeRuleTable(
        name=fields["GRADE RULE TABLE"], sizes=sizes,
        sample_size=fields["SAMPLE SIZE"],
        rules=tuple(tuple(_cm(delta, scale) for delta in rule) for rule in rules),
    )


def _delta(line: str) -> Point:
    parts = line.split(",")
    if len(parts) != 2:
        raise ValueError(f"RUL delta needs two values (dx, dy): {line!r}")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"RUL delta is not a number: {line!r}") from None


def _cm(delta: Point, scale: float) -> Point:
    return (round(delta[0] * scale, MODEL_DECIMALS) + 0.0, round(delta[1] * scale, MODEL_DECIMALS) + 0.0)
