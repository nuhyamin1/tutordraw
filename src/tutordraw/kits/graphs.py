"""Maths kits: axes you can plot into, and a number line with hops."""

from __future__ import annotations

import math
from typing import Callable

from drawcv import (Arrow, BoundingBox, Circle, Color, FillStyle, Group, Line, Path, Point, Polygon,
                    StrokeStyle, Text)

from ..adapters.drawcv import fixed_pivot
from ..errors import ValidationError
from ..validation import finite_number, rgb
from ._base import CURVE, GRID, GRID_TAG, INK, KIT_KEY, _pair, _point

HOP_PEAK = 45.0  # px: the most a number-line hop rises above (or dips below) its line
ACCENT = (214, 96, 50)  # tangents and secants: warm, so they stand apart from the curve
SHADE = 0.3  # the fill opacity of regions and rectangles, so the grid and curve show through
RULES = ("left", "right", "mid")


def _value(f, x: float) -> float:
    """f(x) as a float, or NaN where f fails or has no finite value."""
    try:
        y = float(f(x))
    except (ArithmeticError, ValueError, TypeError):
        return math.nan
    return y if math.isfinite(y) else math.nan


def _samples(samples) -> int:
    if isinstance(samples, bool) or not isinstance(samples, int) or not 2 <= samples <= 5000:
        raise ValidationError("samples must be an integer from 2 to 5000")
    return samples


def _slope(f, x: float) -> float:
    """The derivative of f at x, or NaN where there is no single tangent (a corner, a jump, no value).

    Both one-sided slopes are taken over a tiny step and must agree, so |x|
    at 0 has none; the central difference over a slightly larger step is the
    value, accurate to about 1e-9 for ordinary functions.
    """
    tiny = 1e-6 * max(1.0, abs(x))
    here, left, right = _value(f, x), _value(f, x - tiny), _value(f, x + tiny)
    if any(math.isnan(v) for v in (here, left, right)):
        return math.nan
    before, after = (here - left) / tiny, (right - here) / tiny
    if abs(before - after) > 1e-3 * max(1.0, abs(before), abs(after)):
        return math.nan
    step = 1e-5 * max(1.0, abs(x))
    a, b = _value(f, x - step), _value(f, x + step)
    return math.nan if math.isnan(a) or math.isnan(b) else (b - a) / (2 * step)


def _clip_polygon(points: list[Point], box: BoundingBox) -> list[Point]:
    """A polygon cut to an axis-aligned box (Sutherland-Hodgman); [] if none of it is inside."""
    def at_x(x):
        return lambda p, q: Point(x, p.y + (q.y - p.y) * (x - p.x) / (q.x - p.x))

    def at_y(y):
        return lambda p, q: Point(p.x + (q.x - p.x) * (y - p.y) / (q.y - p.y), y)

    edges = ((lambda p: p.x >= box.left, at_x(box.left)), (lambda p: p.x <= box.right, at_x(box.right)),
             (lambda p: p.y >= box.top, at_y(box.top)), (lambda p: p.y <= box.bottom, at_y(box.bottom)))
    for inside, cross in edges:
        kept = []
        for i, current in enumerate(points):
            previous = points[i - 1]
            if inside(current):
                if not inside(previous):
                    kept.append(cross(previous, current))
                kept.append(current)
            elif inside(previous):
                kept.append(cross(previous, current))
        points = kept
        if not points:
            return []
    return points


def _clip_segment(p: Point, q: Point, box: BoundingBox) -> tuple[Point, Point] | None:
    """The part of segment pq inside an axis-aligned box (Liang-Barsky), or None."""
    t0, t1 = 0.0, 1.0
    dx, dy = q.x - p.x, q.y - p.y
    for towards, room in ((-dx, p.x - box.left), (dx, box.right - p.x),
                          (-dy, p.y - box.top), (dy, box.bottom - p.y)):
        if towards == 0:
            if room < 0:
                return None
            continue
        t = room / towards
        if towards < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return Point(p.x + t0 * dx, p.y + t0 * dy), Point(p.x + t1 * dx, p.y + t1 * dy)


def _clip_polyline(points: list[Point], box: BoundingBox) -> list[list[Point]]:
    """An open line cut to a box: one piece for each stretch inside it."""
    pieces, current = [], []
    for p, q in zip(points, points[1:]):
        segment = _clip_segment(p, q, box)
        if segment is None:
            if len(current) > 1:
                pieces.append(current)
            current = []
            continue
        a, b = segment
        if not current or math.dist((current[-1].x, current[-1].y), (a.x, a.y)) > 1e-9:
            if len(current) > 1:
                pieces.append(current)
            current = [a]
        current.append(b)
        if math.dist((b.x, b.y), (q.x, q.y)) > 1e-9:  # cut short: it leaves the box here
            pieces.append(current)
            current = []
    if len(current) > 1:
        pieces.append(current)
    return pieces


def nice_step(span: float, target_ticks: int = 8) -> float:
    """A 1, 2 or 5 x 10^k step giving about `target_ticks` ticks across `span`."""
    raw = span / max(target_ticks, 1)
    power = 10 ** math.floor(math.log10(raw))
    steps = [m * power * scale for scale in (0.1, 1, 10) for m in (1, 2, 5)]
    # Closest tick count on a log scale: 10 ticks and 5 are equally "off" 7.
    return min(steps, key=lambda step: abs(math.log((span / step) / target_ticks)))


