"""Step-local artwork changes, focus and emphasis, applied only to a working copy."""

from drawcv import Color, Drawable, Group, Point, Rectangle, Scene, StrokeStyle

from .adapters.drawcv import current_fill, set_fill, translate
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


def _lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def _blend(obj: Drawable, start, end, progress: float) -> None:
    """Move one drawable from the previous step's state toward this step's.

    An unspecified property on either side means "whatever the source says",
    so a target restyled in one step slides back when the next leaves it alone.
    """
    from_move = (0.0, 0.0) if start is None or start.move is None else start.move
    to_move = (0.0, 0.0) if end is None or end.move is None else end.move
    dx = _lerp(from_move[0], to_move[0], progress)
    dy = _lerp(from_move[1], to_move[1], progress)
    if dx or dy:
        translate(obj, dx, dy)

    if (start is not None and start.opacity is not None) or             (end is not None and end.opacity is not None):
        base = obj.opacity
        obj.opacity = _lerp(
            start.opacity if start is not None and start.opacity is not None else base,
            end.opacity if end is not None and end.opacity is not None else base,
            progress)

    if (start is not None and start.fill is not None) or             (end is not None and end.fill is not None):
        base = current_fill(obj)
        from_fill = start.fill if start is not None and start.fill is not None else base
        to_fill = end.fill if end is not None and end.fill is not None else base
        from_fill = from_fill if from_fill is not None else to_fill
        to_fill = to_fill if to_fill is not None else from_fill
        # Interpolating in plain RGB, which is simple and predictable rather
        # than perceptually even. Document it rather than pretend otherwise.
        set_fill(obj, tuple(int(round(_lerp(a, b, progress)))
                            for a, b in zip(from_fill, to_fill)))

    # Visibility cannot be interpolated, so this step's own value applies
    # throughout it. Pair visible with opacity to fade something in.
    if end is not None and end.visible is not None:
        obj.visible = end.visible


def apply_restyles(objects: dict[str, Drawable], step: Step, previous: Step | None = None,
                   progress: float = 1.0) -> None:
    """Apply artwork changes first, so labels, highlights and dimming see them.

    `previous` and `progress` are supplied only while animating; at progress 1
    the result is exactly the step's own restyled state.
    """
    current = {r.target.drawable_id: r for r in step.restyles}
    earlier = {r.target.drawable_id: r
               for r in (previous.restyles if previous is not None else ())}
    for drawable_id in {**earlier, **current}:
        _blend(objects[drawable_id], earlier.get(drawable_id),
               current.get(drawable_id), progress)


def residual_moves(step: Step, previous: Step | None, progress: float,
                   target: float = 1.0) -> dict[str, tuple[float, float]]:
    """The translation taking each restyled target from `progress` to `target`.

    Adding it to the current frame puts a target where the step ends, which is
    the geometry label placement is decided against; `target=0` reaches the
    other end of an animated step instead. At progress 1 the default is empty,
    so a static render pays nothing for it.
    """
    current = {r.target.drawable_id: r for r in step.restyles}
    earlier = {r.target.drawable_id: r
               for r in (previous.restyles if previous is not None else ())}
    result: dict[str, tuple[float, float]] = {}
    for drawable_id in {**earlier, **current}:
        start, end = earlier.get(drawable_id), current.get(drawable_id)
        from_move = (0.0, 0.0) if start is None or start.move is None else start.move
        to_move = (0.0, 0.0) if end is None or end.move is None else end.move
        dx = _lerp(from_move[0], to_move[0], target) - _lerp(from_move[0], to_move[0], progress)
        dy = _lerp(from_move[1], to_move[1], target) - _lerp(from_move[1], to_move[1], progress)
        if dx or dy:
            result[drawable_id] = (dx, dy)
    return result


def final_bounds(objects: dict[str, Drawable], ids, moves: dict[str, tuple[float, float]]
                 ) -> dict[str, "BoundingBox"]:
    """Bounds these drawables will have at the end of the step.

    The moves are applied through the real transform pipeline, so a target
    inside a rotated or scaled group measures correctly, then the saved
    translations are restored by assignment rather than by subtracting back.
    Only translation is touched; nothing else here changes a bounding box.
    """
    if not moves:
        return {key: objects[key].get_bounds() for key in ids if key in objects}
    saved = {key: (objects[key].transform.translation_x, objects[key].transform.translation_y)
             for key in moves if key in objects}
    try:
        for key, (dx, dy) in moves.items():
            if key in objects:
                translate(objects[key], dx, dy)
        return {key: objects[key].get_bounds() for key in ids if key in objects}
    finally:
        for key, (x, y) in saved.items():
            objects[key].transform.translation_x = x
            objects[key].transform.translation_y = y


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
