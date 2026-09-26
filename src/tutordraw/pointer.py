"""The presenter's pointer: one hand that glides to whatever the narrator means.

A step points at targets with `Step.point(target, at=)` (or a narration cue).
The lesson has one pointer: it fades in at its first stop, glides from stop to
stop, taps as it arrives, and carries over into the next step from where the
last one left it. A step that points at nothing shows none.

Each step's movement is a list of keyframes (`track`), worked out once from the
step's finished picture, so the Python renderer and the browser player (which
is sent the same keys) place the pointer identically. See docs/POINTER.md.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

STYLES = ("hand", "cursor", "dot")
# Seconds the pointer takes to appear at its first stop, and to tap on arrival.
APPEAR = 0.3
TAP = 0.3
TAP_SCALE = 0.86  # how far the tap presses in, as a scale
GAP = 3.0  # px between the fingertip and the target's outline

# Glyphs in local coordinates: the tip at (0, 0), the body along +y, about 46 px long.
HAND = [(-4.5, 3.0), (-3.6, 0.8), (-1.6, -0.3), (1.6, -0.3), (3.6, 0.8), (4.5, 3.0),
        (4.5, 16.5), (6.0, 15.2), (8.6, 15.0), (10.4, 16.4), (10.6, 19.0),
        (12.2, 17.9), (14.8, 18.0), (16.4, 19.6), (16.4, 22.6),
        (17.6, 22.2), (19.8, 23.0), (21.0, 25.2), (21.0, 33.5),
        (20.0, 40.0), (16.0, 46.0), (-5.5, 46.0), (-10.5, 40.5),
        (-16.8, 31.8), (-17.6, 27.8), (-15.6, 25.6), (-12.2, 26.4), (-4.5, 31.0)]
CURSOR = [(0.0, 0.0), (0.0, 30.0), (7.0, 23.5), (12.5, 35.0), (17.0, 33.0), (11.5, 21.5), (21.0, 21.5)]
DOT_RADIUS = 9.0

# Directions the pointer may reach in from, best first: it hangs down and to
# the right of what it points at, like a cursor, unless something is there.
DIRECTIONS = [(1, 1), (0, 1), (1, 0), (-1, 1), (1, -1), (-1, 0), (0, -1), (-1, -1)]


@dataclass(frozen=True)
class Pose:
    """Where the pointer is: its tip (x, y), the angle its body points away at, size and opacity."""

    x: float
    y: float
    angle: float  # degrees; 0 is the body straight down from the tip
    scale: float = 1.0
    opacity: float = 1.0


@dataclass(frozen=True)
class Stop:
    """One point in a step: the target, and seconds into the step."""

    target: object
    at: float


def glyph(style: str) -> list[tuple[float, float]]:
    return HAND if style == "hand" else CURSOR


def placed(style: str, pose: Pose) -> list[tuple[float, float]]:
    """The glyph's outline on the canvas at a pose."""
    angle = math.radians(pose.angle)
    c, s = math.cos(angle), math.sin(angle)
    return [(pose.x + pose.scale * (c * x - s * y), pose.y + pose.scale * (s * x + c * y))
            for x, y in glyph(style)]


def angle_for(direction: tuple[float, float]) -> float:
    """The rotation that lays the glyph's body (local +y) along `direction`."""
    dx, dy = direction
    return math.degrees(math.atan2(-dx, dy))


def ease(t: float) -> float:
    """Smoothstep: the curve the player uses too (player.js `smooth`)."""
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def pose_at(keys: list[tuple], time: float) -> Pose | None:
    """Interpolate a track's keys [(t, x, y, angle, scale, opacity), ...] at `time` seconds.

    Position and angle ease (smoothstep) between keys, the shortest way round
    for the angle; scale and opacity are linear. Before the first key or with
    no keys there is no pointer.
    """
    if not keys or time < keys[0][0]:
        return None
    if time >= keys[-1][0]:
        return Pose(*keys[-1][1:])
    for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
        if t0 <= time < t1:
            u = (time - t0) / (t1 - t0) if t1 > t0 else 1.0
            e = ease(u)
            turn = (b[2] - a[2] + 180) % 360 - 180
            return Pose(a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, a[2] + turn * e,
                        a[3] + (b[3] - a[3]) * u, a[4] + (b[4] - a[4]) * u)
    return Pose(*keys[-1][1:])


def artwork(style: str, pose: Pose) -> list:
    """The pointer as DrawCV drawables at a pose: a white glyph with a dark outline and soft shadow."""
    from drawcv import Circle, Color, FillStyle, Path, Point, StrokeStyle

    ink = Color(33, 41, 54)
    if style == "dot":
        halo = Circle(center=Point(pose.x, pose.y), radius=DOT_RADIUS * 1.8 * pose.scale,
                      fill=FillStyle(color=Color(229, 57, 53)), stroke=None,
                      opacity=0.25 * pose.opacity, id="td-pointer-halo")
        dot = Circle(center=Point(pose.x, pose.y), radius=DOT_RADIUS * pose.scale,
                     fill=FillStyle(color=Color(229, 57, 53)),
                     stroke=StrokeStyle(color=Color(255, 255, 255), width=2),
                     opacity=pose.opacity, id="td-pointer")
        return [halo, dot]
    parts = []
    for shift, fill, stroke, opacity, ident in (
            (2.5, Color(0, 0, 0), None, 0.18, "td-pointer-shadow"),
            (0.0, Color(255, 255, 255), StrokeStyle(color=ink, width=2), 1.0, "td-pointer")):
        outline = placed(style, Pose(pose.x + shift, pose.y + shift, pose.angle, pose.scale))
        path = Path()
        path.move_to(Point(*outline[0]))
        for x, y in outline[1:]:
            path.line_to(Point(x, y))
        path.close()
        path.fill = FillStyle(color=fill)
        path.stroke = stroke
        path.opacity = opacity * pose.opacity
        path.id = ident
        parts.append(path)
    return parts


