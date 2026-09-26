"""What every kit shares: colours, naming, text, and reattaching after a load."""

from __future__ import annotations

import math

from drawcv import Color, FillStyle, Group, Point, Polygon, Text

from ..adapters.drawcv import fixed_pivot, index_scene
from ..errors import ValidationError
from ..text import validate_annotation_text
from ..validation import finite_number

INK = (60, 70, 90)
CURVE = (40, 100, 200)
GRID = (226, 231, 238)
# Tags a kit's grid lines, which labels should keep off like other artwork though no one registers them.
GRID_TAG = "td-grid"
PAPER = (255, 255, 255)
KIT_KEY = "tutordraw"
# Fills for kits that colour their parts: distinct, light enough for dark text.
PALETTE = ((214, 234, 248), (213, 245, 227), (252, 243, 207), (250, 219, 216),
           (232, 218, 239), (209, 242, 235), (253, 235, 208), (229, 232, 232))


def _pair(value, name: str) -> tuple[float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValidationError(f"{name} must be (low, high)")
    low, high = (finite_number(v, name) for v in value)
    if not low < high:
        raise ValidationError(f"{name} must have low < high")
    return low, high


def _point(value, name: str) -> Point:
    if isinstance(value, Point):
        return Point(finite_number(value.x, name), finite_number(value.y, name))
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValidationError(f"{name} must be (x, y)")
    return Point(*(finite_number(v, name) for v in value))


def _check_name(name, what: str = "name") -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValidationError(f"{what} must be a non-empty string")
    return name


def _check_bool(value, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be a boolean")
    return value


def kit_text(content, font_scale: float, color, *, what: str = "text") -> Text:
    """One line of drawing text, validated like annotation text.

    Kit text is part of the scene, drawn by DrawCV's built-in renderer, so it
    takes Latin, Greek, Cyrillic, CJK and symbols but not Thai or Arabic,
    which need the font engine. Label kit parts with annotations for those.
    """
    if not isinstance(content, str) or not content.strip():
        raise ValidationError(f"{what} must be a non-empty string")
    content = validate_annotation_text(content, allow_newlines=False)
    return Text(text=content, position=Point(0, 0), font_scale=font_scale, thickness=1,
                color=Color(*color))


def centred_lines(lines: list[str], centre: Point, font_scale: float, color,
                  spacing: float = 1.25) -> list[Text]:
    """Texts for several lines, centred as a block on a point."""
    texts = [kit_text(line, font_scale, color) for line in lines]
    height = max(t.get_bounds().height for t in texts) * spacing
    top = centre.y - height * len(texts) / 2
    for i, text in enumerate(texts):
        box = text.get_bounds()
        text.position = Point(centre.x - box.width / 2, top + i * height + (height - box.height) / 2)
    return texts


def wrap_lines(content, font_scale: float, max_width: float, *, what: str = "text") -> list[str]:
    """Split text into lines no wider than `max_width`; "\\n" forces a break."""
    if not isinstance(content, str) or not content.strip():
        raise ValidationError(f"{what} must be a non-empty string")
    lines = []
    for paragraph in content.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if not current or kit_text(candidate, font_scale, INK).get_bounds().width <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def arrow_head(tip: Point, towards: Point, color, length: float = 11, width: float = 9) -> Polygon:
    """A filled triangle at `tip`, pointing away from `towards`."""
    dx, dy = tip.x - towards.x, tip.y - towards.y
    size = math.hypot(dx, dy) or 1.0
    ux, uy = dx / size, dy / size
    base = Point(tip.x - ux * length, tip.y - uy * length)
    return Polygon(vertices=[tip, Point(base.x - uy * width / 2, base.y + ux * width / 2),
                             Point(base.x + uy * width / 2, base.y - ux * width / 2)],
                   fill=FillStyle(color=Color(*color)))


class Kit:
    """Shared plumbing: one DrawCV group in the scene, automatic part names."""

    KIND = ""

    def _start(self, tutorial, name: str, settings: dict) -> None:
        self.tutorial = tutorial
        self.name = _check_name(name)
        self._count = 0
        # An explicit pivot: with the default (the group's own centre) DrawCV
        # recomputes the whole group's bounds every time a child is mapped to
        # world space, which made one render take seconds.
        self.group = Group(children=[], name=name, transform=fixed_pivot())
        self.group.metadata = {KIT_KEY: {"kit": self.KIND, **settings}}
        # In the scene from the start, so parts can become targets as they are added.
        tutorial.scene.add(self.group)

    def _add(self, *parts) -> None:
        for part in parts:
            self.group.add(part, preserve_world_transform=False)

    def _name(self, name: str | None, kind: str) -> str:
        if name is None:
            self._count += 1
            return f"{self.name}_{kind}{self._count}"
        return _check_name(name)

    def _target(self, drawable, name: str):
        return self.tutorial.target(drawable, name=name)

    @property
    def settings(self) -> dict:
        return self.group.metadata[KIT_KEY]

    @classmethod
    def _reattach(cls, tutorial, name: str):
        """The saved group and its settings, as a bare instance to finish off."""
        for obj in index_scene(tutorial.scene).values():
            data = getattr(obj, "metadata", {}).get(KIT_KEY)
            if isinstance(obj, Group) and obj.name == name and isinstance(data, dict) \
                    and data.get("kit") == cls.KIND:
                kit = cls.__new__(cls)
                kit.tutorial, kit.name, kit.group = tutorial, name, obj
                kit._count = sum(1 for t in tutorial.targets
                                 if t.name and t.name.startswith(f"{name}_"))
                return kit, data
        what = cls.KIND.replace("_", " ")
        raise ValidationError(f"No {what} named {name!r} in this lesson")
