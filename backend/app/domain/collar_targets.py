"""Collar attachment vs optional source calibration targets (demo, not a block)."""


def apply_collar_targets(piece, measurements, attachment):
    piece["source_targets"] = {
        "attachment": attachment,
        "buttoned_length": measurements.get("collar_buttoned_length"),
        "outside_edge": measurements.get("collar_outside_edge"),
    }
    return piece
