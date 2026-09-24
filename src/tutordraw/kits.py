"""Teaching kits: ready-made diagrams built from ordinary DrawCV objects.

A kit works out geometry a model gets wrong by hand (tick spacing, mapping
maths coordinates onto the canvas, sampling a function) and adds plain DrawCV
shapes to the tutorial's scene. DrawCV draws them, lesson files save them, and
the parts come back as named targets, ready to label, highlight, measure or
narrate. Nothing here renders anything.
"""

from __future__ import annotations

import math
from typing import Callable

from drawcv import (Arrow, BoundingBox, Circle, Color, FillStyle, Group, Line, Path, Point,
                    StrokeStyle, Text)

from .adapters.drawcv import fixed_pivot
from .errors import ValidationError
from .validation import finite_number, rgb

INK = (60, 70, 90)
CURVE = (40, 100, 200)
GRID = (226, 231, 238)
KIT_KEY = "tutordraw"


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


def _pair(value, name: str) -> tuple[float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValidationError(f"{name} must be (low, high)")
    low, high = (finite_number(v, name) for v in value)
    if not low < high:
        raise ValidationError(f"{name} must have low < high")
    return low, high


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
            for x in xs:
                p = self.to_scene(x, 0)
                parts.append(Line(start=Point(p.x, b.top), end=Point(p.x, b.bottom), stroke=faint))
            for y in ys:
                p = self.to_scene(0, y)
                parts.append(Line(start=Point(b.left, p.y), end=Point(b.right, p.y), stroke=faint))
        start, end = self.to_scene(self.x_range[0], oy), self.to_scene(self.x_range[1], oy)
        self._x_axis = Arrow(start=start, end=Point(end.x + 14, end.y), stroke=ink,
                             fill=FillStyle(color=Color(*self.color)), head_length=10, head_width=8)
        start, end = self.to_scene(ox, self.y_range[0]), self.to_scene(ox, self.y_range[1])
        self._y_axis = Arrow(start=start, end=Point(end.x, end.y - 14), stroke=ink,
                             fill=FillStyle(color=Color(*self.color)), head_length=10, head_width=8)
        parts += [self._x_axis, self._y_axis]
        crossing = (self.x_range[0] < 0 < self.x_range[1]) and (self.y_range[0] < 0 < self.y_range[1])
        for x in xs:
            if crossing and abs(x) < self.x_step / 2:
                continue  # the origin is labelled once, below
            p = self.to_scene(x, oy)
            parts.append(Line(start=Point(p.x, p.y - 4), end=Point(p.x, p.y + 4), stroke=thin))
            parts.append(self._text(format_number(x, self.x_step), p, "below"))
        for y in ys:
            if crossing and abs(y) < self.y_step / 2:
                continue
            p = self.to_scene(ox, y)
            parts.append(Line(start=Point(p.x - 4, p.y), end=Point(p.x + 4, p.y), stroke=thin))
            parts.append(self._text(format_number(y, self.y_step), p, "left"))
        if crossing:
            parts.append(self._text("0", self.to_scene(0, 0), "below-left"))
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
        if isinstance(samples, bool) or not isinstance(samples, int) or not 2 <= samples <= 5000:
            raise ValidationError("samples must be an integer from 2 to 5000")
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

    # --- after reloading a lesson -------------------------------------------

    @classmethod
    def find(cls, tutorial, name: str = "axes") -> Axes:
        """Reattach to axes saved in a lesson, to plot more into them."""
        from .adapters.drawcv import index_scene

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
