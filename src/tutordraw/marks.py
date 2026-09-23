"""Geometry and artwork for step marks: arrows, braces, measures, angles, numbers.

Everything here is a pure function of target bounds (and the camera, for fixed
points), so the planner can evaluate a mark at the step's end state to keep
labels clear of it, and rendering can evaluate it on live bounds each frame.
Strokes are DrawCV Paths so `render_progress` draws them on; text and panels
appear only once the stroke is complete.
"""

from dataclasses import dataclass
import math

from drawcv import BoundingBox, Circle, Color, Drawable, FillStyle, Path, Point, Polygon, Rectangle, StrokeStyle

from .adapters.drawcv import crisp_rect
from .camera import State, to_screen
from .layout import annotation_text, clamp_panel, place_panel
from .model import Mark, Target
from .themes import Theme

GAP = 6.0  # between a target and the end of an arrow or a brace
BRACE_DEPTH = 12.0


@dataclass(frozen=True)
class MarkDrawing:
    artwork: tuple[Drawable, ...]
    bounds: BoundingBox  # everything drawn, text included, at full progress
    panel: BoundingBox | None  # the caption's panel, if any
    empty: bool = False  # nothing to draw, e.g. an arrow between shared centres


def _union(boxes) -> BoundingBox:
    boxes = [b for b in boxes if b is not None]
    left, top = min(b.left for b in boxes), min(b.top for b in boxes)
    right, bottom = max(b.right for b in boxes), max(b.bottom for b in boxes)
    return BoundingBox(left, top, right - left, bottom - top)


def ref_box(ref, bounds: dict[str, BoundingBox], camera: State | None) -> BoundingBox:
    """A target's live bounds, or a fixed scene point seen through the camera."""
    if isinstance(ref, Target):
        return bounds[ref.drawable_id]
    point = to_screen(camera, *ref)
    return BoundingBox(point.x, point.y, 0, 0)


def _stroke(theme: Theme) -> StrokeStyle:
    return StrokeStyle(color=Color(*theme.leader_color), width=theme.leader_width)


def _path(points: list[Point], theme: Theme) -> Path:
    path = Path(stroke=_stroke(theme))
    path.move_to(points[0])
    for point in points[1:]:
        path.line_to(point)
    return path


def _head(tip: Point, direction: Point, theme: Theme) -> Polygon:
    """A filled arrowhead with its tip at `tip`, pointing along `direction`."""
    length = 6 + 3 * theme.leader_width
    norm = math.hypot(direction.x, direction.y) or 1.0
    ux, uy = direction.x / norm, direction.y / norm
    bx, by = tip.x - ux * length, tip.y - uy * length
    half = length * 0.5
    return Polygon(vertices=[tip, Point(bx - uy * half, by + ux * half), Point(bx + uy * half, by - ux * half)],
                   fill=FillStyle(color=Color(*theme.leader_color)), z_index=0)


def _exit(box: BoundingBox, toward: Point, gap: float) -> Point:
    """Where a ray from the box centre toward `toward` leaves it, plus a gap."""
    c = box.center
    dx, dy = toward.x - c.x, toward.y - c.y
    length = math.hypot(dx, dy)
    if length == 0:
        return c
    scales = []
    if dx:
        scales.append(abs(box.width / 2 / dx))
    if dy:
        scales.append(abs(box.height / 2 / dy))
    t = min(scales) if scales else 0.0
    return Point(c.x + dx * t + dx / length * gap, c.y + dy * t + dy / length * gap)


def _caption(text: str, theme: Theme, font) -> tuple[float, float, list, float]:
    """Measure a one-line caption; return its panel size, text and padding."""
    pad = max(3.0, theme.padding * 0.6)
    line = annotation_text(text, theme.font_scale, theme, font)
    measure = line.get_bounds()
    height = max(measure.height, annotation_text("Ag", theme.font_scale, theme, font).get_bounds().height)
    return measure.width + 2 * pad, height + 2 * pad, [line, measure], pad


