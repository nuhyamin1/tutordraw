"""Small authoring model for independent tutorial steps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from .errors import ValidationError
from .validation import finite_number, rgb

if TYPE_CHECKING:
    from drawcv import Drawable
    from .tutorial import Tutorial

Anchor = Literal["left", "right", "top", "bottom", "center"]


@dataclass(frozen=True, eq=False)
class Label:
    """Immutable label definition. Create with Target.label()."""

    target: Target
    text: str
    anchor: Anchor
    leader: bool
    gap: float
    offset: tuple[float, float]
    font_scale: float
    padding: float
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True, eq=False)
class Callout(Label):
    """Step-owned explanatory panel. max_width measures the text area."""

    max_width: float = 260
    line_spacing: float = 1.35


@dataclass(frozen=True)
class Highlight:
    target: Target
    padding: float
    color: tuple[int, int, int]
    width: float


@dataclass(frozen=True, eq=False)
class Target:
    """A reference to an existing drawable. Create with Tutorial.target()."""

    _tutorial: Tutorial = field(repr=False)
    drawable_id: str
    name: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def drawable(self) -> Drawable:
        """Resolve the current source object, including a nested group child."""
        from .adapters.drawcv import index_scene

        obj = index_scene(self._tutorial.scene).get(self.drawable_id)
        if obj is None:
            raise ValidationError(f"Missing target {self.name or self.id!r}: {self.drawable_id}")
        return obj

    def label(
        self, text: str, *, anchor: Anchor = "right", leader: bool = True,
        gap: float | None = None, offset: tuple[float, float] = (0, 0),
        font_scale: float | None = None, padding: float | None = None,
    ) -> Label:
        """Define a printable-ASCII, single-line label; show it via Step.show()."""
        label = make_annotation(self, text, anchor=anchor, leader=leader,
                                gap=gap, offset=offset, font_scale=font_scale, padding=padding)
        self._tutorial._labels[label.id] = label
        return label


def make_annotation(target: Target, text: str, *, anchor: Anchor = "right",
                    leader: bool = True, gap: float | None = None,
                    offset: tuple[float, float] = (0, 0), font_scale: float | None = None,
                    padding: float | None = None, callout: bool = False,
                    max_width: float | None = None, line_spacing: float | None = None) -> Label:
    theme = target._tutorial.theme
    if not isinstance(text, str) or not text.strip():
        raise ValidationError("Annotation text must be a nonempty string")
    if any((ord(c) < 32 or ord(c) > 126) and not (callout and c == "\n") for c in text):
        raise ValidationError("Annotations support printable ASCII; only callouts allow newlines")
    if anchor not in ("left", "right", "top", "bottom", "center"):
        raise ValidationError(f"Unsupported anchor: {anchor!r}")
    if not isinstance(leader, bool):
        raise ValidationError("leader must be a boolean")
    if not isinstance(offset, (tuple, list)) or len(offset) != 2:
        raise ValidationError("offset must contain two finite numbers")
    xy = tuple(finite_number(v, "offset") for v in offset)
    scale = finite_number(theme.font_scale if font_scale is None else font_scale, "font_scale")
    if not 0 < scale <= 10:
        raise ValidationError("font_scale must be > 0 and <= 10")
    options = dict(target=target, text=text, anchor=anchor, leader=leader,
                   gap=finite_number(theme.gap if gap is None else gap, "gap", minimum=0),
                   offset=xy, font_scale=scale,
                   padding=finite_number(theme.padding if padding is None else padding, "padding", minimum=0))
    if not callout:
        return Label(**options)
    width = finite_number(theme.callout_width if max_width is None else max_width, "max_width", minimum=0)
    if width == 0:
        raise ValidationError("max_width must be positive")
    spacing = finite_number(theme.line_spacing if line_spacing is None else line_spacing, "line_spacing", minimum=1)
    return Callout(**options, max_width=width, line_spacing=spacing)


class Step:
    """An independent collection of visible labels. Create with Tutorial.step()."""

    def __init__(self, tutorial: Tutorial, title: str):
        self._tutorial = tutorial
        self.title = title
        self._labels: list[Label] = []
        self._callouts: list[Callout] = []
        self._highlights: dict[str, Highlight] = {}
        self._focus: tuple[Target, ...] = ()
        self._dim_opacity: float | None = None
        self._id = str(uuid4())

    @property
    def id(self) -> str:
        """Stable identity retained by lesson save/load."""
        return self._id

    @property
    def labels(self) -> tuple[Label, ...]:
        return tuple(self._labels)

    def show(self, *labels: Label) -> Step:
        """Show registered labels, without inheriting any other step's state."""
        for label in labels:
            if not isinstance(label, Label) or self._tutorial._labels.get(label.id) is not label:
                raise ValidationError("Label must belong to this tutorial")
        for label in labels:
            if label not in self._labels:
                self._labels.append(label)
        return self

    @property
    def callouts(self) -> tuple[Callout, ...]:
        return tuple(self._callouts)

    @property
    def highlights(self) -> tuple[Highlight, ...]:
        return tuple(self._highlights.values())

    def _check_target(self, target: Target) -> None:
        if not isinstance(target, Target) or self._tutorial._targets.get(target.drawable_id) is not target:
            raise ValidationError("Target must belong to this tutorial")

    def explain(self, target: Target, text: str, *, anchor: Anchor = "right",
                leader: bool = True, gap: float | None = None,
                offset: tuple[float, float] = (0, 0), font_scale: float | None = None,
                padding: float | None = None, max_width: float | None = None,
                line_spacing: float | None = None) -> Callout:
        """Add a wrapped explanation only to this step; return its definition."""
        self._check_target(target)
        annotation = make_annotation(target, text, anchor=anchor, leader=leader,
                                     gap=gap, offset=offset, font_scale=font_scale,
                                     padding=padding, callout=True, max_width=max_width,
                                     line_spacing=line_spacing)
        self._callouts.append(annotation)
        return annotation

    def highlight(self, target: Target, *, padding: float | None = None,
                  color: tuple[int, int, int] | None = None, width: float | None = None) -> Step:
        """Set a rectangular outline for this target in this step."""
        self._check_target(target)
        theme = self._tutorial.theme
        pad = finite_number(theme.highlight_padding if padding is None else padding, "padding", minimum=0)
        stroke = finite_number(theme.highlight_width if width is None else width, "width", minimum=0)
        if stroke == 0:
            raise ValidationError("width must be positive")
        tint = rgb(theme.highlight_color if color is None else color, "color")
        self._highlights[target.id] = Highlight(target, pad, tint, stroke)
        return self

    def dim_others(self, *targets: Target, opacity: float | None = None) -> Step:
        """Replace the focus set; opacity is a multiplier for unrelated branches."""
        if not targets:
            raise ValidationError("dim_others requires at least one target")
        for target in targets:
            self._check_target(target)
        factor = finite_number(self._tutorial.theme.dim_opacity if opacity is None else opacity, "opacity")
        if not 0 <= factor <= 1:
            raise ValidationError("opacity must be between 0 and 1")
        self._focus = tuple(dict.fromkeys(targets))
        self._dim_opacity = factor
        return self
