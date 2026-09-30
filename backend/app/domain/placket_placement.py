"""Strategy: demo_v1 sleeve placket is anchored at the sleeve placket notch."""


def apply_placket_placement(placket, sleeve):
    anchor = next(mark["point"] for mark in sleeve["marks"] if mark["kind"] == "placket")
    placket["placement"] = {"on": "sleeve", "kind": "placket", "anchor": anchor}
    return placket
