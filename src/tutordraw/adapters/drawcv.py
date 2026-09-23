"""DrawCV operations isolated from the teaching model."""

from contextlib import contextmanager
from copy import deepcopy
import math
from pathlib import Path

from drawcv import Color, Drawable, FillStyle, Group, Point, Scene

from ..errors import SceneCopyError, ValidationError


def index_scene(scene: Scene) -> dict[str, Drawable]:
    """Traverse actual scene contents, detecting ambiguous IDs."""
    result: dict[str, Drawable] = {}

    def visit(obj: Drawable) -> None:
        if obj.id in result:
            raise ValidationError(f"Duplicate drawable ID: {obj.id!r}")
        result[obj.id] = obj
        if isinstance(obj, Group):
            for child in obj.children:
                visit(child)

    for obj in scene.objects:
        visit(obj)
    return result


def copy_scene(scene: Scene) -> Scene:
    """Copy through the public document API; never mutate the source."""
    source = index_scene(scene)
    try:
        copied = Scene.from_dict(deepcopy(scene.to_dict()))
        copied_index = index_scene(copied)
        if source.keys() != copied_index.keys():
            raise ValueError("Scene round trip changed drawable IDs")
        for key, obj in source.items():
            if type(copied_index[key]) is not type(obj):
                raise ValueError(f"Scene round trip changed drawable type: {key}")
        return copied
    except Exception as exc:
        raise SceneCopyError(f"Unable to copy DrawCV scene: {exc}") from exc


def overlay_layer(scene: Scene) -> str:
    name = "__tutordraw__"
    while scene.get_layer(name) is not None:
        name += "_"
    scene.create_layer(name)
    return name


def supports_fill(drawable: Drawable) -> bool:
    """Shapes carry a FillStyle; text carries a plain color. Lines and groups have neither."""
    return hasattr(drawable, "fill") or hasattr(drawable, "color")


def set_fill(drawable: Drawable, color: tuple[int, int, int]) -> None:
    """Recolor a working copy, keeping the fill's other settings intact."""
    tint = Color(*color)
    if hasattr(drawable, "fill"):
        existing = drawable.fill
        # FillStyle holds a private paint field, so replace() cannot be used.
        drawable.fill = (FillStyle(color=tint) if existing is None else
                         FillStyle(color=tint, opacity=existing.opacity, enabled=existing.enabled))
    elif hasattr(drawable, "color"):
        drawable.color = tint
    else:
        raise ValidationError(f"{type(drawable).__name__} has no fill or color to set")


def translate(drawable: Drawable, dx: float, dy: float) -> None:
    """Shift a working copy relative to wherever the source placed it."""
    drawable.transform.translation_x += dx
    drawable.transform.translation_y += dy


def load_font(value) -> "FontAsset":
    """Accept a font file path, raw bytes, or an already-built FontAsset."""
    from drawcv import FontAsset

    if isinstance(value, FontAsset):
        return value
    try:
        if isinstance(value, (bytes, bytearray)):
            return FontAsset(name="supplied", data=bytes(value))
        if isinstance(value, (str, Path)):
            return FontAsset.from_file(str(value))
    except Exception as exc:
        raise ValidationError(f"Unusable font: {exc}") from exc
    raise ValidationError("font must be a path, bytes, or a DrawCV FontAsset")


def typography_error(exc: Exception) -> ValidationError | None:
    """Turn DrawCV's missing-engine failure into TutorDraw's own instruction."""
    if "optional dependencies" in str(exc):
        return ValidationError(
            "Shaped scripts need DrawCV's font engine: pip install \"tutordraw[typography]\"")
    return None


@contextmanager
def typography_errors():
    """Replace DrawCV's missing-engine message with TutorDraw's install command."""
    try:
        yield
    except Exception as exc:
        translated = typography_error(exc)
        if translated is not None:
            raise translated from exc
        raise


def paint_color(paint) -> tuple[int, int, int] | None:
    """Reduce any DrawCV paint to the one colour a blend can start from.

    A gradient has no single colour, so use the unweighted mean of its stops:
    simple and predictable, like the RGB interpolation it feeds. Image paints
    have no stops and no colour, so they report None.
    """
    if paint is None:
        return None
    if isinstance(paint, Color):
        return (paint.r, paint.g, paint.b)
    stops = getattr(paint, "stops", ())
    if not stops:
        return None
    return tuple(int(round(sum(getattr(stop.color, channel) for stop in stops) / len(stops)))
                 for channel in ("r", "g", "b"))


def current_fill(drawable: Drawable) -> tuple[int, int, int] | None:
    """The colour an animation should start from, or None if it has none."""
    fill = getattr(drawable, "fill", None)
    # fill.paint, not fill.color: the shorthand raises on gradients and images.
    paint = fill.paint if fill is not None else getattr(drawable, "color", None)
    return paint_color(paint)


