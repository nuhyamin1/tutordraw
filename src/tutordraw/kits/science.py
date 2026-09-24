"""Science kits: force diagrams and labelled cross-sections."""

from __future__ import annotations

import math

from drawcv import Arrow, Circle, Color, FillStyle, Group, Point, Rectangle, StrokeStyle

from ..adapters.drawcv import fixed_pivot
from ..errors import ValidationError
from ..validation import finite_number, rgb
from ._base import INK, PALETTE, Kit, _check_name, _point, centred_lines, kit_text

DIRECTIONS = {"right": 0.0, "up-right": 45.0, "up": 90.0, "up-left": 135.0, "left": 180.0,
              "down-left": 225.0, "down": 270.0, "down-right": 315.0}
FORCE = (200, 60, 50)
NET = (40, 120, 70)
RING_LABEL_SPACING = 58  # px between ring labels: a default panel plus collision clearance


def _degrees(direction) -> float:
    if isinstance(direction, str):
        if direction not in DIRECTIONS:
            raise ValidationError(f"direction must be degrees or one of {', '.join(DIRECTIONS)}, "
                                  f"not {direction!r}")
        return DIRECTIONS[direction]
    return finite_number(direction, "direction") % 360


# --- force diagrams -----------------------------------------------------------


class ForceDiagram(Kit):
    """A body with force arrows drawn out from its edge, lengths to scale.

    Directions are degrees anticlockwise from the right, as in maths (90 is
    up), or words: "up", "down-left" and so on. `scale` is pixels per unit
    of force, so 10 N at scale 6 is a 60 px arrow; pick units once and the
    picture compares forces honestly. `net()` adds the resultant.
    """

    KIND = "force_diagram"

    def __init__(self, tutorial, *, center, body: str = "block", size: float = 80,
                 scale: float = 6, text: str | None = None, name: str = "body", fill=PALETTE[0],
                 color=INK, font_scale: float = 0.5):
        self.center = _point(center, "center")
        self.size = finite_number(size, "size", minimum=0)
        self.scale = finite_number(scale, "scale", minimum=0)
        if self.size == 0 or self.scale == 0:
            raise ValidationError("size and scale must be positive")
        if body not in ("block", "ball"):
            raise ValidationError(f"body must be 'block' or 'ball', not {body!r}")
        self.color = rgb(color, "color")
        self.font_scale = finite_number(font_scale, "font_scale", minimum=0)
        self._forces: dict[str, tuple[float, float]] = {}
        self.shape = body
        self._start(tutorial, name, {"center": [self.center.x, self.center.y], "size": self.size,
                                     "body": body, "scale": self.scale, "forces": {}})
        c, half = self.center, self.size / 2
        stroke = StrokeStyle(color=Color(*self.color), width=2)
        paint = FillStyle(color=Color(*rgb(fill, "fill")))
        shape = (Rectangle(position=Point(c.x - half, c.y - half), width=self.size, height=self.size,
                           stroke=stroke, fill=paint) if body == "block" else
                 Circle(center=c, radius=half, stroke=stroke, fill=paint))
        parts = [shape]
        if text is not None:
            parts += centred_lines([text], c, self.font_scale, self.color)
        # The drawing's own group is the kit; the body is a group inside it so
        # its text dims and moves with it.
        self._body = Group(children=parts, transform=fixed_pivot())
        self._add(self._body)
        self.body = self._target(self._body, name)

    def _vector(self, degrees: float, magnitude: float) -> tuple[float, float]:
        radians = math.radians(degrees)
        return magnitude * math.cos(radians), magnitude * math.sin(radians)

    def _arrow(self, fx: float, fy: float, text: str | None, color, width: float = 4,
               dashed: bool = False) -> Group:
        length = math.hypot(fx, fy) * self.scale
        if length < 12:
            raise ValidationError(f"That force draws {length:.0f} px long, too short to see; "
                                  "raise scale or the magnitude")
        if length > 2000:
            raise ValidationError("That force draws over 2000 px long; lower scale")
        # Start on the body's outline, so arrows never hide what is written on it.
        ux, uy = fx * self.scale / length, -fy * self.scale / length  # canvas y points down
        half = self.size / 2
        reach = half if self.shape == "ball" else half / max(abs(ux), abs(uy))
        c = Point(self.center.x + ux * reach, self.center.y + uy * reach)
        tip = Point(c.x + ux * length, c.y + uy * length)
        tint = Color(*rgb(color, "color"))
        stroke = StrokeStyle(color=tint, width=width, dash_array=(7.0, 5.0) if dashed else ())
        parts = [Arrow(start=c, end=tip, stroke=stroke, fill=FillStyle(color=tint),
                       head_length=14, head_width=12, z_index=3)]
        if text is not None:
            caption = kit_text(text, self.font_scale, tuple(rgb(color, "color")))
            box = caption.get_bounds()
            # Beyond the tip, pushed out by half the text's extent along the line.
            reach = 10 + abs(ux) * box.width / 2 + abs(uy) * box.height / 2
            caption.position = Point(tip.x + ux * reach - box.width / 2,
                                     tip.y + uy * reach - box.height / 2)
            parts.append(caption)
        return Group(children=parts, transform=fixed_pivot())

    def force(self, name: str, direction, magnitude: float, text: str | None = None, *,
              color=FORCE):
        """A force arrow out from the body's edge; returns it as a target.

        `text` ("weight 20 N") sits beyond the arrow's tip. Hide a force until
        its step with `restyle(target, visible=False)`, as for any drawing.
        """
        name = _check_name(name)
        if name in self._forces:
            raise ValidationError(f"{self.name!r} already has a force named {name!r}")
        magnitude = finite_number(magnitude, "magnitude", minimum=0)
        fx, fy = self._vector(_degrees(direction), magnitude)
        art = self._arrow(fx, fy, text, color)
        self._add(art)
        self._forces[name] = (fx, fy)
        self.settings["forces"][name] = [fx, fy]
        return self._target(art, name)

    def components(self, force, *, name: str | None = None, color=(120, 120, 140)):
        """The force's horizontal and vertical parts as dashed arrows, one target."""
        key = getattr(force, "name", force)
        if key not in self._forces:
            raise ValidationError(f"{self.name!r} has no force {key!r}")
        fx, fy = self._forces[key]
        parts = [self._arrow(x, y, None, color, width=2, dashed=True)
                 for x, y in ((fx, 0.0), (0.0, fy)) if abs(x) + abs(y) > 1e-9
                 and math.hypot(x, y) * self.scale >= 12]
        if not parts:
            raise ValidationError(f"{key!r} is too short to split into components")
        art = Group(children=parts, transform=fixed_pivot())
        self._add(art)
        return self._target(art, f"{key}_components" if name is None else _check_name(name))

    @property
    def resultant(self) -> tuple[float, float]:
        """The sum of the forces so far, as (x, y) with y up."""
        return (sum(f[0] for f in self._forces.values()), sum(f[1] for f in self._forces.values()))

    def net(self, text: str | None = None, *, name: str = "net_force", color=NET):
        """The resultant of every force added so far, as its own arrow.

        Balanced forces have no arrow to draw, so this raises; say "the
        forces balance" in the narration instead.
        """
        fx, fy = self.resultant
        if math.hypot(fx, fy) * self.scale < 12:
            raise ValidationError("The forces balance (the net force is about zero), so there is "
                                  "no net arrow to draw; say so in the narration instead")
        art = self._arrow(fx, fy, text, color)
        self._add(art)
        return self._target(art, _check_name(name))

    @classmethod
    def find(cls, tutorial, name: str = "body") -> ForceDiagram:
        """Reattach to a saved force diagram, to add forces or the net force."""
        diagram, data = cls._reattach(tutorial, f"{name}_diagram")
        diagram.name = name
        diagram.center, diagram.size, diagram.scale = Point(*data["center"]), data["size"], data["scale"]
        diagram.shape = data["body"]
        diagram.color, diagram.font_scale = INK, 0.5
        diagram._forces = {key: tuple(value) for key, value in data["forces"].items()}
        diagram.body = tutorial.get_target(name)
        return diagram

    def _start(self, tutorial, name, settings):
        # The body takes the kit's name as its target, so the group needs another.
        super()._start(tutorial, name, settings)
        self.group.name = f"{name}_diagram"


