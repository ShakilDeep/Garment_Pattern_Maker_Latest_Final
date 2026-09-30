"""Strategy: demo_v1 back/yoke shoulder from source forward-shoulder values."""


def back_shoulder_half(shoulder: float, measurements: dict) -> float:
    neck = float(measurements.get("forward_shoulder_neck") or 0)
    arm = float(measurements.get("forward_shoulder_armhole") or 0)
    offset = max(0.0, arm - neck)
    half = shoulder - offset
    if half <= 0:
        raise ValueError("Forward-shoulder offset exceeds half shoulder width")
    return half
