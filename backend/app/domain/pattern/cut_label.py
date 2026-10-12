"""A piece label's text: the piece name and its cut counts, stated as the source states them (no new values)."""
from app.domain.pattern.cutting import CutQuantity

SEPARATOR = " · "


def _pairs(count: int) -> str:
    return f"{count} mirrored pair{'s' if count > 1 else ''}"


def cut_text(name: str, cut: CutQuantity) -> str:
    """e.g. "FRT · cut 2 (1 mirrored pair)", "back · cut 1 on fold", "X · cut 2, 1 on fold"."""
    text = f"{name}{SEPARATOR}cut {cut.total}"
    if cut.mirrored_pairs:
        text += f" ({_pairs(cut.mirrored_pairs)})"
    if cut.on_fold:
        text += " on fold" if cut.on_fold == cut.total else f", {cut.on_fold} on fold"
    return text