def _caption_artwork(panel: BoundingBox, parts: list, pad: float, theme: Theme) -> list[Drawable]:
    line, measure = parts
    bx, by, bw, bh = crisp_rect(panel.x, panel.y, panel.width, panel.height, theme.border_width)
    box = Rectangle(position=Point(bx, by), width=bw, height=bh,
                    fill=FillStyle(color=Color(*theme.panel_color)),
                    stroke=StrokeStyle(color=Color(*theme.border_color), width=theme.border_width),
                    z_index=1)
    line.position = Point(panel.x + pad - measure.x, panel.y + pad - measure.y)
    line.z_index = 2
    return [box, line]


def _centred(point: Point, width: float, height: float) -> BoundingBox:
    return BoundingBox(point.x - width / 2, point.y - height / 2, width, height)


def mark_drawing(mark: Mark, bounds: dict[str, BoundingBox], camera: State | None,
                 theme: Theme, font, canvas: tuple[float, float], progress: float = 1.0
                 ) -> MarkDrawing:
    """Build a mark at `progress` (0..1). Bounds and panel are its full extent."""
    builder = {"arrow": _arrow, "brace": _brace, "measure": _measure,
               "angle": _angle, "number": _number}[mark.kind]
    built = builder(mark, bounds, camera, theme, font)
    if built is None:
        centre = ref_box(mark.refs[0], bounds, camera).center
        return MarkDrawing((), BoundingBox(centre.x, centre.y, 0, 0), None, empty=True)
    strokes, heads, anchor_panel, extent = built
    # Stable IDs: s = strokes that draw on, h = heads/badges, then the caption.
    for k, stroke in enumerate(strokes):
        stroke.render_progress = progress
        stroke.id = f"td-{mark.id}-s{k}"
    artwork: list[Drawable] = list(strokes) if progress > 0 else []
    for k, head in enumerate(heads):
        tip = head(progress)
        if tip is not None and progress > 0:
            tip.id = f"td-{mark.id}-h{k}"
            artwork.append(tip)
    panel = None
    if anchor_panel is not None:
        panel, parts, pad = anchor_panel
        panel = clamp_panel(panel, *canvas)
        if progress >= 1:
            box, line = _caption_artwork(panel, parts, pad, theme)
            box.id, line.id = f"td-{mark.id}-panel", f"td-{mark.id}-text"
            artwork.extend((box, line))
    stroke_boxes = [s.get_bounds() for s in strokes] if strokes else []
    return MarkDrawing(tuple(artwork), _union([*stroke_boxes, *extent, panel]), panel)


def _arrow(mark, bounds, camera, theme, font):
    a, b = (ref_box(ref, bounds, camera) for ref in mark.refs)
    # A fixed point is an exact end; only a target's end keeps a gap from it.
    start = _exit(a, b.center, GAP) if isinstance(mark.refs[0], Target) else a.center
    end = _exit(b, a.center, GAP) if isinstance(mark.refs[1], Target) else b.center
    if math.hypot(end.x - start.x, end.y - start.y) < 1.0:
        # Shared centres (a shape inside another, concentric) leave no arrow
        # to draw. Drawing nothing beats failing the whole frame; lint says why.
        return None
    dx, dy = end.x - start.x, end.y - start.y
    length = math.hypot(dx, dy) or 1.0
    bend = mark.options["bend"]
    # Normal pointing up-screen for a straight arrow, so captions sit above it.
    nx, ny = -dy / length, dx / length
    if ny > 0 or (ny == 0 and nx < 0):
        nx, ny = -nx, -ny
    side = 1.0 if bend >= 0 else -1.0
    mid = Point((start.x + end.x) / 2 + nx * bend * length, (start.y + end.y) / 2 + ny * bend * length)
    path = Path(stroke=_stroke(theme))
    path.move_to(start)
    # A quadratic through `mid`'s control point, written as the equivalent cubic.
    c1 = Point(start.x + 2 / 3 * (mid.x - start.x), start.y + 2 / 3 * (mid.y - start.y))
    c2 = Point(end.x + 2 / 3 * (mid.x - end.x), end.y + 2 / 3 * (mid.y - end.y))
    path.cubic_to(c1, c2, end)

    def tip(progress):
        if progress <= 0:
            return None
        p = min(progress, 1.0)
        return _head(path.point_at(p), path.tangent_at(p), theme)

    heads = [tip]
    if mark.options["both"]:
        heads.append(lambda progress: None if progress <= 0 else _head(
            start, Point(-path.tangent_at(0).x, -path.tangent_at(0).y), theme))
    caption = None
    if mark.text is not None:
        width, height, parts, pad = _caption(mark.text, theme, font)
        centre = path.point_at(0.5)
        # Half the panel's extent along the normal, so it clears the shaft at any angle.
        lift = (abs(nx) * width / 2 + abs(ny) * height / 2 + 6) * side
        caption = (_centred(Point(centre.x + nx * lift, centre.y + ny * lift), width, height), parts, pad)
    return [path], heads, caption, []


