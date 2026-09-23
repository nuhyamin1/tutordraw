"""DrawCV operations isolated from the teaching model."""

from contextlib import contextmanager
from copy import deepcopy
import math
from pathlib import Path

from drawcv import Color, Drawable, FillStyle, Group, Scene

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
