"""Per-step framing: zoom the artwork, never the annotations.

A camera state is (scale, tx, ty) mapping scene to screen as s * p + t. It is
applied by wrapping each layer's top-level artwork in one Group inside the
working copy, so dimming, nested groups and hit testing keep working and the
source scene is never touched. Annotations are added afterwards on the overlay
layer, in screen space, so text stays the same size at any zoom.
"""

from contextlib import contextmanager
import math

from drawcv import BoundingBox, Group, Point, Scene, Transform

State = tuple[float, float, float]
IDENTITY: State = (1.0, 0.0, 0.0)


def fit(camera, bounds: dict[str, BoundingBox], width: float, height: float) -> State | None:
    """The state framing the camera's targets, or None for the whole canvas."""
    if camera is None:
        return None
    boxes = [bounds[t.drawable_id] for t in camera.targets if t.drawable_id in bounds]
    if not boxes:
        return None
    left = min(b.left for b in boxes) - camera.padding
    top = min(b.top for b in boxes) - camera.padding
    right = max(b.right for b in boxes) + camera.padding
    bottom = max(b.bottom for b in boxes) + camera.padding
    span_x, span_y = max(right - left, 1e-6), max(bottom - top, 1e-6)
    scale = min(width / span_x, height / span_y, camera.max_scale)
    cx, cy = (left + right) / 2, (top + bottom) / 2
    return scale, width / 2 - scale * cx, height / 2 - scale * cy


def blend(start: State | None, end: State | None, t: float, width: float, height: float) -> State:
    """Move the screen centre linearly and the scale geometrically.

    Interpolating (s, tx, ty) directly makes the view swing sideways during a
    zoom; blending what sits at the screen centre does not.
    """
    a, b = start or IDENTITY, end or IDENTITY
    if t <= 0:
        return a
    if t >= 1:
        return b

    def centre(state):
        s, tx, ty = state
        return (width / 2 - tx) / s, (height / 2 - ty) / s

    (ax, ay), (bx, by) = centre(a), centre(b)
    scale = math.exp(math.log(a[0]) + (math.log(b[0]) - math.log(a[0])) * t)
    cx, cy = ax + (bx - ax) * t, ay + (by - ay) * t
    return scale, width / 2 - scale * cx, height / 2 - scale * cy


def install(scene: Scene) -> list[Group]:
    """Wrap each layer's top-level artwork in a camera group; return them."""
    groups = []
    for layer in scene.layers:
        objects = list(layer.objects)
        if not objects:
            continue
        for obj in objects:
            layer.remove(obj)
        group = Group(children=objects, transform=Transform(pivot=Point(0, 0)),
                      id=f"td-camera-{len(groups)}")
        layer.add(group)
        groups.append(group)
    return groups


def apply(groups: list[Group], state: State) -> None:
    s, tx, ty = state
    for group in groups:
        group.transform = Transform(translation_x=tx, translation_y=ty,
                                    scale_x=s, scale_y=s, pivot=Point(0, 0))


def to_screen(state: State | None, x: float, y: float) -> Point:
    s, tx, ty = state or IDENTITY
    return Point(s * x + tx, s * y + ty)


@contextmanager
def held_at(groups: list[Group], state: State | None):
    """Temporarily put the camera somewhere else, e.g. at the step's end."""
    if not groups or state is None:
        yield
        return
    saved = [group.transform for group in groups]
    apply(groups, state)
    try:
        yield
    finally:
        for group, transform in zip(groups, saved):
            group.transform = transform