def crisp_rect(x: float, y: float, width: float, height: float,
               stroke_width: float) -> tuple[float, float, float, float]:
    """Snap a stroked rectangle's edges inward so its stroke covers whole pixels.

    DrawCV 0.11 rasterizes like SVG: pixel k spans [k, k + 1], so a 1 px stroke
    centred on a whole coordinate smears across two half-covered pixels. An odd
    integer width is centred on .5, an even one on a whole coordinate. Edges move
    inward by under a pixel, so the rectangle never grows past its measured
    footprint and a panel flush with the canvas keeps its border on screen.
    Other widths cannot be crisp and are returned unchanged.
    """
    if stroke_width != int(stroke_width):
        return x, y, width, height
    half = 0.5 if int(stroke_width) % 2 else 0.0
    left, top = math.ceil(x - half) + half, math.ceil(y - half) + half
    right = math.floor(x + width - half) + half
    bottom = math.floor(y + height - half) + half
    if right <= left or bottom <= top:
        return x, y, width, height
    return left, top, right - left, bottom - top


def outline_path(drawable: Drawable, padding: float):
    """The drawable's own closed outline in world space, grown by padding.

    Groups, text and open shapes cannot be outlined; the error says to use a
    box highlight instead, so the caller can act on it.

    Grown here rather than with DrawCV's Path.offset, which took 0.7-2.4 s for
    one circle on 0.11.0 (it maps every point to world space, recomputing the
    path's bounds each time). flatten_world takes ~2 ms; see DECISIONS.md.
    """
    from drawcv import Path

    try:
        contours = drawable.to_path(preserve_world_transform=True).flatten_world(
            tolerance=0.3, include_closed=True)
    except Exception as exc:
        raise ValidationError(
            f"shape='outline' needs a closed shape; {type(drawable).__name__} cannot be "
            f"outlined ({exc}). Use shape='box' instead.") from exc
    if not contours or not all(closed and len(points) >= 3 for points, closed in contours):
        raise ValidationError(
            f"shape='outline' needs a closed shape; {type(drawable).__name__} is open. "
            "Use shape='box' instead.")
    path = Path()
    for points, _ in contours:
        grown = _grow(points, padding)
        path.move_to(grown[0])
        for point in grown[1:]:
            path.line_to(point)
        path.close()
    path.fill = None
    return path


def _grow(points: list[Point], padding: float) -> list[Point]:
    """Offset a closed polygon outward, with round corners where it turns sharply.

    Each contour uses its own winding, so a hole (wound the other way) grows
    into itself, which is the same thing as the filled region growing.
    """
    import math

    if points[0].x == points[-1].x and points[0].y == points[-1].y:
        points = points[:-1]
    if padding <= 0:
        return list(points)
    count = len(points)
    area = sum(points[i].x * points[(i + 1) % count].y - points[(i + 1) % count].x * points[i].y
               for i in range(count))
    sign = 1.0 if area > 0 else -1.0

    def normal(a: Point, b: Point) -> tuple[float, float]:
        dx, dy = b.x - a.x, b.y - a.y
        length = math.hypot(dx, dy) or 1.0
        return sign * dy / length, -sign * dx / length

    result: list[Point] = []
    for i in range(count):
        prev, here, nxt = points[i - 1], points[i], points[(i + 1) % count]
        n1, n2 = normal(prev, here), normal(here, nxt)
        turn = math.atan2(n1[0] * n2[1] - n1[1] * n2[0], n1[0] * n2[0] + n1[1] * n2[1])
        # At a convex corner the normals turn the same way the contour winds.
        convex = turn * sign > 0
        if convex and abs(turn) > 0.35:
            # Round the corner: sweep the offset from one edge's normal to the next.
            steps = max(2, int(abs(turn) / 0.2))
            start = math.atan2(n1[1], n1[0])
            for k in range(steps + 1):
                angle = start + turn * k / steps
                result.append(Point(here.x + padding * math.cos(angle), here.y + padding * math.sin(angle)))
        else:
            mx, my = n1[0] + n2[0], n1[1] + n2[1]
            length = math.hypot(mx, my) or 1.0
            mx, my = mx / length, my / length
            reach = padding / max(mx * n1[0] + my * n1[1], 0.25)
            result.append(Point(here.x + mx * reach, here.y + my * reach))
    return result


def rect_path(x: float, y: float, width: float, height: float):
    """A rectangle as a Path, so render_progress can draw it on."""
    from drawcv import Rectangle
    path = Rectangle(position=Point(x, y), width=width, height=height).to_path()
    path.fill = None
    return path
