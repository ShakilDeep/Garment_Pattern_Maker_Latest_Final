"""Command: apply bounded, optionally scoped measurement edits."""


def bound_changes(changes):
    if any(value <= 0 or value > 500 for value in changes.values()):
        raise ValueError("Measurements must be greater than 0 and at most 500 cm")
    return changes


def scoped_changes(measurement_id, changes):
    if set(changes) != {measurement_id}:
        raise ValueError("Measurement updates must target only the selected measurement")
    return bound_changes(changes)