def _brace(mark, bounds, camera, theme, font):
    box = _union(ref_box(ref, bounds, camera) for ref in mark.refs)
    side = mark.options["side"]
    horizontal = side in ("top", "bottom")
    length = box.width if horizontal else box.height
    d, h = BRACE_DEPTH, min(BRACE_DEPTH, length / 4)
    # Drawn in local (u, v): along +u, bulging toward +v, tip at (length / 2, d).
    def world(u, v):
        if side == "bottom":
            return Point(box.left + u, box.bottom + GAP + v)
        if side == "top":
            return Point(box.left + u, box.top - GAP - v)
        if side == "right":
            return Point(box.right + GAP + v, box.top + u)
        return Point(box.left - GAP - v, box.top + u)

    path = Path(stroke=_stroke(theme))
    path.move_to(world(0, 0))

    def quad(p0, q, p2):
        c1 = (p0[0] + 2 / 3 * (q[0] - p0[0]), p0[1] + 2 / 3 * (q[1] - p0[1]))
        c2 = (p2[0] + 2 / 3 * (q[0] - p2[0]), p2[1] + 2 / 3 * (q[1] - p2[1]))
        path.cubic_to(world(*c1), world(*c2), world(*p2))

    quad((0, 0), (0, d / 2), (h, d / 2))
    path.line_to(world(length / 2 - h, d / 2))
    quad((length / 2 - h, d / 2), (length / 2, d / 2), (length / 2, d))
    quad((length / 2, d), (length / 2, d / 2), (length / 2 + h, d / 2))
    path.line_to(world(length - h, d / 2))
    quad((length - h, d / 2), (length, d / 2), (length, 0))
    caption = None
    if mark.text is not None:
        width, height, parts, pad = _caption(mark.text, theme, font)
        caption = (place_panel(world(length / 2, d), side, width, height, GAP), parts, pad)
    return [path], [], caption, []


