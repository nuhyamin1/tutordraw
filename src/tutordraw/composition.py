"""What one rendered frame contains, before it becomes pixels.

Rendering is split in two: composing a working scene with every annotation
placed, then rasterizing it. The composition keeps the geometry that placement
decided, so tests, lint and non-raster exports read it instead of guessing.
"""

from dataclasses import dataclass

from drawcv import BoundingBox, Point, Scene


@dataclass(frozen=True)
class AnnotationLayout:
    """Where one visible label or callout was drawn in this frame."""

    id: str
    kind: str  # "label" or "callout"
    text: str
    target: str  # the target's name, or its ID when unnamed
    anchor: str  # the side actually used, after collision avoidance
    panel: BoundingBox
    leader: tuple[Point, Point] | None
    boxed: bool


@dataclass(frozen=True)
class HighlightLayout:
    target: str
    box: BoundingBox
    width: float


@dataclass(frozen=True)
class MarkLayout:
    """A drawn mark (arrow, brace, measure, angle, number) in this frame."""

    id: str
    kind: str
    text: str | None
    targets: tuple[str, ...]  # names (or IDs) of the targets it refers to
    bounds: BoundingBox  # everything it draws, caption included
    panel: BoundingBox | None  # its caption panel, if it has text
    empty: bool = False  # it had nothing to draw (lint reports EMPTY_MARK)


@dataclass(frozen=True)
class Composition:
    """A working scene plus the layout decisions that produced it."""

    scene: Scene
    step: int
    progress: float
    annotations: tuple[AnnotationLayout, ...]
    highlights: tuple[HighlightLayout, ...]
    targets: dict[str, BoundingBox]  # target name (or ID) -> live bounds
    drawables: dict[str, str]  # target name (or ID) -> drawable ID in `scene`
    marks: tuple[MarkLayout, ...] = ()
    camera: tuple[float, float, float] | None = None  # (scale, tx, ty), None = whole canvas

    def to_dict(self) -> dict:
        """Plain, rounded geometry: stable enough to snapshot and compare."""
        def box(b: BoundingBox) -> list[float]:
            return [round(b.x, 2), round(b.y, 2), round(b.width, 2), round(b.height, 2)]

        def point(p: Point) -> list[float]:
            return [round(p.x, 2), round(p.y, 2)]

        result = {
            "step": self.step,
            "progress": round(self.progress, 4),
            "canvas": [self.scene.width, self.scene.height],
            "targets": {name: box(b) for name, b in sorted(self.targets.items())},
            "highlights": [{"target": h.target, "box": box(h.box), "width": h.width}
                           for h in self.highlights],
            "annotations": [{
                "kind": a.kind, "text": a.text, "target": a.target, "anchor": a.anchor,
                "panel": box(a.panel), "boxed": a.boxed,
                "leader": None if a.leader is None else [point(a.leader[0]), point(a.leader[1])],
            } for a in self.annotations],
        }
        # Only present when used, so snapshots from before marks stay valid.
        if self.marks:
            result["marks"] = [{"kind": m.kind, "text": m.text, "targets": list(m.targets),
                                "bounds": box(m.bounds),
                                "panel": None if m.panel is None else box(m.panel)}
                               for m in self.marks]
        if self.camera is not None:
            result["camera"] = [round(v, 4) for v in self.camera]
        return result
