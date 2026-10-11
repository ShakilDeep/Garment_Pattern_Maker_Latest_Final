"""shirt_v2 sleeve: the 1078375 PDS cap (an S-curve, fuller at the back) on the chart's bicep and cap height,
then the long sleeve body to the pleated wrist as the source style has it (y down from the crown)."""
from app.domain.shirt_v2.curves import Pt, cubic, fractions


def sleeve_outline(m: dict) -> tuple[list[Pt], list[Pt], float, float]:
    """(outline, cap curve, wrist width, sleeve body length); the crown is at (0, 0)."""
    length = m["sleeve_length"] - m["cuff_width"]
    cap, bicep, cuff = m["sleeve_cap_height"], m["half_bicep"], m["cuff_edge_to_edge"]
    wrist = cuff + 2 * m.get("sleeve_pleat_depth", 2)
    if length <= cap or wrist >= 2 * bicep:
        raise ValueError("Sleeve length/cuff dimensions are incompatible with sleeve cap and bicep")
    back = cubic([-bicep, cap], [0, 0], fractions("Sleeve", "UA_back:cap_crown"))
    front = cubic([0, 0], [bicep, cap], fractions("Sleeve", "cap_crown:UA_front"))
    cap_curve = [*back, *front[1:]]
    return [*cap_curve, [wrist / 2, length], [-wrist / 2, length]], cap_curve, wrist, length
