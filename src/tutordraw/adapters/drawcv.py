"""DrawCV operations isolated from the teaching model."""

from copy import deepcopy

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
