"""Small authoring model for independent tutorial steps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from .errors import ValidationError
from .text import validate_annotation_text
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
    # False draws the text and leader with no panel behind them. The panel is
    # still measured, so collision avoidance keeps bare text clear of the rest.
    box: bool
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


@dataclass(frozen=True)
class Restyle:
    """How one step changes a target's artwork. Create with Step.restyle()."""

    target: Target
    move: tuple[float, float] | None
    fill: tuple[int, int, int] | None
    opacity: float | None
    visible: bool | None


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
        box: bool = True,
    ) -> Label:
        """Define a single-line label; show it via Step.show(). See docs/TEXT.md."""
        label = make_annotation(self, text, anchor=anchor, leader=leader,
                                gap=gap, offset=offset, font_scale=font_scale,
                                padding=padding, box=box)
        self._tutorial._labels[label.id] = label
        return label


def make_annotation(target: Target, text: str, *, anchor: Anchor = "right",
                    leader: bool = True, gap: float | None = None,
                    offset: tuple[float, float] = (0, 0), font_scale: float | None = None,
                    padding: float | None = None, box: bool = True, callout: bool = False,
                    max_width: float | None = None, line_spacing: float | None = None) -> Label:
    theme = target._tutorial.theme
    text = validate_annotation_text(text, allow_newlines=callout,
                                    font=target._tutorial.font is not None)
    if anchor not in ("left", "right", "top", "bottom", "center"):
        raise ValidationError(f"Unsupported anchor: {anchor!r}")
    if not isinstance(leader, bool):
        raise ValidationError("leader must be a boolean")
    if not isinstance(box, bool):
        raise ValidationError("box must be a boolean")
    if not isinstance(offset, (tuple, list)) or len(offset) != 2:
        raise ValidationError("offset must contain two finite numbers")
    xy = tuple(finite_number(v, "offset") for v in offset)
    scale = finite_number(theme.font_scale if font_scale is None else font_scale, "font_scale")
    if not 0 < scale <= 10:
        raise ValidationError("font_scale must be > 0 and <= 10")
    options = dict(target=target, text=text, anchor=anchor, leader=leader,
                   gap=finite_number(theme.gap if gap is None else gap, "gap", minimum=0),
                   offset=xy, font_scale=scale,
                   padding=finite_number(theme.padding if padding is None else padding, "padding", minimum=0),
                   box=box)
    if not callout:
        return Label(**options)
    width = finite_number(theme.callout_width if max_width is None else max_width, "max_width", minimum=0)
    if width == 0:
        raise ValidationError("max_width must be positive")
    spacing = finite_number(theme.line_spacing if line_spacing is None else line_spacing, "line_spacing", minimum=1)
    return Callout(**options, max_width=width, line_spacing=spacing)


