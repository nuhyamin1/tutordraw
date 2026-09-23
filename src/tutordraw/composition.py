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
class Composition:
    """A working scene plus the layout decisions that produced it."""

    scene: Scene
    step: int
    progress: float
    annotations: tuple[AnnotationLayout, ...]
    highlights: tuple[HighlightLayout, ...]
    targets: dict[str, BoundingBox]  # target name (or ID) -> live bounds

    def to_dict(self) -> dict:
        """Plain, rounded geometry: stable enough to snapshot and compare."""
        def box(b: BoundingBox) -> list[float]:
            return [round(b.x, 2), round(b.y, 2), round(b.width, 2), round(b.height, 2)]

        def point(p: Point) -> list[float]:
            return [round(p.x, 2), round(p.y, 2)]

        return {
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
