"""Bounds-based label layout in output pixels."""

from dataclasses import dataclass
import warnings

from drawcv import BoundingBox, Color, Drawable, FillStyle, Line, Point, Rectangle, StrokeStyle, Text

from .adapters.drawcv import crisp_rect
from .errors import LayoutWarning, ValidationError
from .model import Callout, Label
from .text import is_rtl, thai_segments, uses_font_path
from .themes import Theme

# A font-engine size in pixels that matches the built-in renderer's height for
# the same font_scale, measured on this DrawCV release.
FONT_SIZE_PER_SCALE = 24
# px a leader may stop short of its target's outline before it is taken on to it (`ink_point`).
INK_GAP = 6.0


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


@dataclass(frozen=True)
class Placement:
    """A resolved choice: which anchor to use, and how far to nudge off it.

    The nudge is in canvas pixels and is added to the label's authored offset,
    so it keeps its meaning against whatever bounds the current frame has.
    """

    anchor: str
    dx: float = 0.0
    dy: float = 0.0


@dataclass(frozen=True)
class Measured:
    """Panel contents and size: depends on the text, not on where it goes."""

    lines: tuple[str, ...]
    texts: tuple
    measures: tuple
    line_height: float
    spacing: float
    width: float
    height: float


def anchor_points(bounds: BoundingBox) -> dict[str, Point]:
    """The five attachment points of a target's world-space bounds."""
    cx, cy = bounds.center.x, bounds.center.y
    return {
        "left": Point(bounds.left, cy), "right": Point(bounds.right, cy),
        "top": Point(cx, bounds.top), "bottom": Point(cx, bounds.bottom),
        "center": Point(cx, cy),
    }


def ink_point(target: Drawable, point: Point) -> Point:
    """The point of the target's own outline nearest `point`, where a leader to it should end.

    A bounds point (`anchor_points`) is on a rectangle or a circle, but can be
    in empty space beside a triangle, a slanted line or any irregular shape.
    A point already on the target's fill or its stroke's ink, or within
    INK_GAP of it, keeps `point`; so do a group (a kit: its bounds describe
    it), text and a piece of an equation (a leader goes to text as a block),
    and a target whose outline cannot be traced.
    """
    from drawcv import Group

    from .arrange import _kit

    if isinstance(target, (Group, Text)):
        return point
    parent = target.parent
    while parent is not None:  # typeset maths is text too: a leader goes to its block
        if _kit(parent) == "equation":
            return point
        parent = getattr(parent, "parent", None)
    try:
        if getattr(target, "fill", None) is not None and target.contains_point(point):
            return point
        contours = target.to_path(preserve_world_transform=True).flatten_world(tolerance=1.0)
    except Exception:
        return point
    best, nearest = point, float("inf")
    for points in contours:
        for a, b in zip(points, points[1:]):
            dx, dy = b.x - a.x, b.y - a.y
            length = dx * dx + dy * dy
            t = 0.0 if not length else max(0.0, min(1.0, ((point.x - a.x) * dx + (point.y - a.y) * dy) / length))
            x, y = a.x + t * dx, a.y + t * dy
            distance = (point.x - x) ** 2 + (point.y - y) ** 2
            if distance < nearest:
                best, nearest = Point(x, y), distance
    # A point on the stroke's ink (bounds include half its width), or no farther off it than INK_GAP (the
    # opening of a letter, a rounded corner), is on the shape already: unchanged.
    stroke = getattr(target, "stroke", None)
    half = (getattr(stroke, "width", 1.0) or 1.0) / 2 if stroke is not None else 0.0
    return point if nearest <= (half + INK_GAP) ** 2 else best


def measure_label(label: Label, theme: Theme | None = None, font=None) -> Measured:
    """Lay the text out and size its panel, independently of any position."""
    theme = theme or Theme()
    lines = (wrap_text(label.text, label.font_scale, label.max_width, theme, font)
             if isinstance(label, Callout) else [label.text])
    texts = [annotation_text(line, label.font_scale, theme, font) for line in lines]
    measures = [text.get_bounds() for text in texts]
    line_height = max(1, annotation_text("Ag", label.font_scale, theme, font).get_bounds().height,
                      *(m.height for m in measures))
    spacing = label.line_spacing if isinstance(label, Callout) else 1
    return Measured(
        tuple(lines), tuple(texts), tuple(measures), line_height, spacing,
        max(1, *(m.width for m in measures)) + 2 * label.padding,
        line_height * (1 + (len(lines) - 1) * spacing) + 2 * label.padding)


def place_panel(point: Point, anchor: str, width: float, height: float, gap: float,
                offset: tuple[float, float] = (0.0, 0.0)) -> BoundingBox:
    """Put a panel of this size beside an anchor point. Center sits to the right."""
    x, y = point.x + gap, point.y - height / 2
    if anchor == "left":
        x = point.x - gap - width
    elif anchor == "top":
        x, y = point.x - width / 2, point.y - gap - height
    elif anchor == "bottom":
        x, y = point.x - width / 2, point.y + gap
    return BoundingBox(x + offset[0], y + offset[1], width, height)


