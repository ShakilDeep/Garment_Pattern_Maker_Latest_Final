"""The tester's fill-in record for the manual Optitex check of the T146 kit (spec §10).

Only facts of the kit are filled in (files, checksums, sizes, pieces). Everything Optitex shows is left blank
for the person doing the import, including the menu path, which has never been verified.
"""
from dataclasses import dataclass

BLANK = "________"
NOT_VERIFIED = "Until this form is filled in and recorded in markdown/MASTER.md: Optitex import not yet verified."


@dataclass(frozen=True)
class KitFacts:
    zip_name: str
    sums: dict[str, str]  # file name -> sha256
    sizes: tuple[str, ...]
    pieces: tuple[str, ...]


def _check(text: str) -> str:
    return f"- [ ] pass  [ ] fail: {text}. Notes: {BLANK}"


def record_form(facts: KitFacts) -> str:
    pieces = ", ".join(f"`{name}`" for name in facts.pieces)
    lines = [
        "# Optitex import record: shirt 1078375 (T146)", "",
        f"Tester: {BLANK}  Date: {BLANK}  Optitex version (expected PDS 21.4.x): {BLANK}  PC / OS: {BLANK}", "",
        f"Kit file: `{facts.zip_name}`  sha256 `{facts.sums[facts.zip_name]}`",
        *(f"- `{name}` sha256 `{digest}`" for name, digest in facts.sums.items() if name != facts.zip_name), "",
        "## Import (spec §10 item 1)",
        f"Menu path used: {BLANK}", f"Files chosen (expected base.dxf + grade_rules.rul): {BLANK}", "",
        "## Checks (spec §10 items 2-4)",
        _check(f"piece names are {pieces}"),
        _check("quantities, fold (mirrored halves), grain, notches, sew and cut lines are as in README.txt"),
        _check(f"the size table lists {', '.join(facts.sizes)} and every size nests in the grade view"),
        _check("each piece's area matches the GET /accuracy '<size> <piece> cut area' rows, and its perimeter "
               "and sew area the client PDS, within 0.5 %"), "",
        "## What Optitex showed for the open questions",
        f"- Q4 grain line position: {BLANK}", f"- Q10 piece names: {BLANK}",
        f"- Q12 notches (0.7 cm slits exported; PDS T-notch cut 1.2 cm): {BLANK}",
        f"- `Quantity:` text (integer here; ASTM may expect an R,L form): {BLANK}", "",
        "## Problems found (each becomes a regression test)",
        f"1. {BLANK}  screenshot: {BLANK}", "",
        "## Summary line for the MASTER T146 row",
        (f"`{BLANK} (date) {BLANK} (tester): Optitex {BLANK} imported {facts.zip_name} (sha256 "
         f"{facts.sums[facts.zip_name][:12]}...) via {BLANK}; checks 2-4: {BLANK}; problems: {BLANK}`"), "",
        NOT_VERIFIED,
    ]
    return "\n".join(lines) + "\n"