def format_number(value: float, step: float) -> str:
    """Tick text: as few decimals as the step needs, ASCII minus, no "-0"."""
    decimals = max(0, -math.floor(math.log10(step) + 1e-9)) if step < 1 else 0
    text = f"{value:.{decimals}f}"
    return "0" if text in ("-0", "-0.0", "-0.00") or float(text) == 0 else text


NUMBER_GAP = 2.0  # px kept between two tick numbers on Axes


class Axes:
    """A pair of labelled axes with a coordinate system you can plot into.

    `box` is (left, top, width, height) on the canvas; `x_range` and `y_range`
    are the maths coordinates at its edges. Steps default to a round 1/2/5
    spacing. Axes cross at 0 when 0 is in range, else at the lower edge.
    """

    def __init__(self, tutorial, *, box, x_range, y_range, x_step: float | None = None,
                 y_step: float | None = None, x_label: str | None = "x",
                 y_label: str | None = "y", grid: bool = False, name: str = "axes",
                 color=INK, font_scale: float = 0.5):
        if not isinstance(box, (tuple, list)) or len(box) != 4:
            raise ValidationError("box must be (left, top, width, height)")
        left, top, width, height = (finite_number(v, "box") for v in box)
        if width <= 0 or height <= 0:
            raise ValidationError("box width and height must be positive")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("name must be a non-empty string")
        self.tutorial = tutorial
        self.name = name
        self.box = BoundingBox(left, top, width, height)
        self.x_range = _pair(x_range, "x_range")
        self.y_range = _pair(y_range, "y_range")
        self.x_step = self._step(x_step, self.x_range, "x_step")
        self.y_step = self._step(y_step, self.y_range, "y_step")
        self.color = rgb(color, "color")
        self.font_scale = finite_number(font_scale, "font_scale", minimum=0)
        if not isinstance(grid, bool):
            raise ValidationError("grid must be a boolean")
        self._count = 0
        # An explicit pivot: with the default (the group's own centre) DrawCV
        # recomputes the whole group's bounds, curves included, every time a
        # child is mapped to world space, which made one render take seconds.
        self.group = Group(children=[], name=name, transform=fixed_pivot())
        self.group.metadata = {KIT_KEY: {"kit": "axes", "box": [left, top, width, height],
                                         "x_range": list(self.x_range),
                                         "y_range": list(self.y_range),
                                         "x_step": self.x_step, "y_step": self.y_step}}
        self._draw(grid, x_label, y_label)
        tutorial.scene.add(self.group)
        self.x_axis = tutorial.target(self._x_axis, name=f"{name}_x_axis")
        self.y_axis = tutorial.target(self._y_axis, name=f"{name}_y_axis")

    # --- coordinates ---------------------------------------------------------

    @staticmethod
    def _step(step, extent, name):
        if step is None:
            return nice_step(extent[1] - extent[0])
        step = finite_number(step, name, minimum=0)
        if step == 0 or (extent[1] - extent[0]) / step > 200:
            raise ValidationError(f"{name} must be positive and give at most 200 ticks")
        return step

    def to_scene(self, x: float, y: float) -> Point:
        """Where the maths point (x, y) is on the canvas."""
        (x0, x1), (y0, y1) = self.x_range, self.y_range
        b = self.box
        return Point(b.left + (x - x0) / (x1 - x0) * b.width,
                     b.top + b.height - (y - y0) / (y1 - y0) * b.height)

    @property
    def origin(self) -> tuple[float, float]:
        """Where the axes cross, in maths coordinates."""
        (x0, x1), (y0, y1) = self.x_range, self.y_range
        return (0.0 if x0 <= 0 <= x1 else x0), (0.0 if y0 <= 0 <= y1 else y0)

    def _ticks(self, extent, step):
        first = math.ceil(extent[0] / step - 1e-9)
        last = math.floor(extent[1] / step + 1e-9)
        return [k * step for k in range(first, last + 1)]

    # --- drawing -------------------------------------------------------------

    def _text(self, content: str, anchor: Point, align: str) -> Text:
        """Text placed by an anchor: "below", "left" or "below-left" of the point."""
        text = Text(text=content, position=Point(0, 0), font_scale=self.font_scale,
                    color=Color(*self.color))
        box = text.get_bounds()
        if align == "below":
            text.position = Point(anchor.x - box.width / 2, anchor.y + 6)
        elif align == "left":
            text.position = Point(anchor.x - box.width - 7, anchor.y - box.height / 2)
        else:
            text.position = Point(anchor.x - box.width - 6, anchor.y + 6)
        return text

    def _draw(self, grid: bool, x_label, y_label) -> None:
        ink = StrokeStyle(color=Color(*self.color), width=2)
        thin = StrokeStyle(color=Color(*self.color), width=1)
        ox, oy = self.origin
        b = self.box
        xs, ys = self._ticks(self.x_range, self.x_step), self._ticks(self.y_range, self.y_step)
        parts = []
        if grid:
            faint = StrokeStyle(color=Color(*GRID), width=1)
            lines = [Line(start=Point(p.x, b.top), end=Point(p.x, b.bottom), stroke=faint)
                     for p in (self.to_scene(x, 0) for x in xs)]
            lines += [Line(start=Point(b.left, p.y), end=Point(b.right, p.y), stroke=faint)
                      for p in (self.to_scene(0, y) for y in ys)]
            for line in lines:
                line.add_tag(GRID_TAG)  # placement keeps panels off it (collision.plan_annotations)
            parts += lines
        start, end = self.to_scene(self.x_range[0], oy), self.to_scene(self.x_range[1], oy)
        self._x_axis = Arrow(start=start, end=Point(end.x + 14, end.y), stroke=ink,
                             fill=FillStyle(color=Color(*self.color)), head_length=10, head_width=8)
        start, end = self.to_scene(ox, self.y_range[0]), self.to_scene(ox, self.y_range[1])
        self._y_axis = Arrow(start=start, end=Point(end.x, end.y - 14), stroke=ink,
                             fill=FillStyle(color=Color(*self.color)), head_length=10, head_width=8)
        parts += [self._x_axis, self._y_axis]
        crossing = (self.x_range[0] < 0 < self.x_range[1]) and (self.y_range[0] < 0 < self.y_range[1])
        origin = self._text("0", self.to_scene(0, 0), "below-left") if crossing else None
        # A number that would touch one already written is left out, its tick still drawn: with a
        # range starting just below 0, "-0.5" sat on the origin's "0", and the two "-0.5"s met at
        # the corner. The origin's number is written first, then x's, then y's.
        written = [origin.get_bounds()] if origin is not None else []

        def number(text: Text) -> None:
            box = text.get_bounds()
            if not any(box.left < b.right + NUMBER_GAP and b.left < box.right + NUMBER_GAP
                       and box.top < b.bottom + NUMBER_GAP and b.top < box.bottom + NUMBER_GAP
                       for b in written):
                written.append(box)
                parts.append(text)

        for x in xs:
            if crossing and abs(x) < self.x_step / 2:
                continue  # the origin is labelled once, below
            p = self.to_scene(x, oy)
            parts.append(Line(start=Point(p.x, p.y - 4), end=Point(p.x, p.y + 4), stroke=thin))
            number(self._text(format_number(x, self.x_step), p, "below"))
        for y in ys:
            if crossing and abs(y) < self.y_step / 2:
                continue
            p = self.to_scene(ox, y)
            parts.append(Line(start=Point(p.x - 4, p.y), end=Point(p.x + 4, p.y), stroke=thin))
            number(self._text(format_number(y, self.y_step), p, "left"))
        if origin is not None:
            parts.append(origin)
        if x_label:
            end = self.to_scene(self.x_range[1], oy)
            label = Text(text=x_label, position=Point(end.x + 18, end.y - 10),
                         font_scale=self.font_scale * 1.2, color=Color(*self.color))
            parts.append(label)
        if y_label:
            end = self.to_scene(ox, self.y_range[1])
            label = Text(text=y_label, position=Point(end.x + 8, end.y - 30),
                         font_scale=self.font_scale * 1.2, color=Color(*self.color))
            parts.append(label)
        for part in parts:
            self.group.add(part, preserve_world_transform=False)

    def _name(self, name: str | None, kind: str) -> str:
        if name is None:
            self._count += 1
            return f"{self.name}_{kind}{self._count}"
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("name must be a non-empty string")
        return name

    # --- plotting ------------------------------------------------------------

    def plot(self, f: Callable[[float], float], *, name: str | None = None,
             domain: tuple[float, float] | None = None, samples: int = 240,
             color=CURVE, width: float = 3):
        """Draw y = f(x) and return it as a target.

        Points where f fails or is not finite break the curve (so 1/x has two
        branches), and the curve is cut where it leaves the y range, meeting the
        edge exactly. Label a spot on it with `point(x, f(x), visible=False)`.
        """
        if not callable(f):
            raise ValidationError("f must be a function of x")
        low, high = self.x_range if domain is None else _pair(domain, "domain")
        samples = _samples(samples)
        y0, y1 = self.y_range
        values = []
        for i in range(samples):
            x = low + (high - low) * i / (samples - 1)
            try:
                y = float(f(x))
            except (ArithmeticError, ValueError, TypeError):
                y = math.nan
            values.append((x, y if math.isfinite(y) else math.nan))
        segments, current = [], []

        def inside(y):
            return y0 <= y <= y1

        for (xa, ya), (xb, yb) in zip(values, values[1:] + [(math.nan, math.nan)]):
            if math.isnan(ya):
                if current:
                    segments.append(current)
                current = []
                continue
            if inside(ya):
                current.append((xa, ya))
            if math.isnan(yb):
                continue
            if inside(ya) != inside(yb):
                # Crossing the edge: end (or start) exactly on it.
                edge = y1 if max(ya, yb) > y1 else y0
                t = (edge - ya) / (yb - ya)
                current.append((xa + (xb - xa) * t, edge))
                if inside(ya):
                    segments.append(current)
                    current = []
        if current:
            segments.append(current)
        segments = [s for s in segments if len(s) > 1]
        if not segments:
            raise ValidationError("Nothing of the curve lies inside the axes' x and y ranges")
        path = Path(stroke=StrokeStyle(color=Color(*rgb(color, "color")),
                                       width=finite_number(width, "width", minimum=0)),
                    transform=fixed_pivot())
        for segment in segments:
            path.move_to(self.to_scene(*segment[0]))
            for x, y in segment[1:]:
                path.line_to(self.to_scene(x, y))
        self.group.add(path, preserve_world_transform=False)
        return self.tutorial.target(path, name=self._name(name, "plot"))

    def point(self, x: float, y: float, *, name: str | None = None, radius: float = 5,
              color=CURVE, visible: bool = True):
        """A dot at (x, y). With visible=False it is an anchor to label a curve at."""
        x, y = finite_number(x, "x"), finite_number(y, "y")
        if not (self.x_range[0] <= x <= self.x_range[1] and self.y_range[0] <= y <= self.y_range[1]):
            raise ValidationError(f"({x:g}, {y:g}) is outside the axes' ranges")
        if not isinstance(visible, bool):
            raise ValidationError("visible must be a boolean")
        radius = finite_number(radius, "radius", minimum=0)
        dot = Circle(center=self.to_scene(x, y), radius=radius if visible else 0.5,
                     fill=FillStyle(color=Color(*rgb(color, "color"))),
                     opacity=1.0 if visible else 0.001)
        self.group.add(dot, preserve_world_transform=False)
        return self.tutorial.target(dot, name=self._name(name, "point"))

    def guide(self, *, x: float | None = None, y: float | None = None, name: str | None = None):
        """Dashed guide lines: x=a is vertical, y=b horizontal, both drop from (a, b) to the axes."""
        if x is None and y is None:
            raise ValidationError("guide needs x, y or both")
        dash = StrokeStyle(color=Color(*self.color), width=1.5, dash_array=(6.0, 5.0))
        ox, oy = self.origin
        path = Path(stroke=dash, transform=fixed_pivot())
        if x is not None and y is not None:
            corner = self.to_scene(finite_number(x, "x"), finite_number(y, "y"))
            path.move_to(self.to_scene(x, oy))
            path.line_to(corner)
            path.line_to(self.to_scene(ox, y))
        elif x is not None:
            x = finite_number(x, "x")
            path.move_to(self.to_scene(x, self.y_range[0]))
            path.line_to(self.to_scene(x, self.y_range[1]))
        else:
            y = finite_number(y, "y")
            path.move_to(self.to_scene(self.x_range[0], y))
            path.line_to(self.to_scene(self.x_range[1], y))
        self.group.add(path, preserve_world_transform=False)
        return self.tutorial.target(path, name=self._name(name, "guide"))

    # --- drawing in maths coordinates ----------------------------------------

    def along(self, f, x_from: float, x_to: float, *, samples: int = 32,
              start=None) -> list[tuple[float, float]]:
        """The way along y = f(x) from x_from to x_to, as canvas offsets for `Step.restyle`.

        `samples` + 1 evenly spaced points, each as (dx, dy) pixels from
        `start`, a maths point (default the curve's own point at x_from),
        which is where the thing being moved was first drawn. So
        `restyle(dot, move=way[-1], via=way[1:-1])` on an animated step
        slides a dot drawn at (1, f(1)) along the curve, and the step after
        it keeps `move=way[-1]`. Refuses a curve with no value on the way.
        """
        samples = _samples(samples)
        x_from, x_to = finite_number(x_from, "x_from"), finite_number(x_to, "x_to")
        xs = [x_from + (x_to - x_from) * k / samples for k in range(samples + 1)]
        ys = [_value(f, x) for x in xs]
        missing = next((x for x, y in zip(xs, ys) if math.isnan(y)), None)
        if missing is not None:
            raise ValidationError(f"The curve has no value at x = {missing:g}, so nothing can move along it there")
        if start is None:
            start = (x_from, ys[0])
        sx, sy = (finite_number(v, "start") for v in start)
        origin = self.to_scene(sx, sy)
        return [(p.x - origin.x, p.y - origin.y) for p in (self.to_scene(x, y) for x, y in zip(xs, ys))]

    def to_scene_offset(self, dx: float, dy: float) -> tuple[float, float]:
        """A maths displacement (dx, dy) in canvas pixels; y points up in maths and down on the canvas."""
        (x0, x1), (y0, y1) = self.x_range, self.y_range
        return (finite_number(dx, "dx") * self.box.width / (x1 - x0),
                -finite_number(dy, "dy") * self.box.height / (y1 - y0))

    def contains(self, x: float, y: float) -> bool:
        """Whether the maths point (x, y) is inside the axes' ranges."""
        return (self.x_range[0] <= finite_number(x, "x") <= self.x_range[1]
                and self.y_range[0] <= finite_number(y, "y") <= self.y_range[1])

    def clip(self, points, *, closed: bool = False) -> list[list[Point]]:
        """Maths points as canvas points, cut exactly where they leave the plot area.

        For drawing your own shapes in the graph's coordinates: a closed shape
        (a polygon) gives one piece, an open line one piece per stretch inside
        the ranges, and nothing inside gives []. Cutting the geometry, rather
        than masking it, keeps its bounds true, so labels and marks sit by
        what is visible. Pass the pieces to DrawCV shapes and `add` them.
        """
        if not isinstance(closed, bool):
            raise ValidationError("closed must be a boolean")
        if not isinstance(points, (tuple, list)) or len(points) < (3 if closed else 2):
            raise ValidationError(f"points must be a list of at least {3 if closed else 2} (x, y) pairs")
        scene = [self.to_scene(q.x, q.y) for q in (_point(p, "points") for p in points)]
        if closed:
            shape = _clip_polygon(scene, self.box)
            return [shape] if len(shape) >= 3 else []
        return _clip_polyline(scene, self.box)

    def add(self, drawable, *, name: str | None = None):
        """Make a DrawCV drawable part of the graph and return it as a target.

        It joins the axes' group, so it hides, fades and moves with the graph.
        Build it from `to_scene`, `to_scene_offset` or `clip` so it lines up.
        """
        if not hasattr(drawable, "get_bounds") or not hasattr(drawable, "transform"):
            raise ValidationError("add expects a DrawCV drawable")
        self.group.add(drawable, preserve_world_transform=False)
        return self.tutorial.target(drawable, name=self._name(name, "shape"))

    # --- constructions -------------------------------------------------------

    def _domain(self, domain) -> tuple[float, float]:
        """`domain`, or the whole x range, cut to the x range."""
        if domain is None:
            return self.x_range
        low, high = _pair(domain, "domain")
        low, high = max(low, self.x_range[0]), min(high, self.x_range[1])
        if not low < high:
            raise ValidationError(f"domain {tuple(domain)} lies outside the axes' x range "
                                  f"{self.x_range[0]:g} to {self.x_range[1]:g}")
        return low, high

    @staticmethod
    def _boundary(value, what: str):
        """A boundary of a region: a function of x, or a number for a horizontal line such as y = 0."""
        if callable(value):
            return value
        height = finite_number(value, what)
        return lambda x: height

    @staticmethod
    def _shade(color, opacity) -> tuple[tuple[int, int, int], float]:
        opacity = finite_number(opacity, "opacity", minimum=0)
        if opacity > 1:
            raise ValidationError("opacity must be between 0 and 1")
        return rgb(color, "color"), opacity

    def region(self, f, g=0.0, *, domain=None, samples: int = 240, color=CURVE, opacity: float = SHADE,
               name: str | None = None):
        """Shade between y = f(x) and y = g(x) and return it as a target.

        With the default g = 0 it is the area under a curve; with two curves
        the area between them; with a number, everything above or below a
        level (g = 9 on axes up to 9 shades y > f(x)). Both are sampled like
        `plot`, so the shading meets the curve exactly; it is cut to the
        ranges, breaks where either has no value, and sits beneath the grid
        and curves. `domain` limits it in x (the whole x range by default).
        """
        top, bottom = self._boundary(f, "f"), self._boundary(g, "g")
        low, high = self._domain(domain)
        samples = _samples(samples)
        tint, opacity = self._shade(color, opacity)
        y0, y1 = self.y_range
        runs, run = [], []
        for i in range(samples):
            x = low + (high - low) * i / (samples - 1)
            a, b = _value(top, x), _value(bottom, x)
            if math.isnan(a) or math.isnan(b):
                if len(run) > 1:
                    runs.append(run)
                run = []
                continue
            run.append((x, min(max(a, y0), y1), min(max(b, y0), y1)))
        if len(run) > 1:
            runs.append(run)
        runs = [run for run in runs if any(a != b for _, a, b in run)]
        if not runs:
            raise ValidationError(f"Nothing to shade: the two boundaries have no values, or no gap between them "
                                  f"inside the axes, from x = {low:g} to {high:g}")
        path = Path(fill=FillStyle(color=Color(*tint), opacity=opacity), z_index=-1, transform=fixed_pivot())
        for run in runs:
            path.move_to(self.to_scene(run[0][0], run[0][1]))
            for x, a, _ in run[1:]:
                path.line_to(self.to_scene(x, a))
            for x, _, b in reversed(run):
                path.line_to(self.to_scene(x, b))
            path.close()
        self.group.add(path, preserve_world_transform=False)
        return self.tutorial.target(path, name=self._name(name, "region"))

    def rectangles(self, f, domain, count: int, *, rule: str = "left", color=CURVE, opacity: float = SHADE,
                   name: str | None = None):
        """`count` equal rectangles from y = 0 up to f, across `domain`: a Riemann sum.

        `rule` picks where each rectangle meets the curve: its "left" edge,
        its "right" edge or its "mid"point. Heights are cut to the y range, and
        a rectangle where f has no value is left out. One target for them all.
        """
        if not callable(f):
            raise ValidationError("f must be a function of x")
        a, b = _pair(domain, "domain")
        x0, x1 = self.x_range
        if a < x0 or b > x1:
            raise ValidationError(f"domain ({a:g}, {b:g}) must lie inside the axes' x range {x0:g} to {x1:g}")
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 500:
            raise ValidationError("count must be a whole number from 1 to 500")
        if rule not in RULES:
            raise ValidationError(f"rule must be one of {', '.join(RULES)}")
        tint, opacity = self._shade(color, opacity)
        y0, y1 = self.y_range
        base = min(max(0.0, y0), y1)
        path = Path(fill=FillStyle(color=Color(*tint), opacity=opacity),
                    stroke=StrokeStyle(color=Color(*tint), width=1.5), z_index=-1, transform=fixed_pivot())
        drawn = 0
        for i in range(count):
            left, right = a + (b - a) * i / count, a + (b - a) * (i + 1) / count
            height = _value(f, {"left": left, "right": right, "mid": (left + right) / 2}[rule])
            if math.isnan(height) or min(max(height, y0), y1) == base:
                continue
            top = min(max(height, y0), y1)
            path.move_to(self.to_scene(left, base))
            for corner in ((right, base), (right, top), (left, top)):
                path.line_to(self.to_scene(*corner))
            path.close()
            drawn += 1
        if not drawn:
            raise ValidationError(f"No rectangles to draw: f has no value, or is 0, at every {rule} point")
        self.group.add(path, preserve_world_transform=False)
        return self.tutorial.target(path, name=self._name(name, "rectangles"))

    def _straight(self, x: float, y: float, slope: float, span, color, width, name, kind: str):
        """The line through (x, y) with this slope, across `span`, cut to the plot area."""
        low, high = self._domain(span)
        stroke = StrokeStyle(color=Color(*rgb(color, "color")), width=finite_number(width, "width", minimum=0))
        pieces = _clip_polyline([self.to_scene(low, y + slope * (low - x)),
                                 self.to_scene(high, y + slope * (high - x))], self.box)
        if not pieces:
            raise ValidationError(f"None of the {kind} lies inside the axes from x = {low:g} to {high:g}; "
                                  "widen the span or the y range")
        line = Line(start=pieces[0][0], end=pieces[0][-1], stroke=stroke)
        self.group.add(line, preserve_world_transform=False)
        return self.tutorial.target(line, name=self._name(name, kind))

    def _on_curve(self, f, x, what: str) -> tuple[float, float]:
        if not callable(f):
            raise ValidationError("f must be a function of x")
        x = finite_number(x, what)
        y = _value(f, x)
        if math.isnan(y):
            raise ValidationError(f"The curve has no value at {what} = {x:g}")
        return x, y

    def tangent(self, f, x: float, *, span=None, color=ACCENT, width: float = 2.5, name: str | None = None):
        """The tangent to y = f(x) at x, drawn across `span` (the whole x range by default).

        The slope is worked out from f, so the line touches the curve exactly.
        It is refused where the curve has no single tangent: a corner, a jump,
        or no value there. (x, f(x)) must be inside the ranges.
        """
        x, y = self._on_curve(f, x, "x")
        if not self.contains(x, y):
            raise ValidationError(f"({x:g}, {y:g}) is outside the axes' ranges")
        slope = _slope(f, x)
        if math.isnan(slope):
            raise ValidationError(f"The curve has no single tangent at x = {x:g}: it has a corner, a jump "
                                  "or a vertical tangent there")
        return self._straight(x, y, slope, span, color, width, name, "tangent")

    def secant(self, f, x1: float, x2: float, *, span=None, color=ACCENT, width: float = 2.5,
               name: str | None = None):
        """The straight line through the curve at x1 and x2, across `span` (the whole x range by default).

        Give `span=(x1, x2)` for just the chord between the two points.
        """
        a, fa = self._on_curve(f, x1, "x1")
        b, fb = self._on_curve(f, x2, "x2")
        if a == b:
            raise ValidationError("a secant needs two different x values; use tangent for one")
        return self._straight(a, fa, (fb - fa) / (b - a), span, color, width, name, "secant")

    def intersections(self, f, g=0.0, *, domain=None, samples: int = 2000) -> list[tuple[float, float]]:
        """Where y = f(x) meets y = g(x), as (x, y) pairs from left to right; with g = 0, f's roots.

        Crossings are found where f - g changes sign and refined by bisection;
        a curve that only touches the other (x^2 and 0 at 0) is found too. A
        jump across the other curve (tan x at pi/2) is not a meeting point.
        The points may lie outside the y range; `contains` says.
        """
        top, bottom = self._boundary(f, "f"), self._boundary(g, "g")
        low, high = self._domain(domain)
        if isinstance(samples, bool) or not isinstance(samples, int) or not 10 <= samples <= 20000:
            raise ValidationError("samples must be an integer from 10 to 20000")
        xs = [low + (high - low) * i / (samples - 1) for i in range(samples)]
        gap = [_value(top, x) - _value(bottom, x) for x in xs]
        close = 1e-6 * (self.y_range[1] - self.y_range[0])

        def difference(x):
            return _value(top, x) - _value(bottom, x)

        found = []
        for i, d in enumerate(gap):
            if d == 0:
                found.append(xs[i])
        for i in range(samples - 1):
            a, b = gap[i], gap[i + 1]
            if math.isnan(a) or math.isnan(b) or a * b >= 0:
                continue
            left, right = xs[i], xs[i + 1]
            for _ in range(80):
                middle = (left + right) / 2
                d = difference(middle)
                if math.isnan(d):
                    break
                if (d < 0) == (a < 0):
                    left = middle
                else:
                    right = middle
            x = (left + right) / 2
            if abs(difference(x)) <= close:
                found.append(x)
        for i in range(1, samples - 1):
            a, b, c = gap[i - 1], gap[i], gap[i + 1]
            if any(math.isnan(v) for v in (a, b, c)) or not (a * b > 0 and b * c > 0) \
                    or not abs(b) <= min(abs(a), abs(c)):
                continue
            left, right = xs[i - 1], xs[i + 1]  # a touch: the gap's smallest size, by golden-section search
            for _ in range(100):
                m1, m2 = left + (right - left) * 0.382, left + (right - left) * 0.618
                if abs(difference(m1)) < abs(difference(m2)):
                    right = m2
                else:
                    left = m1
            x = (left + right) / 2
            if abs(difference(x)) <= close:
                found.append(x)
        found.sort()
        merged = []
        for x in found:
            if not merged or x - merged[-1] > 1.5 * (high - low) / samples:
                merged.append(x)

        def tidy(value, span):  # rounding error around 0 reads as 0, not 7e-25
            return 0.0 if abs(value) < 1e-12 * span else value
        return [(tidy(x, high - low), tidy(_value(top, x), self.y_range[1] - self.y_range[0])) for x in merged]

    # --- after reloading a lesson -------------------------------------------

    @classmethod
    def find(cls, tutorial, name: str = "axes") -> Axes:
        """Reattach to axes saved in a lesson, to plot more into them."""
        from ..adapters.drawcv import index_scene

        for obj in index_scene(tutorial.scene).values():
            data = getattr(obj, "metadata", {}).get(KIT_KEY)
            if isinstance(obj, Group) and obj.name == name and isinstance(data, dict) \
                    and data.get("kit") == "axes":
                axes = cls.__new__(cls)
                axes.tutorial, axes.name, axes.group = tutorial, name, obj
                axes.box = BoundingBox(*data["box"])
                axes.x_range, axes.y_range = tuple(data["x_range"]), tuple(data["y_range"])
                axes.x_step, axes.y_step = data["x_step"], data["y_step"]
                axes.color, axes.font_scale = INK, 0.5
                axes.x_axis = tutorial.get_target(f"{name}_x_axis")
                axes.y_axis = tutorial.get_target(f"{name}_y_axis")
                existing = [t.name for t in tutorial.targets if t.name and t.name.startswith(f"{name}_")]
                axes._count = len(existing)
                return axes
        raise ValidationError(f"No axes named {name!r} in this lesson")


