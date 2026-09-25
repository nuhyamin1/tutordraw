"""Place blocks of drawing beside, below or above others, from their measured bounds.

A model writing a caption or an equation by absolute pixels has to guess how
big it will be, and stacks things on each other or on a diagram's tick
numbers. TutorDraw knows every size exactly, so a caller measures a block
and asks for it by relation instead: `place` puts it on one side of another
block's real bounds with a gap, and `clear` moves one that already covers
something to the nearest free spot. Both work on plain bounding boxes, so
they suit any drawable; `shift_to` moves a drawable onto the box chosen.

`words`, `diagrams` and `collisions` read a composed frame for the drawing's
own text and equations lying on each other or on a kit, which lint reports
(TEXT_OVERLAP, TEXT_ON_DIAGRAM); `occupied` gives the boxes to `clear` one of
them off.
"""

from __future__ import annotations

from drawcv import BoundingBox, Drawable, Group, Point, Text

from .adapters.drawcv import stroke_boxes, translate
from .errors import ValidationError
from .validation import finite_number

SIDES = ("right", "left", "below", "above", "beside")
GAP = 16.0  # px between a block and what it is placed by
MARGIN = 8.0  # px kept from the canvas edge, and between a moved block and what it clears


def _size(size) -> tuple[float, float]:
    if not isinstance(size, (tuple, list)) or len(size) != 2:
        raise ValidationError("size must be (width, height)")
    width, height = (finite_number(v, "size") for v in size)
    if width <= 0 or height <= 0:
        raise ValidationError("size must be positive")
    return width, height


def _canvas(canvas) -> tuple[float, float] | None:
    if canvas is None:
        return None
    if not isinstance(canvas, (tuple, list)) or len(canvas) != 2:
        raise ValidationError("canvas must be (width, height)")
    return tuple(finite_number(v, "canvas", minimum=0) for v in canvas)


def place(size, reference: BoundingBox, side: str, *, gap: float = GAP, canvas=None,
          margin: float = MARGIN) -> BoundingBox:
    """Where a block of `size` goes on `side` of `reference`, `gap` px away.

    "right" and "left" line its top up with the reference's top; "below" and
    "above" line up their left edges, so blocks placed one below another form
    a column. "beside" is "right" when that fits the canvas, else "left" when
    that does, else whichever side has more room. With `canvas`, the block is
    slid along the side (never across it) to stay `margin` inside the canvas.
    A block that cannot fit on its side keeps its side and runs off the
    canvas, for the caller to report, rather than landing on the reference.
    """
    if side not in SIDES:
        raise ValidationError(f"side must be one of {', '.join(SIDES)}, not {side!r}")
    width, height = _size(size)
    gap = finite_number(gap, "gap", minimum=0)
    margin = finite_number(margin, "margin", minimum=0)
    area = _canvas(canvas)
    if side == "beside":
        side = "right"
        if area is not None and reference.right + gap + width > area[0] - margin:
            room_right = area[0] - margin - reference.right - gap
            room_left = reference.left - gap - margin
            if room_left >= width or room_left > room_right:
                side = "left"
    if side == "right":
        x, y = reference.right + gap, reference.top
    elif side == "left":
        x, y = reference.left - gap - width, reference.top
    elif side == "below":
        x, y = reference.left, reference.bottom + gap
    else:
        x, y = reference.left, reference.top - gap - height
    if area is not None:
        if side in ("right", "left"):
            y = _slide(y, height, area[1], margin)
        else:
            x = _slide(x, width, area[0], margin)
    return BoundingBox(x, y, width, height)


def _slide(start: float, extent: float, limit: float, margin: float) -> float:
    """Shift a span back inside [margin, limit - margin]; one too long starts at the margin."""
    if extent > limit - 2 * margin:
        return margin
    return min(max(start, margin), limit - margin - extent)