def _measure(mark, bounds, camera, theme, font):
    axis, offset = mark.options["axis"], mark.options["offset"]
    boxes = [ref_box(ref, bounds, camera) for ref in mark.refs]
    strokes = []
    if len(boxes) == 1:
        b = boxes[0]
        ends = ((b.left, b.bottom), (b.right, b.bottom)) if axis == "x" else ((b.right, b.top), (b.right, b.bottom))
        edges = [b, b]
    else:
        ends = tuple((box.center.x, box.center.y) for box in boxes)
        edges = boxes
    if axis == "x":
        y = max(edge.bottom for edge in edges) + offset
        a, b = Point(ends[0][0], y), Point(ends[1][0], y)
        for (x, _), edge in zip(ends, edges):
            strokes.append(_path([Point(x, edge.bottom + 3), Point(x, y + 5)], theme))
    elif axis == "y":
        x = max(edge.right for edge in edges) + offset
        a, b = Point(x, ends[0][1]), Point(x, ends[1][1])
        for (_, y), edge in zip(ends, edges):
            strokes.append(_path([Point(edge.right + 3, y), Point(x + 5, y)], theme))
    else:
        a, b = Point(*ends[0]), Point(*ends[1])
        # Lift the line off whatever edge it measures, toward the top of the
        # screen (as captions on arrows go), with extension lines back to it.
        length = math.hypot(b.x - a.x, b.y - a.y) or 1.0
        nx, ny = -(b.y - a.y) / length, (b.x - a.x) / length
        if ny > 0 or (ny == 0 and nx < 0):
            nx, ny = -nx, -ny
        if offset > 0:
            lifted = [Point(p.x + nx * offset, p.y + ny * offset) for p in (a, b)]
            for p, q in zip((a, b), lifted):
                strokes.append(_path([Point(p.x + nx * 3, p.y + ny * 3),
                                      Point(q.x + nx * 5, q.y + ny * 5)], theme))
            a, b = lifted
    line = _path([a, b], theme)
    strokes.append(line)
    direction = Point(b.x - a.x, b.y - a.y)
    heads = [lambda p: _head(b, direction, theme) if p >= 1 else None,
             lambda p: _head(a, Point(-direction.x, -direction.y), theme) if p >= 1 else None]
    caption = None
    if mark.text is not None:
        width, height, parts, pad = _caption(mark.text, theme, font)
        caption = (_centred(Point((a.x + b.x) / 2, (a.y + b.y) / 2), width, height), parts, pad)
    return strokes, heads, caption, []


def _angle(mark, bounds, camera, theme, font):
    vertex, first, second = (ref_box(ref, bounds, camera).center for ref in mark.refs)
    radius = mark.options["radius"]
    start = math.atan2(first.y - vertex.y, first.x - vertex.x)
    sweep = math.atan2(second.y - vertex.y, second.x - vertex.x) - start
    sweep = (sweep + math.pi) % (2 * math.pi) - math.pi  # the smaller way round
    count = max(2, int(abs(math.degrees(sweep)) // 4) + 2)
    arc = [Point(vertex.x + radius * math.cos(start + sweep * i / (count - 1)),
                 vertex.y + radius * math.sin(start + sweep * i / (count - 1))) for i in range(count)]
    caption = None
    if mark.text is not None:
        width, height, parts, pad = _caption(mark.text, theme, font)
        middle = start + sweep / 2
        reach = radius + 4 + math.hypot(width, height) / 2
        caption = (_centred(Point(vertex.x + reach * math.cos(middle), vertex.y + reach * math.sin(middle)),
                            width, height), parts, pad)
    return [_path(arc, theme)], [], caption, []


def _number(mark, bounds, camera, theme, font):
    box = ref_box(mark.refs[0], bounds, camera)
    text = annotation_text(str(mark.options["n"]), theme.font_scale * 0.8, theme, font)
    text.color = Color(255, 255, 255)
    measure = text.get_bounds()
    radius = max(10.0, max(measure.width, measure.height) / 2 + 5)
    corner = mark.options["corner"]
    x = box.left if corner.endswith("left") else box.right
    y = box.top if corner.startswith("top") else box.bottom
    # Tucked half over the corner so it reads as belonging to that target.
    cx = x - radius / 2 if corner.endswith("left") else x + radius / 2
    cy = y - radius / 2 if corner.startswith("top") else y + radius / 2
    badge = Circle(center=Point(cx, cy), radius=radius, fill=FillStyle(color=Color(*theme.highlight_color)),
                   stroke=StrokeStyle(color=Color(255, 255, 255), width=2), z_index=1)
    text.position = Point(cx - measure.width / 2 - measure.x, cy - measure.height / 2 - measure.y)
    text.z_index = 2
    extent = BoundingBox(cx - radius - 1, cy - radius - 1, 2 * radius + 2, 2 * radius + 2)
    # Numbers appear whole: they are returned as fixed "heads" shown at any progress.
    return [], [lambda p: badge if p > 0 else None, lambda p: text if p > 0 else None], None, [extent]
