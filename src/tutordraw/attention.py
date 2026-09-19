"""Step-local focus and emphasis, applied only to a working scene."""

from drawcv import Color, Drawable, Group, Point, Rectangle, Scene, StrokeStyle

from .errors import ValidationError
from .model import Highlight, Step


def visible_ids(scene: Scene) -> set[str]:
    """Structural visibility: layer/ancestor flags and nonzero opacity."""
    result: set[str] = set()

    def visit(obj: Drawable, parent_visible: bool) -> bool:
        visible = parent_visible and obj.visible and obj.opacity > 0
        if isinstance(obj, Group):
            child_states = [visit(child, visible) for child in obj.children]
            visible = visible and any(child_states)
        if visible:
            result.add(obj.id)
        return visible

    for layer in scene.layers:
        for obj in layer.objects:
            visit(obj, layer.visible and layer.opacity > 0)
    return result


def apply_dimming(scene: Scene, focused_ids: set[str], factor: float) -> None:
    """Dim maximal unrelated branches once, preserving focused subtrees."""
    relevant: set[str] = set()

    def mark(obj: Drawable) -> bool:
        child_states = [mark(child) for child in obj.children] if isinstance(obj, Group) else []
        contains_focus = obj.id in focused_ids or any(child_states)
        if contains_focus:
            relevant.add(obj.id)
        return contains_focus

    def dim(obj: Drawable) -> None:
        if obj.id in focused_ids:
            return  # The whole subtree is focused.
        if obj.id not in relevant:
            obj.opacity *= factor
        elif isinstance(obj, Group):
            for child in obj.children:
                dim(child)

    for obj in scene.objects:
        mark(obj)
    for obj in scene.objects:
        dim(obj)


def apply_attention(scene: Scene, step: Step) -> None:
    requested = [h.target for h in step.highlights] + list(step._focus)
    visible = visible_ids(scene)
    for target in requested:
        if target.drawable_id not in visible:
            raise ValidationError(f"Cannot emphasize hidden target {target.name or target.id!r}")
    if step._dim_opacity is not None:
        apply_dimming(scene, {t.drawable_id for t in step._focus}, step._dim_opacity)


def highlight_artwork(highlight: Highlight, obj: Drawable) -> Rectangle:
    bounds = obj.get_bounds()
    pad = highlight.padding
    return Rectangle(position=Point(bounds.x - pad, bounds.y - pad),
                     width=bounds.width + 2 * pad, height=bounds.height + 2 * pad,
                     stroke=StrokeStyle(color=Color(*highlight.color), width=highlight.width),
                     z_index=-1)