def _hits(box: BoundingBox, obstacles, margin: float) -> bool:
    return any(box.left < o.right + margin and o.left - margin < box.right
               and box.top < o.bottom + margin and o.top - margin < box.bottom for o in obstacles)


def clear(box: BoundingBox, obstacles, *, canvas, margin: float = MARGIN) -> BoundingBox | None:
    """The nearest box of the same size that keeps `margin` from every obstacle, or None.

    Returns `box` itself when it already does. Candidates are the positions
    that put an edge `margin` px from an obstacle's edge or the canvas's,
    combined in x and y; the free one needing the shortest move wins, ties
    going to a move down, then right, so reading order is kept where it can
    be. Deterministic: the same boxes always give the same answer. Tested
    all at once with numpy, so hundreds of obstacles (a graph's ink) are fine.
    """
    import numpy as np

    area = _canvas(canvas)
    margin = finite_number(margin, "margin", minimum=0)
    obstacles = [o for o in obstacles if o.width > 0 and o.height > 0]
    width, height = box.width, box.height
    if not _outside(box.x, box.y, width, height, area, margin) and not _hits(box, obstacles, margin):
        return box
    lefts = np.array([o.left for o in obstacles]) - margin
    rights = np.array([o.right for o in obstacles]) + margin
    tops = np.array([o.top for o in obstacles]) - margin
    bottoms = np.array([o.bottom for o in obstacles]) + margin
    xs = np.unique(np.concatenate(([box.x, margin, area[0] - margin - width], rights, lefts - width)))
    ys = np.unique(np.concatenate(([box.y, margin, area[1] - margin - height], bottoms, tops - height)))
    xs = xs[(xs >= margin - 1e-9) & (xs + width <= area[0] - margin + 1e-9)]
    ys = ys[(ys >= margin - 1e-9) & (ys + height <= area[1] - margin + 1e-9)]
    if not len(xs) or not len(ys):
        return None
    x, y = (grid.ravel() for grid in np.meshgrid(xs, ys))
    dx, dy = x - box.x, y - box.y
    # Shortest first; then prefer down over up and right over left, then the position itself.
    order = np.lexsort((x, y, dx < 0, dy < 0, np.round(dx * dx + dy * dy, 6)))
    step, eps = 4096, 1e-6
    for start in range(0, len(order), step):
        chosen = order[start:start + step]
        cx, cy = x[chosen][:, None], y[chosen][:, None]
        hit = ((cx < rights - eps) & (lefts + eps < cx + width)
               & (cy < bottoms - eps) & (tops + eps < cy + height)).any(axis=1)
        free = np.flatnonzero(~hit)
        if len(free):
            k = chosen[free[0]]
            return BoundingBox(float(x[k]), float(y[k]), width, height)
    return None


def _outside(x, y, width, height, area, margin) -> bool:
    return not (margin <= x + 1e-9 and x + width <= area[0] - margin + 1e-9
                and margin <= y + 1e-9 and y + height <= area[1] - margin + 1e-9)


def shift_to(drawable: Drawable, x: float, y: float) -> None:
    """Move a drawable so the top left of its measured bounds is at (x, y).

    Text moves by its position; anything else by its transform's translation,
    so a group (an equation, a kit) moves with all its parts.
    """
    x, y = finite_number(x, "x"), finite_number(y, "y")
    box = drawable.get_bounds()
    dx, dy = x - box.x, y - box.y
    position = getattr(drawable, "position", None)
    if isinstance(position, Point):
        drawable.position = Point(position.x + dx, position.y + dy)
    else:
        translate(drawable, dx, dy)


# --- the drawing's own words -------------------------------------------------

OVERLAY = "__tutordraw__"  # the layer annotations are drawn into (adapters.drawcv.overlay_layer)
TOUCH = 1.0  # px: boxes that meet by less than this in either direction do not overlap


def _kit(obj) -> str | None:
    """The kind of kit a group is ("axes", "equation", ...), or None."""
    from .kits._base import KIT_KEY

    data = getattr(obj, "metadata", None)
    data = data.get(KIT_KEY) if isinstance(data, dict) else None
    return data.get("kit") if isinstance(data, dict) else None


