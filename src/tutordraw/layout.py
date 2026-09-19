"""Bounds-based label layout in output pixels."""

from dataclasses import dataclass
import warnings

from drawcv import BoundingBox, Color, Drawable, FillStyle, Line, Point, Rectangle, StrokeStyle, Text

from .errors import LayoutWarning
from .model import Label


@dataclass(frozen=True)
class LabelLayout:
    anchor: Point
    panel: BoundingBox
    leader_end: Point


def label_artwork(label: Label, target: Drawable, width: int, height: int
                  ) -> tuple[LabelLayout, list[Drawable]]:
    # get_bounds includes the transformed stroke but not post-processing effects.
    bounds = target.get_bounds()
    cx, cy = bounds.center.x, bounds.center.y
    anchors = {
        "left": Point(bounds.left, cy), "right": Point(bounds.right, cy),
        "top": Point(cx, bounds.top), "bottom": Point(cx, bounds.bottom),
        "center": Point(cx, cy),
    }
    anchor = anchors[label.anchor]
    text = Text(text=label.text, font_scale=label.font_scale, thickness=1,
                color=Color(28, 43, 65))
    measured = text.get_bounds()
    w, h = measured.width + 2 * label.padding, measured.height + 2 * label.padding
    x, y = anchor.x + label.gap, anchor.y - h / 2
    if label.anchor == "left":
        x = anchor.x - label.gap - w
    elif label.anchor == "top":
        x, y = anchor.x - w / 2, anchor.y - label.gap - h
    elif label.anchor == "bottom":
        x, y = anchor.x - w / 2, anchor.y + label.gap
    x, y = x + label.offset[0], y + label.offset[1]
    panel = BoundingBox(x, y, w, h)
    # Intersect the ray from the panel center toward the target with its edge.
    dx, dy = anchor.x - panel.center.x, anchor.y - panel.center.y
    ratio = max(abs(dx) / (w / 2), abs(dy) / (h / 2))
    end = Point(panel.center.x + dx / ratio, panel.center.y + dy / ratio) if ratio else panel.center
    if x < 0 or y < 0 or panel.right > width or panel.bottom > height:
        warnings.warn(f"Label {label.text!r} extends outside the canvas", LayoutWarning, stacklevel=3)
    artwork: list[Drawable] = []
    if label.leader and ratio > 1:
        artwork.append(Line(start=anchor, end=end, stroke=StrokeStyle(color=Color(75, 104, 140), width=2)))
    artwork.append(Rectangle(position=Point(x, y), width=w, height=h,
                             fill=FillStyle(color=Color.white()),
                             stroke=StrokeStyle(color=Color(194, 207, 223), width=1)))
    text.position = Point(x + label.padding - measured.x, y + label.padding - measured.y)
    artwork.append(text)
    return LabelLayout(anchor, panel, end), artwork