# --- cross-sections -----------------------------------------------------------


class CrossSection(Kit):
    """Layers cut open: bands stacked top to bottom, or rings from the outside in.

    Earth's layers, soil horizons, a leaf, skin, the atmosphere, a tooth.
    `layers` are `(name, text)` or `(name, text, thickness)`, outermost or
    topmost first; thickness is relative (default 1). `labels()` gives each
    layer a label, lined up in one column beside the drawing.
    """

    KIND = "cross_section"

    def __init__(self, tutorial, *, box, layers, shape: str = "bands", name: str = "section",
                 fills=PALETTE, color=INK):
        if not isinstance(box, (tuple, list)) or len(box) != 4:
            raise ValidationError("box must be (left, top, width, height)")
        left, top, width, height = (finite_number(v, "box") for v in box)
        if width <= 0 or height <= 0:
            raise ValidationError("box width and height must be positive")
        if shape not in ("bands", "rings"):
            raise ValidationError(f"shape must be 'bands' or 'rings', not {shape!r}")
        if not isinstance(layers, (list, tuple)) or not 1 <= len(layers) <= 12:
            raise ValidationError("layers must be a list of 1 to 12 (name, text[, thickness]) entries")
        if not isinstance(fills, (list, tuple)) or not fills:
            raise ValidationError("fills must be a non-empty list of colours")
        parsed = []
        for entry in layers:
            if not isinstance(entry, (list, tuple)) or len(entry) not in (2, 3):
                raise ValidationError("each layer must be (name, text) or (name, text, thickness)")
            thickness = finite_number(entry[2], "thickness", minimum=0) if len(entry) == 3 else 1.0
            if thickness == 0:
                raise ValidationError("thickness must be positive")
            if not isinstance(entry[1], str) or not entry[1].strip():
                raise ValidationError("each layer needs its text, e.g. ('crust', 'Crust')")
            parsed.append((_check_name(entry[0], "layer name"), entry[1], thickness))
        names = [p[0] for p in parsed]
        if len(set(names)) != len(names):
            raise ValidationError("layer names must be different")
        self.box, self.shape, self.color = (left, top, width, height), shape, rgb(color, "color")
        self._start(tutorial, name, {"box": [left, top, width, height], "shape": shape,
                                     "layers": [[n, t] for n, t, _ in parsed], "mids": {}})
        total = sum(p[2] for p in parsed)
        stroke = StrokeStyle(color=Color(*self.color), width=1.5)
        targets = []
        if shape == "bands":
            y = top
            for i, (layer, text, thickness) in enumerate(parsed):
                h = height * thickness / total
                band = Rectangle(position=Point(left, y), width=width, height=h, stroke=stroke,
                                 fill=FillStyle(color=Color(*rgb(fills[i % len(fills)], "fills"))))
                self._add(band)
                targets.append(self._target(band, layer))
                y += h
        else:
            cx, cy = left + width / 2, top + height / 2
            outer = min(width, height) / 2
            r = outer
            for i, (layer, text, thickness) in enumerate(parsed):
                band = outer * thickness / total
                ring = Circle(center=Point(cx, cy), radius=r, stroke=stroke,
                              fill=FillStyle(color=Color(*rgb(fills[i % len(fills)], "fills"))))
                self._add(ring)
                targets.append(self._target(ring, layer))
                # Halfway through the ring; the innermost disc, halfway out.
                self.settings["mids"][layer] = r - band / 2 if i < len(parsed) - 1 else r / 2
                r -= band
        self.layers = tuple(targets)
        self._texts = {layer: text for layer, text, _ in parsed}

    def _ring_anchor(self, layer: str, side: str):
        """An invisible target inside a ring, "<layer>_layer", made on first use.

        Every ring's bounds are a whole disc, so a leader aimed at the target
        would end on the rim they all share. The anchor sits halfway through
        the ring on a line leaning up toward the labels' side, and is named so
        descriptions read "the mantle layer is labelled".
        """
        name = f"{layer}_layer"
        try:
            return self.tutorial.get_target(name)
        except ValidationError:
            left, top, width, height = self.box
            angle = math.radians(-35 if side == "right" else -145)
            mid = self.settings["mids"][layer]
            point = Point(left + width / 2 + math.cos(angle) * mid, top + height / 2 + math.sin(angle) * mid)
            dot = Circle(center=point, radius=0.5, opacity=0.001, fill=FillStyle(color=Color(*self.color)))
            self._add(dot)
            return self._target(dot, name)

    def layer(self, name: str):
        """A layer's target by name."""
        for target in self.layers:
            if target.name == name:
                return target
        raise ValidationError(f"{self.name!r} has no layer {name!r}; it has "
                              f"{', '.join(t.name for t in self.layers)}")

    def labels(self, *, side: str = "right", gap: float = 36) -> list:
        """A label for every layer, lined up in a column on `side` ("left" or "right").

        A band's leader ends on its edge. A ring's points into the ring itself,
        not at the rim they share, and ring labels are spaced evenly down the
        column; ring anchors lean toward the side of the first call. Show them
        together (`step.show(*section.labels())`) or one per step.
        """
        if side not in ("left", "right"):
            raise ValidationError(f"side must be 'left' or 'right', not {side!r}")
        gap = finite_number(gap, "gap", minimum=0)
        left, _, width, _ = self.box
        edge = left + width if side == "right" else left
        if self.shape == "bands":
            return [layer.label(self._texts[layer.name], anchor=side, gap=gap) for layer in self.layers]
        result, first = [], None
        for i, layer in enumerate(self.layers):
            anchor = self._ring_anchor(layer.name, side)
            centre = anchor.drawable.get_bounds().center
            first = centre.y if first is None else first
            reach = abs(edge - centre.x) + gap
            result.append(anchor.label(self._texts[layer.name], anchor=side, gap=reach,
                                       offset=(0, first + i * RING_LABEL_SPACING - centre.y)))
        return result

    @classmethod
    def find(cls, tutorial, name: str = "section") -> CrossSection:
        """Reattach to a saved cross-section, to label its layers."""
        section, data = cls._reattach(tutorial, name)
        section.box, section.shape, section.color = tuple(data["box"]), data["shape"], INK
        section.layers = tuple(tutorial.get_target(n) for n, _ in data["layers"])
        section._texts = {n: text for n, text in data["layers"]}
        return section
