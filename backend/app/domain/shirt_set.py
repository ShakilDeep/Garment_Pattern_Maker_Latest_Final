"""Factory: sleeve piece plus placket anchored at the construction notch."""
from app.domain.geometry import length, make_piece
from app.domain.placket_placement import apply_placket_placement
from app.domain.sleeve_marks import apply_sleeve_marks


def sleeve_and_placket(measurements, outline, cap_curve, wrist):
    sleeve = apply_sleeve_marks(
        make_piece("Sleeve", outline, seams={"cap": length(cap_curve), "wrist": wrist}),
        measurements,
    )
    width, height = measurements["sleeve_placket_width"], measurements["sleeve_placket_length"]
    placket = make_piece(
        "Sleeve Placket",
        [[0, height], [0, width / 2], [width / 2, 0], [width, width / 2], [width, height]],
    )
    return sleeve, apply_placket_placement(placket, sleeve)
