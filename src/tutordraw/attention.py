"""Step-local artwork changes, focus and emphasis, applied only to a working copy."""

from contextlib import contextmanager
import math

from drawcv import Color, Drawable, Group, Point, Rectangle, Scene, StrokeStyle

from .adapters.drawcv import crisp_rect, current_fill, outline_path, rect_path, set_fill, translate
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


def offset_at(start, end, progress: float) -> tuple[float, float]:
    """Where a target's move has got to at `progress` from the previous step's restyle to this one's.

    A straight line between the two offsets, or with `end.via` a polyline
    through them, walked at an even speed along its length. Progress outside
    0..1 (an easing that overshoots) runs on along the first or last leg.
    """
    from_move = (0.0, 0.0) if start is None or start.move is None else start.move
    to_move = (0.0, 0.0) if end is None or end.move is None else end.move
    via = end.via if end is not None and end.via else ()
    points = [from_move, *via, to_move]
    legs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])]
    total = sum(legs)
    if len(points) == 2 or total == 0:
        return (_lerp(from_move[0], to_move[0], progress), _lerp(from_move[1], to_move[1], progress))
    distance = progress * total
    moving = [index for index, length in enumerate(legs) if length > 0]
    if distance <= 0:
        index = moving[0]
        t = distance / legs[index]
    elif distance >= total:
        index = moving[-1]
        t = 1 + (distance - total) / legs[index]
    else:
        walked = 0.0
        for index, length in enumerate(legs):
            if length > 0 and distance <= walked + length:
                t = (distance - walked) / length
                break
            walked += length
    a, b = points[index], points[index + 1]
    return (_lerp(a[0], b[0], t), _lerp(a[1], b[1], t))


def _scale(restyle) -> float:
    return 1.0 if restyle is None or restyle.scale is None else restyle.scale


def pivot_point(box, pivot: str) -> tuple[float, float]:
    """The point of `box` a pivot name picks: "top_left", "center", "bottom", ..."""
    vertical, horizontal = {"top": ("top", "center"), "bottom": ("bottom", "center"),
                            "left": ("center", "left"), "right": ("center", "right"),
                            "center": ("center", "center")}.get(pivot) or pivot.split("_")
    x = {"left": box.x, "center": box.x + box.width / 2, "right": box.x + box.width}[horizontal]
    y = {"top": box.y, "center": box.y + box.height / 2, "bottom": box.y + box.height}[vertical]
    return x, y


def restyle_anchors(objects: dict[str, Drawable], *steps) -> dict[str, "BoundingBox"]:
    """Each scaled target's bounds in its parent's space, as the source draws it.

    A pivot names a point of these, so call this before any restyle is
    applied: the point a target scales about never depends on the frame.
    """
    anchors = {}
    for step in steps:
        for restyle in (step.restyles if step is not None else ()):
            key = restyle.target.drawable_id
            if restyle.scale is not None and key not in anchors and key in objects:
                anchors[key] = objects[key].get_bounds_in_parent()
    return anchors


def _centre(restyle, anchors) -> tuple[float, float]:
    """(1 - scale) times the pivot: the shift that keeps the pivot in place as the target scales."""
    s = _scale(restyle)
    if s == 1.0:
        return 0.0, 0.0
    x, y = pivot_point(anchors[restyle.target.drawable_id], restyle.pivot)
    return (1 - s) * x, (1 - s) * y


def pose_at(start, end, progress: float, anchors=None) -> tuple[float, float, float]:
    """(scale, dx, dy): where a target's pose has got to at `progress`, in its parent's space.

    A point the source draws at u is drawn at scale * u + (dx, dy). Scale,
    the pivot's shift and the move each go in a straight line (the move along
    `via` when it has one), so every point of the artwork does too, and a
    player blending the two end frames linearly shows exactly this.
    """
    anchors = anchors or {}
    s = _lerp(_scale(start), _scale(end), progress)
    c0, c1 = _centre(start, anchors), _centre(end, anchors)
    dx, dy = offset_at(start, end, progress)
    return s, _lerp(c0[0], c1[0], progress) + dx, _lerp(c0[1], c1[1], progress) + dy


def apply_pose(obj: Drawable, ratio: float, dx: float, dy: float) -> None:
    """Map a drawable's artwork by x -> ratio * x + (dx, dy) in its parent's space."""
    if ratio == 1.0:
        if dx or dy:
            translate(obj, dx, dy)
        return
    transform = obj.transform
    if transform.pivot is None:  # fix DrawCV's dynamic pivot where it is now, so nothing jumps
        transform.pivot = obj.get_geometry_bounds().center
    pivot = transform.pivot
    tx, ty = transform.translation_x, transform.translation_y
    transform.translation_x = tx + (ratio - 1) * (tx + pivot.x) + dx
    transform.translation_y = ty + (ratio - 1) * (ty + pivot.y) + dy
    transform.scale_x *= ratio
    transform.scale_y *= ratio


