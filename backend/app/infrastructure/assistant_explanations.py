"""Offline explanations grounded in application-provided evidence."""


def explain(text, context):
    if not context:
        return None
    lines = []
    if "validation" in text or "validate" in text:
        pattern = context["pattern"]
        if not pattern:
            return (
                f"No pattern is available for size {context['size']}. Generate this size before validation."
            )
        if pattern.get("stale"):
            lines.append(
                "This pattern is stale. Regenerate from current inputs before relying on validation."
            )
        lines.extend(
            f"{v['severity']}: {v['message']} Next: {v.get('action') or 'Open Validation Center.'}"
            for v in context["validation"]
        )
        if not lines:
            lines.append(
                "No retained validation warnings or errors for this size. This does not certify physical fit."
            )
    elif "selected" in text or "this piece" in text:
        piece = context["selected_piece"]
        if not piece:
            return "Select a piece for this size to inspect its dimensions and seam inventory."
        lines.append(
            f"{piece['name']}: {piece['width']} × {piece['height']} cm; cut quantity {piece['quantity']}."
        )
        seams = "; ".join(f"{name.replace('_', ' ')}: {value:.2f} cm"
                          for name, value in (piece.get('seams') or {}).items())
        lines.append(f"Measured seams: {seams or 'No seam measurements recorded'}. "
                     "These are demo geometry, not certified production rules.")
    elif any(word in text for word in ("ambigu", "conflict", "document", "source")):
        lines.extend(
            f"{r['name']}: {r['why']} Source: {r['source']}"
            for r in context["requirements"]
            if r["status"] in ("AMBIGUOUS", "CONFLICTING")
        )
        lines.extend(
            f"{i['label']} — {i['source']}, page {i.get('page', 'n/a')}: {i['issue']}"
            for i in context["source_issues"]
        )
        if not lines:
            lines.append(
                "No retained source ambiguities for this size. Confirm the original documents before drafting."
            )
    elif any(word in text for word in ("requirement", "unresolved", "missing")):
        lines.extend(
            f"{r['name']} ({'blocking' if r['blocking'] else 'nonblocking'}): {r['why']}"
            for r in context["requirements"]
        )
        if not lines:
            lines.append(
                "No unresolved requirements for this size. Production accuracy still requires physical validation."
            )
    if not lines:
        return None
    answer = "\n".join(lines)
    if len(answer) > 3500 or context["truncated"]:
        answer = (
            answer[:3500]
            + "\nSummary shortened. Open Requirements, Source Review, or Validation Center for all evidence."
        )
    return answer