class NumberLine:
    """A horizontal number line with ticks, for arithmetic and inequalities.

    `start` is the left end on the canvas and `length` its width in pixels;
    `value_range` is the numbers at its ends. The step defaults to a round
    1, 2 or 5 x 10^n giving about ten ticks.
    """

    def __init__(self, tutorial, *, start, length: float, value_range, step: float | None = None,
                 name: str = "number_line", color=INK, font_scale: float = 0.55):
        if not isinstance(start, (tuple, list)) or len(start) != 2:
            raise ValidationError("start must be (x, y)")
        x, y = (finite_number(v, "start") for v in start)
        length = finite_number(length, "length", minimum=0)
        if length == 0:
            raise ValidationError("length must be positive")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("name must be a non-empty string")
        self.tutorial, self.name = tutorial, name
        self.start, self.length = Point(x, y), length
        self.value_range = _pair(value_range, "value_range")
        if step is None:
            self.step = nice_step(self.value_range[1] - self.value_range[0], target_ticks=10)
        else:
            self.step = finite_number(step, "step", minimum=0)
            if self.step == 0 or (self.value_range[1] - self.value_range[0]) / self.step > 200:
                raise ValidationError("step must be positive and give at most 200 ticks")
        self.color = rgb(color, "color")
        self.font_scale = finite_number(font_scale, "font_scale", minimum=0)
        self._count = 0
        self.group = Group(children=[], name=name, transform=fixed_pivot())
        self.group.metadata = {KIT_KEY: {"kit": "number_line", "start": [x, y], "length": length,
                                         "value_range": list(self.value_range), "step": self.step}}
        self._draw()
        tutorial.scene.add(self.group)
        self.line = tutorial.target(self._line, name=f"{name}_line")

    def to_scene(self, value: float) -> Point:
        """Where a value sits on the canvas."""
        low, high = self.value_range
        return Point(self.start.x + (value - low) / (high - low) * self.length, self.start.y)

    def _in_range(self, value, what: str) -> float:
        value = finite_number(value, what)
        if not self.value_range[0] <= value <= self.value_range[1]:
            raise ValidationError(f"{what} {value:g} is outside the number line's range")
        return value

    def _head(self, tip: Point, direction: float) -> Polygon:
        return Polygon(vertices=[tip, Point(tip.x - 10 * direction, tip.y - 5),
                                 Point(tip.x - 10 * direction, tip.y + 5)],
                       fill=FillStyle(color=Color(*self.color)))

    def _draw(self) -> None:
        ink = StrokeStyle(color=Color(*self.color), width=2)
        left, right = self.start, Point(self.start.x + self.length, self.start.y)
        self._line = Line(start=Point(left.x - 16, left.y), end=Point(right.x + 16, right.y), stroke=ink)
        parts = [self._line, self._head(Point(right.x + 22, right.y), 1),
                 self._head(Point(left.x - 22, left.y), -1)]
        low, high = self.value_range
        first, last = math.ceil(low / self.step - 1e-9), math.floor(high / self.step + 1e-9)
        for k in range(first, last + 1):
            value = k * self.step
            p = self.to_scene(value)
            parts.append(Line(start=Point(p.x, p.y - 6), end=Point(p.x, p.y + 6), stroke=ink))
            text = Text(text=format_number(value, self.step), position=Point(0, 0),
                        font_scale=self.font_scale, color=Color(*self.color))
            box = text.get_bounds()
            text.position = Point(p.x - box.width / 2, p.y + 12)
            parts.append(text)
        for part in parts:
            self.group.add(part, preserve_world_transform=False)

    def _name(self, name, kind):
        return Axes._name(self, name, kind)

    def point(self, value: float, *, name: str | None = None, open: bool = False,
              radius: float = 7, color=CURVE):
        """A dot on the line. `open=True` draws it hollow, as for a strict inequality."""
        value = self._in_range(value, "value")
        if not isinstance(open, bool):
            raise ValidationError("open must be a boolean")
        tint = Color(*rgb(color, "color"))
        dot = Circle(center=self.to_scene(value), radius=finite_number(radius, "radius", minimum=0),
                     fill=FillStyle(color=Color(255, 255, 255) if open else tint),
                     stroke=StrokeStyle(color=tint, width=2.5), z_index=2)
        self.group.add(dot, preserve_world_transform=False)
        return self.tutorial.target(dot, name=self._name(name, "point"))

    def anchor(self, value: float):
        """An invisible target at a value, named "<name>_at_<value>", reused if it exists.

        Marks such as `step.connect` need targets at their ends; these read well
        in descriptions ("the number line at 5").
        """
        value = self._in_range(value, "value")
        name = f"{self.name}_at_{format_number(value, self.step)}"
        try:
            return self.tutorial.get_target(name)
        except ValidationError:
            dot = Circle(center=self.to_scene(value), radius=0.5, opacity=0.001,
                         fill=FillStyle(color=Color(*self.color)))
            self.group.add(dot, preserve_world_transform=False)
            return self.tutorial.target(dot, name=name)

    def hop(self, step, start: float, end: float, text: str | None = None, *,
            at: float | None = None, draw: bool = True, bend: float | None = None):
        """A hop arrow in one step, as used to teach +3 or -2; returns the Mark.

        It is a step mark (`step.connect` between anchors on the line), so it
        belongs to that step only, draws on by default, takes `at=` and can be
        a narration cue. Rightward hops arc above the line, leftward below.
        """
        a, b = self._in_range(start, "start"), self._in_range(end, "end")
        if a == b:
            raise ValidationError("a hop needs two different values")
        if bend is None:
            # Arc height is half the bend times the length; cap it at HOP_PEAK px
            # so a long hop stays close to its line instead of ballooning.
            length = abs(self.to_scene(b).x - self.to_scene(a).x)
            bend = min(0.35, 2 * HOP_PEAK / length)
        bend = finite_number(bend, "bend")
        if not 0 < bend <= 1:
            raise ValidationError("bend must be greater than 0 and at most 1")
        # connect's positive bend lifts toward the top of the screen.
        return step.connect(self.anchor(a), self.anchor(b), text,
                            bend=bend if b > a else -bend, at=at, draw=draw)

    def interval(self, start: float, end: float, *, name: str | None = None, open_start: bool = False,
                 open_end: bool = False, color=(40, 150, 90)):
        """A highlighted stretch of the line, with open or closed ends (for inequalities)."""
        a, b = self._in_range(start, "start"), self._in_range(end, "end")
        if not a < b:
            raise ValidationError("an interval needs start < end")
        for flag, what in ((open_start, "open_start"), (open_end, "open_end")):
            if not isinstance(flag, bool):
                raise ValidationError(f"{what} must be a boolean")
        tint = Color(*rgb(color, "color"))
        p, q = self.to_scene(a), self.to_scene(b)
        parts = [Line(start=p, end=q, stroke=StrokeStyle(color=tint, width=7), z_index=1)]
        for point, hollow in ((p, open_start), (q, open_end)):
            parts.append(Circle(center=point, radius=7, z_index=2,
                                fill=FillStyle(color=Color(255, 255, 255) if hollow else tint),
                                stroke=StrokeStyle(color=tint, width=2.5)))
        span = Group(children=parts, transform=fixed_pivot())
        self.group.add(span, preserve_world_transform=False)
        return self.tutorial.target(span, name=self._name(name, "interval"))

    @classmethod
    def find(cls, tutorial, name: str = "number_line") -> NumberLine:
        """Reattach to a number line saved in a lesson, to add more to it."""
        from ..adapters.drawcv import index_scene

        for obj in index_scene(tutorial.scene).values():
            data = getattr(obj, "metadata", {}).get(KIT_KEY)
            if isinstance(obj, Group) and obj.name == name and isinstance(data, dict) \
                    and data.get("kit") == "number_line":
                line = cls.__new__(cls)
                line.tutorial, line.name, line.group = tutorial, name, obj
                line.start, line.length = Point(*data["start"]), data["length"]
                line.value_range, line.step = tuple(data["value_range"]), data["step"]
                line.color, line.font_scale = INK, 0.55
                line.line = tutorial.get_target(f"{name}_line")
                line._count = sum(1 for t in tutorial.targets
                                  if t.name and t.name.startswith(f"{name}_"))
                return line
        raise ValidationError(f"No number line named {name!r} in this lesson")
