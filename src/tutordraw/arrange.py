"""Place blocks of drawing beside, below or above others, from their measured bounds.

A model writing a caption or an equation by absolute pixels has to guess how
big it will be, and stacks things on each other or on a diagram's tick
numbers. TutorDraw knows every size exactly, so a caller measures a block
and asks for it by relation instead: `place` puts it on one side of another
block's real bounds with a gap, and `clear` moves one that already covers
something to the nearest free spot. Both work on plain bounding boxes, so
they suit any drawable; `shift_to` moves a drawable onto the box chosen.
"""

from __future__ import annotations

from drawcv import BoundingBox, Drawable, Point

from .adapters.drawcv import translate
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
    be. Deterministic: the same boxes always give the same answer.
    """
    area = _canvas(canvas)
    margin = finite_number(margin, "margin", minimum=0)
    obstacles = [o for o in obstacles if o.width > 0 and o.height > 0]
    width, height = box.width, box.height

    def inside(x, y):
        return margin <= x + 1e-9 and x + width <= area[0] - margin + 1e-9 \
            and margin <= y + 1e-9 and y + height <= area[1] - margin + 1e-9

    if inside(box.x, box.y) and not _hits(box, obstacles, margin):
        return box
    xs = {box.x, margin, area[0] - margin - width}
    ys = {box.y, margin, area[1] - margin - height}
    for o in obstacles:
        xs |= {o.right + margin, o.left - margin - width}
        ys |= {o.bottom + margin, o.top - margin - height}
    best = None
    for x in xs:
        for y in ys:
            if not inside(x, y):
                continue
            candidate = BoundingBox(x, y, width, height)
            if _hits(candidate, obstacles, margin - 1e-6):
                continue
            dx, dy = x - box.x, y - box.y
            # Shortest first; then prefer down over up and right over left.
            score = (round(dx * dx + dy * dy, 6), dy < 0, dx < 0, y, x)
            if best is None or score < best[0]:
                best = (score, candidate)
    return None if best is None else best[1]


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
