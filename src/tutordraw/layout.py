"""Bounds-based label layout in output pixels."""

from dataclasses import dataclass
import warnings

from drawcv import BoundingBox, Color, Drawable, FillStyle, Line, Point, Rectangle, StrokeStyle, Text

from .errors import LayoutWarning, ValidationError
from .model import Callout, Label
from .text import is_rtl, thai_segments, uses_font_path
from .themes import Theme

# A font-engine size in pixels that matches the built-in renderer's height for
# the same font_scale, measured on this DrawCV release.
FONT_SIZE_PER_SCALE = 24


def annotation_text(content: str, font_scale: float, theme: Theme, font) -> Text:
    """Build one line of annotation text on whichever renderer can draw it."""
    color = Color(*theme.text_color)
    if uses_font_path(content, font is not None):
        return Text(text=content, fonts=(font,),
                    font_size=font_scale * FONT_SIZE_PER_SCALE, color=color)
    return Text(text=content, font_scale=font_scale, thickness=1, color=color)


@dataclass(frozen=True)
class LabelLayout:
    anchor: Point
    panel: BoundingBox
    leader_end: Point


def wrap_text(text: str, font_scale: float, max_width: float, theme: Theme | None = None,
              font=None) -> list[str]:
    """Wrap using the renderer's measurements, splitting oversized words."""
    measure_theme = theme or Theme()

    def fits(value: str) -> bool:
        return annotation_text(value, font_scale, measure_theme, font).get_bounds().width <= max_width

    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        segments = thai_segments(paragraph)
        if segments is not None:
            # Thai pieces already carry their own spacing; never insert any.
            for piece in segments:
                if not current or fits(current + piece):
                    current += piece
                else:
                    lines.append(current.strip())
                    current = piece if piece.strip() else ""
            lines.append(current.strip())
            continue
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if fits(candidate):
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            for char in word:
                if not fits(char):
                    raise ValidationError(f"Callout max_width is too small for character {char!r}")
                if current and not fits(current + char):
                    lines.append(current)
                    current = ""
                current += char
        lines.append(current)
    return lines


def label_artwork(label: Label, target: Drawable, width: int, height: int,
                  theme: Theme | None = None, font=None
                  ) -> tuple[LabelLayout, list[Drawable]]:
    theme = theme or Theme()
    # get_bounds includes the transformed stroke but not post-processing effects.
    bounds = target.get_bounds()
    cx, cy = bounds.center.x, bounds.center.y
    anchors = {
        "left": Point(bounds.left, cy), "right": Point(bounds.right, cy),
        "top": Point(cx, bounds.top), "bottom": Point(cx, bounds.bottom),
        "center": Point(cx, cy),
    }
    anchor = anchors[label.anchor]
    lines = (wrap_text(label.text, label.font_scale, label.max_width, theme, font)
             if isinstance(label, Callout) else [label.text])
    texts = [annotation_text(line, label.font_scale, theme, font) for line in lines]
    measures = [text.get_bounds() for text in texts]
    line_height = max(1, annotation_text("Ag", label.font_scale, theme, font).get_bounds().height,
                      *(m.height for m in measures))
    spacing = label.line_spacing if isinstance(label, Callout) else 1
    w = max(1, *(m.width for m in measures)) + 2 * label.padding
    h = line_height * (1 + (len(lines) - 1) * spacing) + 2 * label.padding
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
        artwork.append(Line(start=anchor, end=end, stroke=StrokeStyle(color=Color(*theme.leader_color), width=theme.leader_width), z_index=0))
    artwork.append(Rectangle(position=Point(x, y), width=w, height=h,
                             fill=FillStyle(color=Color(*theme.panel_color)),
                             stroke=StrokeStyle(color=Color(*theme.border_color), width=theme.border_width), z_index=1))
    # Wrapped right-to-left lines hang from the right edge, not the left.
    rtl = is_rtl(label.text)
    for i, (text, measured) in enumerate(zip(texts, measures)):
        left = x + w - label.padding - measured.width if rtl else x + label.padding
        text.position = Point(left - measured.x,
                              y + label.padding + i * line_height * spacing - measured.y)
        text.z_index = 2
        if lines[i]:
            artwork.append(text)
    return LabelLayout(anchor, panel, end), artwork
