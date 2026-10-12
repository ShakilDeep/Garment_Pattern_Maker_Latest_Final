"""README.txt of a project's Optitex export (T146): what the files are, and what is not yet verified.

Every line states a fact of the project or a decision recorded in markdown/MASTER.md; nothing claims that
Optitex has opened the files. That claim needs a person's record in MASTER (spec §10).
"""
from app.application.accuracy.report_json import OPTITEX
from app.application.accuracy.suites import profile_of
from app.domain.pattern.style import Style

UNIT_TEXT = {"mm": "METRIC (mm)", "inch": "ENGLISH (inch)"}
OPEN_QUESTIONS = (
    "Q4 grain position: the client PDS has none; grain is drawn along CF/CB (x), centred on each piece.",
    "Q10 piece names: the client PDS piece names are used.",
    "Q12 notches: exported as 0.7 cm slits from the sew line; the client PDS stores T-notches with a 1.2 cm cut.",
)
TESTER_CHECKS = (
    "1. Import base.dxf with grade_rules.rul (record the Optitex menu path used).",
    "2. Check piece names, quantities, fold (mirrored halves), grain, notches, sew and cut lines.",
    "3. Open the size table: every size listed above is present and nests in the grade view.",
    ("4. Compare each piece's Optitex area with the '<size> <piece> cut area' rows of GET /accuracy, and its "
     "perimeter and sew area with the client PDS, within 0.5 % per piece."),
)
FILES = ("base.dxf: the base size, cut-line corners carrying grade rule numbers (layer 5)",
         "grade_rules.rul: each rule's move per size",
         "all_sizes.dxf: every size drawn exactly, for checking the grade")


def readme(project: dict, style: Style, unit: str, accuracy: str) -> str:
    lines = [
        OPTITEX, "",
        f"Project: {project['name']}", f"Block: {profile_of(project)}",
        f"Sizes: {', '.join(style.sizes)}", f"Base size: {style.base_size}",
        f"File units: {UNIT_TEXT[unit]} (the pattern is drafted in cm)", f"Accuracy report: {accuracy}", "",
        "Files:", *(f"- {line}" for line in FILES), "",
        "Open questions that affect the import (markdown/MASTER.md START HERE §7):",
        *(f"- {line}" for line in OPEN_QUESTIONS), "",
        "Manual Optitex check (spec §10), to be recorded in markdown/MASTER.md by the tester:", *TESTER_CHECKS,
    ]
    return "\n".join(lines) + "\n"