class Step:
    """An independent collection of visible labels. Create with Tutorial.step()."""

    def __init__(self, tutorial: Tutorial, title: str, *, duration: float = 3.0, pause: float = 0.0):
        self._tutorial = tutorial
        self.title = title
        self.set_timing(duration=duration, pause=pause)
        self._labels: list[Label] = []
        self._callouts: list[Callout] = []
        self._highlights: dict[str, Highlight] = {}
        self._restyles: dict[str, Restyle] = {}
        self._easing: str | None = None
        self._reveals: dict[str, float] = {}
        self._focus: tuple[Target, ...] = ()
        self._dim_opacity: float | None = None
        self._id = str(uuid4())

    @property
    def duration(self) -> float:
        """Presentation duration in seconds, excluding the trailing pause."""
        return self._duration

    @property
    def pause(self) -> float:
        """Extra seconds holding this step before the next hard cut."""
        return self._pause

    def set_timing(self, *, duration: float, pause: float = 0.0) -> Step:
        """Replace both timing values atomically; pause defaults to zero."""
        seconds = finite_number(duration, "duration", minimum=0)
        hold = finite_number(pause, "pause", minimum=0)
        if seconds == 0:
            raise ValidationError("duration must be positive")
        finite_number(seconds + hold, "duration + pause")
        self._duration, self._pause = seconds, hold
        return self

    @property
    def id(self) -> str:
        """Stable identity retained by lesson save/load."""
        return self._id

    @property
    def labels(self) -> tuple[Label, ...]:
        return tuple(self._labels)

    def show(self, *labels: Label, at: float | None = None) -> Step:
        """Show registered labels, without inheriting any other step's state.

        `at` delays them by that many seconds from the start of the step, so a
        narrator can introduce one thing at a time. See docs/REVEAL.md.
        """
        for label in labels:
            if not isinstance(label, Label) or self._tutorial._labels.get(label.id) is not label:
                raise ValidationError("Label must belong to this tutorial")
        seconds = None if at is None else finite_number(at, "at", minimum=0)
        for label in labels:
            if label not in self._labels:
                self._labels.append(label)
            if seconds is not None:
                self._reveals[label.id] = seconds
        return self

    @property
    def reveals(self) -> dict[str, float]:
        """Annotation id to its delay in seconds; only delayed ones appear."""
        return dict(self._reveals)

    def revealed_at(self, annotation: Label) -> float:
        """Seconds from the start of this step before the annotation appears."""
        if not isinstance(annotation, Label):
            raise ValidationError("revealed_at needs a label or callout")
        return self._reveals.get(annotation.id, 0.0)

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
                padding: float | None = None, box: bool = True,
                max_width: float | None = None,
                line_spacing: float | None = None, at: float | None = None) -> Callout:
        """Add a wrapped explanation only to this step; return its definition."""
        self._check_target(target)
        seconds = None if at is None else finite_number(at, "at", minimum=0)
        annotation = make_annotation(target, text, anchor=anchor, leader=leader,
                                     gap=gap, offset=offset, font_scale=font_scale,
                                     padding=padding, box=box, callout=True,
                                     max_width=max_width, line_spacing=line_spacing)
        self._callouts.append(annotation)
        if seconds is not None:
            self._reveals[annotation.id] = seconds
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

    @property
    def easing(self) -> str | None:
        """The easing curve name when this step animates, otherwise None."""
        return self._easing

    def animate(self, easing: str = "ease_in_out") -> Step:
        """Interpolate into this step's restyled state over its duration.

        Without this the step is a hard cut, which stays the default. The
        animation runs from the previous step's state, holds through any
        pause, and does not change what `render_step` produces.
        """
        from drawcv import get_easing

        if not isinstance(easing, str):
            raise ValidationError("easing must be a string")
        try:
            get_easing(easing)  # DrawCV owns the curve names and their validation.
        except Exception as exc:
            raise ValidationError(f"Unknown easing curve: {easing!r}") from exc
        # DrawCV matches names case-insensitively; store one canonical spelling
        # so saved lessons and step.easing are predictable.
        self._easing = easing.lower()
        return self

    def hard_cut(self) -> Step:
        """Undo animate(); the step snaps to its state at the cut."""
        self._easing = None
        return self

    @property
    def restyles(self) -> tuple[Restyle, ...]:
        return tuple(self._restyles.values())

    def restyle(self, target: Target, *, move: tuple[float, float] | None = None,
                fill: tuple[int, int, int] | None = None, opacity: float | None = None,
                visible: bool | None = None) -> Step:
        """Change this target's artwork for this step only, leaving the source alone.

        `move` shifts by (dx, dy) pixels relative to wherever the source placed
        it, so attached labels and highlights follow. Repeating this call for the
        same target replaces its settings, as `highlight` does.
        """
        from .adapters.drawcv import supports_fill

        self._check_target(target)
        if move is None and fill is None and opacity is None and visible is None:
            raise ValidationError("restyle needs at least one of move, fill, opacity or visible")
        if move is not None:
            if not isinstance(move, (tuple, list)) or len(move) != 2:
                raise ValidationError("move must contain two finite numbers")
            move = tuple(finite_number(value, "move") for value in move)
        if fill is not None:
            fill = rgb(fill, "fill")
            drawable = target.drawable
            if not supports_fill(drawable):
                raise ValidationError(
                    f"fill cannot be set on {type(drawable).__name__}; it has no fill or color")
        if opacity is not None:
            opacity = finite_number(opacity, "opacity")
            if not 0 <= opacity <= 1:
                raise ValidationError("opacity must be between 0 and 1")
        if visible is not None and not isinstance(visible, bool):
            raise ValidationError("visible must be a boolean")
        self._restyles[target.id] = Restyle(target, move, fill, opacity, visible)
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
