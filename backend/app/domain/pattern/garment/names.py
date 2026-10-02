"""Where a garment tool cuts, and the ids it gives the points, edges and marks it adds (CAD-03).

Ids are derived from one prefix ("<prefix>.<role>"), so applying a tool to every size yields the same ids.
"""

from dataclasses import dataclass

from app.domain.pattern.ids import AnnotationId, PointId, SegmentId


@dataclass(frozen=True)
class Cut:
    """A point on an outline edge, at the edge's own parameter t (a fraction on lines and arcs)."""

    segment: SegmentId
    t: float


@dataclass(frozen=True)
class DartNames:
    """A dart's leg ends l1 and l2 (in outline order), apex, legs, and the rest of the edge it opens in."""

    l1: PointId
    l2: PointId
    apex: PointId
    leg1: SegmentId
    leg2: SegmentId
    edge: SegmentId

    @classmethod
    def of(cls, prefix: str) -> "DartNames":
        return cls(PointId(f"{prefix}.l1"), PointId(f"{prefix}.l2"), PointId(f"{prefix}.apex"),
                   SegmentId(f"{prefix}.leg1"), SegmentId(f"{prefix}.leg2"), SegmentId(f"{prefix}.edge"))


@dataclass(frozen=True)
class SlashNames:
    """One opened slash: the fixed point q, its moved copy qm, the rest of the edge and the bridging edge."""

    q: PointId
    qm: PointId
    edge: SegmentId
    bridge: SegmentId

    @classmethod
    def of(cls, prefix: str) -> "SlashNames":
        return cls(PointId(f"{prefix}.q"), PointId(f"{prefix}.qm"), SegmentId(f"{prefix}.edge"),
                   SegmentId(f"{prefix}.bridge"))


@dataclass(frozen=True)
class SpreadNames:
    """A parallel spread: both ends of the slash (q, r), their moved copies, edge rests, bridges and marks."""

    q: PointId
    qm: PointId
    r: PointId
    rm: PointId
    e1: SegmentId
    e2: SegmentId
    b1: SegmentId
    b2: SegmentId
    fixed: AnnotationId
    moved: AnnotationId

    @classmethod
    def of(cls, prefix: str) -> "SpreadNames":
        point, segment = (lambda role: PointId(f"{prefix}.{role}")), (lambda role: SegmentId(f"{prefix}.{role}"))
        return cls(point("q"), point("qm"), point("r"), point("rm"), segment("e1"), segment("e2"),
                   segment("b1"), segment("b2"), AnnotationId(f"{prefix}.fixed"), AnnotationId(f"{prefix}.moved"))