def _shown(obj) -> bool:
    return obj.effective_visible and obj.effective_opacity > 0.01


def _artwork(scene):
    """Top-level drawables of every layer but TutorDraw's own annotation layer."""
    for layer in scene.layers:
        if not layer.name.startswith(OVERLAY):
            yield from layer.objects


def _overlap(a: BoundingBox, b: BoundingBox) -> bool:
    return (min(a.right, b.right) - max(a.left, b.left) > TOUCH
            and min(a.bottom, b.bottom) - max(a.top, b.top) > TOUCH)


def words(scene) -> list[tuple[Drawable, BoundingBox]]:
    """The drawing's free words on screen: text and equations that are not part of another kit.

    Each is (drawable, its bounds). Text inside a kit (tick numbers, a node's
    text, a caption added to a graph) is laid out by that kit and belongs to
    it; an equation is its group. Annotations are not the drawing's words.
    """
    found = []

    def visit(obj, inside: bool) -> None:
        if not _shown(obj):
            return
        kind = _kit(obj) if isinstance(obj, Group) else None
        if kind == "equation" and not inside:
            found.append((obj, obj.get_bounds()))
        elif isinstance(obj, Group):
            for child in obj.children:
                visit(child, inside or kind is not None)
        elif isinstance(obj, Text) and not inside and obj.text.strip():
            found.append((obj, obj.get_bounds()))

    for obj in _artwork(scene):
        visit(obj, False)
    return found


def diagrams(scene) -> list[tuple[Group, BoundingBox]]:
    """Every kit on screen other than an equation, outermost only, with its bounds."""
    found = []

    def visit(obj) -> None:
        if not _shown(obj) or not isinstance(obj, Group):
            return
        kind = _kit(obj)
        if kind is not None and kind != "equation":
            found.append((obj, obj.get_bounds()))
        elif kind is None:
            for child in obj.children:
                visit(child)

    for obj in _artwork(scene):
        visit(obj)
    return found


def _ink(group, near: BoundingBox) -> list[BoundingBox]:
    """Boxes along what a kit actually draws near a box (anywhere, for None): text, fills, strokes chunked."""
    boxes = []

    def visit(obj) -> None:
        if not _shown(obj):
            return
        box = obj.get_bounds()
        if near is not None and not _overlap(box, near):
            return
        if isinstance(obj, Group) and _kit(obj) != "equation":
            for child in obj.children:
                visit(child)
        elif isinstance(obj, (Text, Group)):
            boxes.append(box)
        else:
            boxes.extend(stroke_boxes(obj) or [box])

    for child in group.children:
        visit(child)
    return boxes


def occupied(scene, *, exclude=()) -> list[BoundingBox]:
    """Boxes over everything a word must keep off: the other words, and each kit's ink.

    For `clear`: a word moved to a free spot among these lands on no other
    text or equation and on no line, text or shading of a diagram. `exclude`
    holds drawables (a word being moved) to leave out.
    """
    skip = {drawable.id for drawable in exclude}
    boxes = [box for word, box in words(scene) if word.id not in skip]
    for group, bounds in diagrams(scene):
        boxes.extend(_ink(group, None))
    return boxes


def collisions(scene) -> list[tuple[Drawable, Drawable]]:
    """(word, what it lies on) for every free word on another, or on a kit's ink.

    Pairs of words come once, in drawing order. Against a kit the second item
    is the kit's group, reported once per word however much of it is covered.
    """
    free = words(scene)
    kits = diagrams(scene)
    found = []
    for index, (word, box) in enumerate(free):
        found.extend((word, other) for other, second in free[index + 1:] if _overlap(box, second))
        found.extend((word, group) for group, bounds in kits
                     if _overlap(box, bounds) and any(_overlap(box, piece) for piece in _ink(group, box)))
    return found