def _blend(obj: Drawable, start, end, progress: float, anchors=None) -> None:
    """Move one drawable from the previous step's state toward this step's.

    An unspecified property on either side means "whatever the source says",
    so a target restyled in one step slides back when the next leaves it alone.
    """
    apply_pose(obj, *pose_at(start, end, progress, anchors))

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
                   progress: float = 1.0, anchors=None) -> None:
    """Apply artwork changes first, so labels, highlights and dimming see them.

    `previous` and `progress` are supplied only while animating; at progress 1
    the result is exactly the step's own restyled state. `anchors` are the
    `restyle_anchors` of both steps; by default they are taken from the
    objects as they are, which must then be as the source draws them.
    """
    if anchors is None:
        anchors = restyle_anchors(objects, step, previous)
    current = {r.target.drawable_id: r for r in step.restyles}
    earlier = {r.target.drawable_id: r
               for r in (previous.restyles if previous is not None else ())}
    for drawable_id in {**earlier, **current}:
        _blend(objects[drawable_id], earlier.get(drawable_id),
               current.get(drawable_id), progress, anchors)


def residual_moves(step: Step, previous: Step | None, progress: float,
                   target: float = 1.0, anchors=None) -> dict[str, tuple[float, float, float]]:
    """(dx, dy, ratio) taking each restyled target from `progress` to `target`.

    Applied to the current frame (`posed`), it puts a target where the step
    ends, which is the geometry label placement is decided against;
    `target=0` reaches the other end of an animated step instead. At
    progress 1 the default is empty, so a static render pays nothing for it.
    `anchors` as for `apply_restyles`; only a restyle that scales needs them.
    """
    current = {r.target.drawable_id: r for r in step.restyles}
    earlier = {r.target.drawable_id: r
               for r in (previous.restyles if previous is not None else ())}
    result: dict[str, tuple[float, float, float]] = {}
    for drawable_id in {**earlier, **current}:
        start, end = earlier.get(drawable_id), current.get(drawable_id)
        s_there, x_there, y_there = pose_at(start, end, target, anchors)
        s_here, x_here, y_here = pose_at(start, end, progress, anchors)
        ratio = s_there / s_here
        dx, dy = x_there - ratio * x_here, y_there - ratio * y_here
        if dx or dy or ratio != 1.0:
            result[drawable_id] = (dx, dy, ratio)
    return result


@contextmanager
def posed(objects: dict[str, Drawable], moves: dict[str, tuple[float, ...]]):
    """The objects with `residual_moves` applied while the block runs, then put back exactly.

    The moves go through the real transform pipeline, so a target inside a
    rotated or scaled group, and everything inside a scaled target, measure
    correctly; the saved transforms are restored by assignment rather than
    by undoing the arithmetic.
    """
    saved = {}
    for key in moves:
        if key in objects:
            t = objects[key].transform
            saved[key] = (t.translation_x, t.translation_y, t.scale_x, t.scale_y, t.pivot)
    try:
        for key, move in moves.items():
            if key in objects:
                apply_pose(objects[key], move[2] if len(move) > 2 else 1.0, move[0], move[1])
        yield objects
    finally:
        for key, (x, y, sx, sy, pivot) in saved.items():
            t = objects[key].transform
            t.translation_x, t.translation_y, t.scale_x, t.scale_y, t.pivot = x, y, sx, sy, pivot


def final_bounds(objects: dict[str, Drawable], ids, moves: dict[str, tuple[float, ...]]
                 ) -> dict[str, "BoundingBox"]:
    """Bounds these drawables will have at the end of the step (see `posed`)."""
    if not moves:
        return {key: objects[key].get_bounds() for key in ids if key in objects}
    with posed(objects, moves):
        return {key: objects[key].get_bounds() for key in ids if key in objects}


def apply_attention(scene: Scene, step: Step) -> None:
    requested = [h.target for h in step.highlights] + list(step._focus)
    visible = visible_ids(scene)
    for target in requested:
        if target.drawable_id not in visible:
            raise ValidationError(f"Cannot emphasize hidden target {target.name or target.id!r}")
    if step._dim_opacity is not None:
        apply_dimming(scene, {t.drawable_id for t in step._focus}, step._dim_opacity)


def highlight_artwork(highlight: Highlight, obj: Drawable, progress: float = 1.0) -> Drawable:
    """A box around the target's bounds, or its own outline grown by padding.

    Below full progress the stroke is a Path drawn that far along; at full
    progress a box stays a plain Rectangle, exactly as before draw-on existed.
    """
    stroke = StrokeStyle(color=Color(*highlight.color), width=highlight.width)
    pad = highlight.padding
    if highlight.shape == "outline":
        shape = outline_path(obj, pad)
        shape.stroke = stroke
    else:
        bounds = obj.get_bounds()
        x, y, w, h = crisp_rect(bounds.x - pad, bounds.y - pad,
                                bounds.width + 2 * pad, bounds.height + 2 * pad, highlight.width)
        if progress >= 1:
            return Rectangle(position=Point(x, y), width=w, height=h, stroke=stroke, z_index=-1,
                             id=f"td-hl-{highlight.target.id}")
        shape = rect_path(x, y, w, h)
        shape.stroke = stroke
    shape.z_index = -1
    shape.id = f"td-hl-{highlight.target.id}"
    if progress < 1:
        shape.render_progress = progress
    return shape