def _box(points):
    from drawcv import BoundingBox

    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return BoundingBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def reach(style: str, drawable, direction: tuple[float, float]) -> Pose:
    """The pose that points at `drawable` with the body reaching in along `direction`.

    The tip goes on the target's own outline (layout.ink_point) where the
    direction leaves its bounds, a few pixels outside it.
    """
    from drawcv import Point

    from .layout import ink_point

    box = drawable.get_bounds()
    length = math.hypot(*direction)
    dx, dy = direction[0] / length, direction[1] / length
    half_w, half_h = box.width / 2, box.height / 2
    t = min(half_w / abs(dx) if dx else math.inf, half_h / abs(dy) if dy else math.inf)
    edge = Point(box.center.x + dx * t, box.center.y + dy * t)
    tip = ink_point(drawable, edge)
    return Pose(tip.x + dx * GAP, tip.y + dy * GAP, 0.0 if style == "dot" else angle_for((dx, dy)))


def plan(tutorial, index: int) -> list[tuple[Stop, Pose]]:
    """Each stop of a step with the pose it rests at, judged on the step's finished picture.

    The body reaches in from the first of DIRECTIONS that keeps it on the
    canvas and covers the least of the step's panels, marks, highlights and
    other targets. What the target lies on (a cell round its nucleus) does
    not count: every side of the target is on it.
    """
    from .adapters.drawcv import index_scene
    from .collision import outside_area, overlap_area

    step = tutorial.steps[index]
    style = tutorial.theme.pointer_style
    composition = tutorial._compose(index, 1.0, pointer=False)
    objects = index_scene(composition.scene)
    width, height = composition.scene.width, composition.scene.height
    busy = [a.panel for a in composition.annotations]
    busy += [m.panel or m.bounds for m in composition.marks]
    result = []
    for stop in step.points:
        drawable = objects[stop.target.drawable_id]
        others = [objects[t.drawable_id].get_bounds() for t in tutorial.targets
                  if t.drawable_id != stop.target.drawable_id and t.drawable_id in objects
                  and objects[t.drawable_id].effective_visible]
        # What the target lies on contains its centre (a cell round its nucleus): not an obstacle.
        centre = drawable.get_bounds().center
        under = [box for box in others
                 if not (box.left <= centre.x <= box.right and box.top <= centre.y <= box.bottom)]
        best = None
        for rank, direction in enumerate(DIRECTIONS):
            pose = reach(style, drawable, direction)
            body = _box(placed(style, pose)) if style != "dot" else _box(
                [(pose.x - DOT_RADIUS, pose.y - DOT_RADIUS), (pose.x + DOT_RADIUS, pose.y + DOT_RADIUS)])
            score = (outside_area(body, width, height),
                     sum(overlap_area(body, box) for box in (*busy, *under)), rank)
            if best is None or score < best[0]:
                best = (score, pose)
            if style == "dot" or not any(score[:2]):
                break
        result.append((stop, best[1]))
    return result


def track(tutorial, index: int) -> list[tuple]:
    """The step's pointer keyframes: [(seconds, x, y, angle, scale, opacity), ...], or [] for none.

    Starts where the previous step's pointer rested, if it had one, and
    glides from there; otherwise it fades in (APPEAR) at the first stop. A
    stop that comes before the last glide and tap are done waits for them.
    """
    step = tutorial.steps[index]
    stops = plan(tutorial, index) if step.points else []
    if not stops:
        return []
    glide = tutorial.theme.pointer_seconds
    keys: list[tuple] = []
    current = None
    if index > 0 and tutorial.steps[index - 1].points:
        before = tutorial._pointer_track(index - 1)
        if before:
            last = before[-1]
            current = (last[1], last[2], last[3])
            keys.append((0.0, *current, 1.0, 1.0))
    free = 0.0
    for stop, pose in stops:
        here = (pose.x, pose.y, pose.angle)
        at = max(min(stop.at, step.duration), free)
        if current is None:
            keys += [(at, *here, 1.0, 0.0), (at + APPEAR, *here, 1.0, 1.0)]
            arrive = at + APPEAR
        else:
            if not keys or at > keys[-1][0]:
                keys.append((at, *current, 1.0, 1.0))
            keys.append((at + glide, *here, 1.0, 1.0))
            arrive = at + glide
        keys += [(arrive + TAP / 2, *here, TAP_SCALE, 1.0), (arrive + TAP, *here, 1.0, 1.0)]
        free, current = arrive + TAP, here
    return [tuple(round(v, 3) for v in key) for key in keys]
