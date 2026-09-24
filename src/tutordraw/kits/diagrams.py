"""Process kits: flowcharts, timelines and cycles."""

from __future__ import annotations

import math
import re

from drawcv import (BoundingBox, Circle, Color, FillStyle, Group, Line, Path, Point, Polygon,
                    Rectangle, RoundedRectangle, StrokeStyle)

from ..adapters.drawcv import fixed_pivot
from ..errors import ValidationError
from ..validation import finite_number, rgb
from ._base import (INK, PALETTE, PAPER, Kit, _check_name, _pair, _point, arrow_head,
                    centred_lines, kit_text, wrap_lines)
from .graphs import format_number, nice_step

SHAPES = ("box", "decision", "terminal", "data")


def slug(text: str) -> str | None:
    """A target name from display text: "Condensation!" -> "condensation"."""
    value = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return value or None


def _size(value, name: str) -> tuple[float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValidationError(f"{name} must be (width, height)")
    width, height = (finite_number(v, name, minimum=0) for v in value)
    if width == 0 or height == 0:
        raise ValidationError(f"{name} must be positive")
    return width, height


def node_art(shape: str, centre: Point, width: float, height: float, text: str, *,
             fill, color, font_scale: float) -> tuple[Group, object]:
    """A shape with its text wrapped and centred inside; returns (group, shape)."""
    if shape not in SHAPES:
        raise ValidationError(f"shape must be one of {', '.join(SHAPES)}, not {shape!r}")
    left, top = centre.x - width / 2, centre.y - height / 2
    stroke = StrokeStyle(color=Color(*color), width=2)
    paint = FillStyle(color=Color(*fill))
    if shape == "box":
        body = RoundedRectangle(x=left, y=top, width=width, height=height, corner_radius=6,
                                stroke=stroke, fill=paint)
        room = width - 16
    elif shape == "terminal":
        body = RoundedRectangle(x=left, y=top, width=width, height=height,
                                corner_radius=height / 2, stroke=stroke, fill=paint)
        room = width - height * 0.6
    elif shape == "decision":
        body = Polygon(vertices=[Point(centre.x, top), Point(left + width, centre.y),
                                 Point(centre.x, top + height), Point(left, centre.y)],
                       stroke=stroke, fill=paint)
        room = width * 0.62
    else:
        skew = height * 0.35
        body = Polygon(vertices=[Point(left + skew, top), Point(left + width, top),
                                 Point(left + width - skew, top + height), Point(left, top + height)],
                       stroke=stroke, fill=paint)
        room = width - 2 * skew - 8
    lines = wrap_lines(text, font_scale, room)
    art = Group(children=[body, *centred_lines(lines, centre, font_scale, color)],
                transform=fixed_pivot())
    return art, body


class _Nodes(Kit):
    """Kits made of labelled shapes: each node is a group target plus its shape."""

    def _node(self, name: str, text: str, shape: str, centre: Point, fill) -> object:
        name = _check_name(name)
        width, height = self.node_size
        art, body = node_art(shape, centre, width, height, text,
                             fill=rgb(fill, "fill"), color=self.color, font_scale=self.font_scale)
        self._add(art)
        self._shapes[name] = (shape, centre)
        target = self._target(art, name)
        self._target(body, f"{name}_shape")
        return target

    def _edge(self, name: str, towards: Point) -> Point:
        """Where a line leaving this node toward `towards` crosses its outline."""
        shape, c = self._shapes[name]
        width, height = self.node_size
        dx, dy = towards.x - c.x, towards.y - c.y
        if dx == dy == 0:
            return c
        if shape == "decision":
            t = 1 / (abs(dx) / (width / 2) + abs(dy) / (height / 2))
        else:
            t = min(width / 2 / abs(dx) if dx else math.inf, height / 2 / abs(dy) if dy else math.inf)
        return Point(c.x + dx * t, c.y + dy * t)

    def _node_name(self, value, what: str) -> str:
        name = getattr(value, "name", value)
        if not isinstance(name, str) or name not in self._shapes:
            raise ValidationError(f"{what} must be a node of {self.name!r} (a target it returned "
                                  f"or its name); it has {', '.join(sorted(self._shapes)) or 'none'}")
        return name


# --- flowcharts ---------------------------------------------------------------


class Flowchart(_Nodes):
    """Boxes and decisions on a grid, joined by arrows that turn square corners.

    `origin` is the centre of the node at column 0, row 0; `cell` is the
    spacing between columns and rows. Nodes are placed with `at=(col, row)`,
    so an LLM lays a chart out by counting rather than measuring.
    """

    KIND = "flowchart"

    def __init__(self, tutorial, *, origin, cell=(220, 110), node_size=(170, 60),
                 name: str = "flowchart", color=INK, fill=PALETTE[0], font_scale: float = 0.5):
        self.origin = _point(origin, "origin")
        self.cell = _size(cell, "cell")
        self.node_size = _size(node_size, "node_size")
        if self.node_size[0] >= self.cell[0] or self.node_size[1] >= self.cell[1]:
            raise ValidationError("node_size must be smaller than cell, to leave room for arrows")
        self.color, self.fill = rgb(color, "color"), rgb(fill, "fill")
        self.font_scale = finite_number(font_scale, "font_scale", minimum=0)
        self._shapes: dict[str, tuple[str, Point]] = {}
        self._start(tutorial, name, {"origin": [self.origin.x, self.origin.y], "cell": list(self.cell),
                                     "node_size": list(self.node_size), "nodes": {}})

    def to_scene(self, col: float, row: float) -> Point:
        """The canvas centre of grid cell (col, row)."""
        return Point(self.origin.x + col * self.cell[0], self.origin.y + row * self.cell[1])

    def node(self, name: str, text: str, *, at, shape: str = "box", fill=None):
        """A node at grid cell `at=(col, row)`; returns its target.

        Shapes: "box" (a step), "decision" (a diamond), "terminal" (start or
        end, a pill) and "data" (input or output, a slanted box). The shape
        alone is also a target, `<name>_shape`, for `restyle(fill=...)`.
        """
        if isinstance(name, str) and name in self._shapes:
            raise ValidationError(f"{self.name!r} already has a node named {name!r}")
        col, row = (finite_number(v, "at") for v in _size_like(at))
        centre = self.to_scene(col, row)
        target = self._node(name, text, shape, centre, self.fill if fill is None else fill)
        self.settings["nodes"][name] = [shape, centre.x, centre.y]
        return target

    def link(self, source, destination, text: str | None = None, *, name: str | None = None):
        """An arrow from one node to another, drawn into the scene; returns its target.

        Nodes in one row or column join straight. Otherwise the arrow leaves
        the side facing the destination and turns once, into its top or
        bottom. An arrow back up a column (a loop) runs round the left-hand
        side. `text` ("yes", "no") sits by the start of the arrow.
        """
        a, b = self._node_name(source, "source"), self._node_name(destination, "destination")
        if a == b:
            raise ValidationError("link needs two different nodes")
        route = self._route(a, b)
        tint = self.color
        path = Path(stroke=StrokeStyle(color=Color(*tint), width=2), transform=fixed_pivot())
        path.move_to(route[0])
        for p in route[1:]:
            path.line_to(p)
        parts = [path, arrow_head(route[-1], route[-2], tint)]
        if text is not None:
            parts.append(self._tag(text, route))
        art = Group(children=parts, transform=fixed_pivot())
        self._add(art)
        return self._target(art, f"arrow_from_{a}_to_{b}" if name is None else _check_name(name))

    def _route(self, a: str, b: str) -> list[Point]:
        (_, p), (_, q) = self._shapes[a], self._shapes[b]
        width, height = self.node_size
        if abs(p.x - q.x) < 1e-6 and q.y < p.y:
            # A loop back up the same column: out of the left, up, and back in.
            # Left, because a decision's branches usually leave to the right.
            side = p.x - width / 2 - (self.cell[0] - width) / 3
            return [Point(p.x - width / 2, p.y), Point(side, p.y), Point(side, q.y),
                    Point(q.x - width / 2, q.y)]
        if abs(p.x - q.x) < 1e-6 or abs(p.y - q.y) < 1e-6:
            return [self._edge(a, q), self._edge(b, p)]
        corner = Point(q.x, p.y)
        return [self._edge(a, corner), corner, self._edge(b, corner)]

    def _tag(self, text: str, route: list[Point]):
        tag = kit_text(text, self.font_scale * 0.9, self.color)
        box = tag.get_bounds()
        a, b = route[0], route[1]
        if abs(a.y - b.y) < 1e-6:  # leaving sideways: text above the line
            x = a.x + (6 if b.x > a.x else -6 - box.width)
            tag.position = Point(x, a.y - box.height - 6)
        else:  # leaving up or down: text beside the line
            y = a.y + (6 if b.y > a.y else -6 - box.height)
            tag.position = Point(a.x + 8, y)
        # Never off the canvas: a loop from a node near the left edge would be.
        width = self.tutorial.scene.width
        x = min(max(tag.position.x, 2.0), width - box.width - 2)
        tag.position = Point(x, max(tag.position.y, 2.0))
        return tag

    @classmethod
    def find(cls, tutorial, name: str = "flowchart") -> Flowchart:
        """Reattach to a saved flowchart, to add nodes and links."""
        chart, data = cls._reattach(tutorial, name)
        chart.origin, chart.cell = Point(*data["origin"]), tuple(data["cell"])
        chart.node_size = tuple(data["node_size"])
        chart.color, chart.fill, chart.font_scale = INK, PALETTE[0], 0.5
        chart._shapes = {key: (shape, Point(x, y)) for key, (shape, x, y) in data["nodes"].items()}
        return chart


def _size_like(value):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValidationError("at must be (col, row)")
    return value


# --- timelines ----------------------------------------------------------------


class Timeline(Kit):
    """Dated events along a horizontal line, with periods as bands above it.

    `start` is the left end on the canvas and `length` its width; `span` is
    the first and last date (years, or any number). Events alternate above
    and below the line and step further out when they would collide.
    """

    KIND = "timeline"

    def __init__(self, tutorial, *, start, length: float, span, step: float | None = None,
                 name: str = "timeline", color=INK, font_scale: float = 0.5):
        self.start = _point(start, "start")
        self.length = finite_number(length, "length", minimum=0)
        if self.length == 0:
            raise ValidationError("length must be positive")
        self.span = _pair(span, "span")
        width = self.span[1] - self.span[0]
        if step is None:
            self.step = nice_step(width, target_ticks=8)
        else:
            self.step = finite_number(step, "step", minimum=0)
            if self.step == 0 or width / self.step > 200:
                raise ValidationError("step must be positive and give at most 200 ticks")
        self.color = rgb(color, "color")
        self.font_scale = finite_number(font_scale, "font_scale", minimum=0)
        self._placed: dict[str, list[BoundingBox]] = {"above": [], "below": []}
        self._events = 0
        self._start(tutorial, name, {"start": [self.start.x, self.start.y], "length": self.length,
                                     "span": list(self.span), "step": self.step, "placed": {}})
        self._draw()
        self.line = self._target(self._line, f"{name}_line")

    def to_scene(self, when: float) -> Point:
        """Where a date sits on the canvas."""
        low, high = self.span
        return Point(self.start.x + (when - low) / (high - low) * self.length, self.start.y)

    def _in_span(self, value, what: str) -> float:
        value = finite_number(value, what)
        if not self.span[0] <= value <= self.span[1]:
            raise ValidationError(f"{what} {value:g} is outside the timeline's span "
                                  f"{self.span[0]:g} to {self.span[1]:g}")
        return value

    def _draw(self) -> None:
        ink = StrokeStyle(color=Color(*self.color), width=3)
        left, right = self.start, Point(self.start.x + self.length, self.start.y)
        self._line = Line(start=Point(left.x - 12, left.y), end=Point(right.x + 12, right.y), stroke=ink)
        parts = [self._line, arrow_head(Point(right.x + 24, right.y), right, self.color)]
        low, high = self.span
        first, last = math.ceil(low / self.step - 1e-9), math.floor(high / self.step + 1e-9)
        thin = StrokeStyle(color=Color(*self.color), width=2)
        for k in range(first, last + 1):
            value = k * self.step
            p = self.to_scene(value)
            parts.append(Line(start=Point(p.x, p.y - 5), end=Point(p.x, p.y + 5), stroke=thin))
            text = kit_text(format_number(value, self.step), self.font_scale * 0.9, self.color)
            box = text.get_bounds()
            # Dates sit just under the line; below-line events start further down.
            text.position = Point(p.x - box.width / 2, p.y + 9)
            parts.append(text)
        self._add(*parts)

    def event(self, when: float, text: str, *, name: str | None = None, side: str | None = None,
              color=(200, 80, 60)):
        """A dot on the line with its text on a stem; returns the event as one target.

        `side` is "above" or "below"; by default events alternate. A stem grows
        in 36 px levels until the text clears the events already placed.
        """
        when = self._in_span(when, "when")
        if side is None:
            side = "above" if self._events % 2 == 0 else "below"
        if side not in ("above", "below"):
            raise ValidationError(f"side must be 'above' or 'below', not {side!r}")
        self._events += 1
        tint = rgb(color, "color")
        p = self.to_scene(when)
        lines = wrap_lines(text, self.font_scale, 150)
        texts = centred_lines(lines, Point(0, 0), self.font_scale, self.color)
        tall = max(t.position.y + t.get_bounds().height for t in texts) - min(t.position.y for t in texts)
        wide = max(t.get_bounds().width for t in texts)
        sign = -1 if side == "above" else 1
        base = 40  # above: clear of a row-0 period; below: clear of the dates
        for level in range(8):
            reach = base + level * 36
            centre_y = p.y + sign * (reach + tall / 2 + 4)
            box = BoundingBox(p.x - wide / 2 - 6, centre_y - tall / 2 - 3, wide + 12, tall + 6)
            if not any(_overlaps(box, other) for other in self._placed[side]):
                break
        self._placed[side].append(box)
        self.settings["placed"].setdefault(side, []).append([box.x, box.y, box.width, box.height])
        texts = centred_lines(lines, Point(p.x, centre_y), self.font_scale, self.color)
        stem_end = Point(p.x, centre_y - sign * (tall / 2 + 4))
        parts = [Line(start=p, end=stem_end, stroke=StrokeStyle(color=Color(*tint), width=2)),
                 Circle(center=p, radius=6, fill=FillStyle(color=Color(*tint)),
                        stroke=StrokeStyle(color=Color(*PAPER), width=2)),
                 *texts]
        art = Group(children=parts, transform=fixed_pivot())
        self._add(art)
        return self._target(art, self._name(name, "event"))

    def period(self, start: float, end: float, text: str, *, name: str | None = None, row: int = 0,
               color=PALETTE[2]):
        """A band spanning two dates just above the line, e.g. a war or an era.

        `row` stacks overlapping periods: 0 sits on the line, 1 above that.
        Add periods before events: events then climb clear of the bands.
        """
        a, b = self._in_span(start, "start"), self._in_span(end, "end")
        if not a < b:
            raise ValidationError("a period needs start < end")
        if isinstance(row, bool) or not isinstance(row, int) or not 0 <= row <= 5:
            raise ValidationError("row must be an integer from 0 to 5")
        p, q = self.to_scene(a), self.to_scene(b)
        height = 22
        top = p.y - 8 - height - row * (height + 4)
        band = Rectangle(position=Point(p.x, top), width=q.x - p.x, height=height, z_index=-1,
                         fill=FillStyle(color=Color(*rgb(color, "color"))),
                         stroke=StrokeStyle(color=Color(*self.color), width=1))
        caption = kit_text(text, self.font_scale * 0.85, self.color)
        box = caption.get_bounds()
        caption.position = Point((p.x + q.x) / 2 - box.width / 2, top + (height - box.height) / 2)
        # Events added later climb over the band rather than sitting on it.
        taken = BoundingBox(p.x, top, q.x - p.x, height)
        self._placed["above"].append(taken)
        self.settings["placed"].setdefault("above", []).append([taken.x, taken.y, taken.width, taken.height])
        art = Group(children=[band, caption], transform=fixed_pivot())
        self._add(art)
        return self._target(art, self._name(name, "period"))

    @classmethod
    def find(cls, tutorial, name: str = "timeline") -> Timeline:
        """Reattach to a saved timeline, to add events and periods."""
        line, data = cls._reattach(tutorial, name)
        line.start, line.length = Point(*data["start"]), data["length"]
        line.span, line.step = tuple(data["span"]), data["step"]
        line.color, line.font_scale = INK, 0.5
        line._placed = {side: [BoundingBox(*box) for box in data["placed"].get(side, [])]
                        for side in ("above", "below")}
        line._events = sum(1 for t in tutorial.targets if t.name and t.name.startswith(f"{name}_event"))
        line.line = tutorial.get_target(f"{name}_line")
        return line


def _overlaps(a: BoundingBox, b: BoundingBox) -> bool:
    return a.x < b.x + b.width and b.x < a.x + a.width and a.y < b.y + b.height and b.y < a.y + a.height


# --- cycles -------------------------------------------------------------------


class Cycle(_Nodes):
    """Stages around a circle, each joined to the next by a curved arrow.

    The water cycle, the cell cycle, the carbon cycle, a product loop. The
    first stage sits at the top and the rest follow clockwise. Each stage is
    a target named from its text ("Evaporation" -> `evaporation`) unless you
    give `(name, text)` pairs. `arrows[0]` joins stage 1 to stage 2 and is
    named `arrow_from_<stage1>_to_<stage2>`; the last closes the loop.
    """

    KIND = "cycle"

    def __init__(self, tutorial, *, center, radius: float, stages, name: str = "cycle",
                 node_size=(150, 54), clockwise: bool = True, color=INK, fills=PALETTE,
                 font_scale: float = 0.5):
        self.center = _point(center, "center")
        self.radius = finite_number(radius, "radius", minimum=0)
        self.node_size = _size(node_size, "node_size")
        if not isinstance(clockwise, bool):
            raise ValidationError("clockwise must be a boolean")
        self.color = rgb(color, "color")
        self.font_scale = finite_number(font_scale, "font_scale", minimum=0)
        if not isinstance(stages, (list, tuple)) or not 2 <= len(stages) <= 12:
            raise ValidationError("stages must be a list of 2 to 12 stage texts or (name, text) pairs")
        if not isinstance(fills, (list, tuple)) or not fills:
            raise ValidationError("fills must be a non-empty list of colours")
        pairs = []
        for i, stage in enumerate(stages, start=1):
            if isinstance(stage, str):
                pairs.append((slug(stage) or f"{name}_stage{i}", stage))
            elif isinstance(stage, (list, tuple)) and len(stage) == 2:
                pairs.append((_check_name(stage[0], "stage name"), stage[1]))
            else:
                raise ValidationError("each stage must be a text or a (name, text) pair")
        names = [n for n, _ in pairs]
        if len(set(names)) != len(names):
            raise ValidationError("stage names must be different; pass (name, text) pairs")
        width, height = self.node_size
        # Room between neighbours along the circle, or the arrows vanish.
        chord = 2 * self.radius * math.sin(math.pi / len(pairs))
        if chord < math.hypot(width, height) * 0.75:
            raise ValidationError(f"radius {self.radius:g} is too small for {len(pairs)} stages of "
                                  f"node_size {width:g}x{height:g}; try radius "
                                  f"{math.ceil(math.hypot(width, height) * 0.75 / 2 / math.sin(math.pi / len(pairs)) + 20)}")
        self._shapes: dict[str, tuple[str, Point]] = {}
        self._start(tutorial, name, {"center": [self.center.x, self.center.y], "radius": self.radius,
                                     "stages": names})
        turn = 1 if clockwise else -1
        angles = [-math.pi / 2 + turn * 2 * math.pi * i / len(pairs) for i in range(len(pairs))]
        self.stages = tuple(
            self._node(stage_name, text, "box", self._at(angle), fills[i % len(fills)])
            for i, ((stage_name, text), angle) in enumerate(zip(pairs, angles)))
        arrows = []
        for i, angle in enumerate(angles):
            following = angles[(i + 1) % len(angles)]
            if following * turn < angle * turn:
                following += turn * 2 * math.pi
            arrows.append(self._arc(names[i], names[(i + 1) % len(names)], angle, following))
        self.arrows = tuple(arrows)

    def _at(self, angle: float) -> Point:
        return Point(self.center.x + self.radius * math.cos(angle),
                     self.center.y + self.radius * math.sin(angle))

    def _arc(self, a: str, b: str, start: float, end: float):
        # Walk the circle and keep the stretch outside both nodes, less a margin.
        count = 64
        points = [self._at(start + (end - start) * k / count) for k in range(count + 1)]
        width, height = self.node_size
        (_, p), (_, q) = self._shapes[a], self._shapes[b]

        def clear(pt: Point) -> bool:
            return all(abs(pt.x - c.x) > width / 2 + 8 or abs(pt.y - c.y) > height / 2 + 8 for c in (p, q))

        points = [pt for pt in points if clear(pt)]
        if len(points) < 2:
            raise ValidationError("The stages overlap; use a larger radius or smaller node_size")
        path = Path(stroke=StrokeStyle(color=Color(*self.color), width=2.5), transform=fixed_pivot())
        path.move_to(points[0])
        for pt in points[1:]:
            path.line_to(pt)
        head = arrow_head(points[-1], points[-3] if len(points) > 2 else points[0], self.color)
        art = Group(children=[path, head], transform=fixed_pivot())
        self._add(art)
        return self._target(art, f"arrow_from_{a}_to_{b}")

    def stage(self, key):
        """A stage by its position (1 is the first) or its name."""
        if isinstance(key, int) and not isinstance(key, bool):
            if not 1 <= key <= len(self.stages):
                raise ValidationError(f"stage numbers run from 1 to {len(self.stages)}")
            return self.stages[key - 1]
        for target in self.stages:
            if target.name == key:
                return target
        raise ValidationError(f"{self.name!r} has no stage {key!r}; it has "
                              f"{', '.join(t.name for t in self.stages)}")

    @classmethod
    def find(cls, tutorial, name: str = "cycle") -> Cycle:
        """Reattach to a saved cycle, to reach its stages and arrows by name."""
        cycle, data = cls._reattach(tutorial, name)
        cycle.center, cycle.radius = Point(*data["center"]), data["radius"]
        cycle.stages = tuple(tutorial.get_target(n) for n in data["stages"])
        names = data["stages"]
        cycle.arrows = tuple(tutorial.get_target(f"arrow_from_{a}_to_{b}")
                             for a, b in zip(names, names[1:] + names[:1]))
        return cycle