def clamp_panel(panel: BoundingBox, width: float, height: float) -> BoundingBox:
    """Shift a panel minimally back onto the canvas; one too big is left alone.

    This is re-applied every frame rather than frozen with the placement: it is
    continuous, so a panel tracking a moving target slides along the edge
    instead of jumping, and it cannot be defeated by an offset that was chosen
    against a different frame's bounds.
    """
    x = min(max(panel.x, 0.0), width - panel.width) if panel.width <= width else panel.x
    y = min(max(panel.y, 0.0), height - panel.height) if panel.height <= height else panel.y
    if (x, y) == (panel.x, panel.y):
        return panel
    return BoundingBox(x, y, panel.width, panel.height)


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
                  theme: Theme | None = None, font=None,
                  placement: Placement | None = None, measured: Measured | None = None,
                  progress: float = 1.0) -> tuple[LabelLayout, list[Drawable]]:
    """Build one annotation's artwork, optionally at a resolved placement.

    Without a placement this is the authored anchor, gap and offset exactly, so
    a single label lays out the same as it always has. Below full `progress`
    only the leader is drawn, that far along; the panel and text follow once it
    arrives.
    """
    theme = theme or Theme()
    # get_bounds includes the transformed stroke but not post-processing effects.
    points = anchor_points(target.get_bounds())
    measured = measured if measured is not None else measure_label(label, theme, font)
    lines, texts, measures = measured.lines, measured.texts, measured.measures
    line_height, spacing = measured.line_height, measured.spacing
    side = label.anchor if placement is None else placement.anchor
    nudge = (0.0, 0.0) if placement is None else (placement.dx, placement.dy)
    anchor = points[side]
    w, h = measured.width, measured.height
    panel = place_panel(anchor, side, w, h, label.gap,
                        (label.offset[0] + nudge[0], label.offset[1] + nudge[1]))
    if placement is not None:
        # Only under collision avoidance; without it the authored offset stands.
        panel = clamp_panel(panel, width, height)
    x, y = panel.x, panel.y
    # The panel sits by a point of the target's bounds; the leader goes on to the shape itself.
    if label.leader:
        anchor = ink_point(target, anchor)
    # Intersect the ray from the panel center toward the target with its edge.
    dx, dy = anchor.x - panel.center.x, anchor.y - panel.center.y
    ratio = max(abs(dx) / (w / 2), abs(dy) / (h / 2))
    end = Point(panel.center.x + dx / ratio, panel.center.y + dy / ratio) if ratio else panel.center
    if x < 0 or y < 0 or panel.right > width or panel.bottom > height:
        warnings.warn(f"Label {label.text!r} extends outside the canvas", LayoutWarning, stacklevel=3)
    artwork: list[Drawable] = []
    if label.leader and ratio > 1:
        leader = Line(start=anchor, end=end, stroke=StrokeStyle(color=Color(*theme.leader_color), width=theme.leader_width), z_index=0,
                      id=f"td-{label.id}-leader")
        if progress < 1:
            leader.render_progress = progress
        artwork.append(leader)
    if progress < 1:
        return LabelLayout(anchor, panel, end), artwork
    if label.box:
        bx, by, bw, bh = crisp_rect(x, y, w, h, theme.border_width)
        artwork.append(Rectangle(position=Point(bx, by), width=bw, height=bh, id=f"td-{label.id}-panel",
                                 fill=FillStyle(color=Color(*theme.panel_color)),
                                 stroke=StrokeStyle(color=Color(*theme.border_color), width=theme.border_width), z_index=1))
    # Wrapped right-to-left lines hang from the right edge, not the left.
    rtl = is_rtl(label.text)
    for i, (text, measure) in enumerate(zip(texts, measures)):
        left = x + w - label.padding - measure.width if rtl else x + label.padding
        text.position = Point(left - measure.x,
                              y + label.padding + i * line_height * spacing - measure.y)
        text.z_index = 2
        # Stable IDs, so the same annotation matches itself across frames and
        # steps in SVG output; td-<owner>-<role> also tells a player its timing.
        text.id = f"td-{label.id}-t{i}"
        if lines[i]:
            if not label.box and theme.halo_width > 0:
                artwork.extend(_halo(lines[i], text.position, label, theme, font, text.id))
            artwork.append(text)
    return LabelLayout(anchor, panel, end), artwork


def _halo(line: str, position: Point, label: Label, theme: Theme, font, owner: str) -> list[Text]:
    """Copies of a line in panel_color around it, so bare text reads on any art.

    DrawCV text has no stroke, so the outline is eight offset copies beneath
    the real text; at halo widths of a few pixels they read as one outline.
    """
    copies = []
    r = theme.halo_width
    for k, (dx, dy) in enumerate(((r, 0), (-r, 0), (0, r), (0, -r),
                   (r * 0.7071, r * 0.7071), (-r * 0.7071, r * 0.7071),
                   (r * 0.7071, -r * 0.7071), (-r * 0.7071, -r * 0.7071))):
        copy = annotation_text(line, label.font_scale, theme, font)
        copy.color = Color(*theme.panel_color)
        copy.position = Point(position.x + dx, position.y + dy)
        copy.z_index = 1
        copy.id = f"{owner}-halo{k}"
        copies.append(copy)
    return copies
