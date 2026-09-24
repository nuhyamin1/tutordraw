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
Side = Literal["left", "right", "top", "bottom"]
Corner = Literal["top_left", "top_right", "bottom_left", "bottom_right"]
MARK_KINDS = ("arrow", "brace", "measure", "angle", "number")
HIGHLIGHT_SHAPES = ("box", "outline")


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
    shape: str = "box"  # "box" or "outline" (follows the target's own path)
    at: float = 0.0
    draw: bool = False


@dataclass(frozen=True, eq=False)
class Mark:
    """A step-owned drawn annotation: arrow, brace, measure, angle or number.

    `refs` holds Targets or fixed (x, y) scene points, in the order the kind
    defines. Create with Step.connect/brace/measure/angle/number.
    """

    kind: str
    refs: tuple
    text: str | None
    options: dict
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class Camera:
    """Frame these targets' end-state bounds. Create with Step.zoom_to()."""

    targets: tuple[Target, ...]
    padding: float
    max_scale: float


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
        self._marks: list[Mark] = []
        self._draw: set[str] = set()
        self._camera: Camera | None = None
        self._narration: tuple = ()
        self._focus: tuple[Target, ...] = ()
        self._dim_opacity: float | None = None
        self._prompt = None
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

    def show(self, *labels: Label, at: float | None = None, draw: bool = False) -> Step:
        """Show registered labels, without inheriting any other step's state.

        `at` delays them by that many seconds from the start of the step, so a
        narrator can introduce one thing at a time. See docs/REVEAL.md.
        `draw=True` draws each leader on before its panel appears.
        """
        for label in labels:
            if not isinstance(label, Label) or self._tutorial._labels.get(label.id) is not label:
                raise ValidationError("Label must belong to this tutorial")
        seconds = None if at is None else finite_number(at, "at", minimum=0)
        _check_bool(draw, "draw")
        for label in labels:
            if label not in self._labels:
                self._labels.append(label)
            if seconds is not None:
                self._reveals[label.id] = seconds
            if draw:
                self._draw.add(label.id)
        return self

    @property
    def draws(self) -> frozenset[str]:
        """IDs of annotations and marks that draw on rather than appear whole."""
        return frozenset(self._draw)

    def draw_progress(self, item, elapsed: float) -> float:
        """How far `item` has drawn on at `elapsed` seconds: 0 hidden, 1 complete.

        Everything is complete at the end of the step, so render_step never
        shows a half-drawn stroke. Without draw=True an item jumps 0 -> 1.
        """
        if elapsed >= self._duration:
            return 1.0
        if isinstance(item, Highlight):
            start, drawing = item.at, item.draw
        else:
            start, drawing = self._reveals.get(item.id, 0.0), item.id in self._draw
        if elapsed < start:
            return 0.0
        if not drawing:
            return 1.0
        return min(1.0, (elapsed - start) / self._tutorial.theme.draw_seconds)

    @property
    def reveals(self) -> dict[str, float]:
        """Annotation id to its delay in seconds; only delayed ones appear."""
        return dict(self._reveals)

    def revealed_at(self, annotation: Label | Mark) -> float:
        """Seconds from the start of this step before the annotation appears."""
        if not isinstance(annotation, (Label, Mark)):
            raise ValidationError("revealed_at needs a label, callout or mark")
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
                line_spacing: float | None = None, at: float | None = None,
                draw: bool = False) -> Callout:
        """Add a wrapped explanation only to this step; return its definition."""
        self._check_target(target)
        seconds = None if at is None else finite_number(at, "at", minimum=0)
        _check_bool(draw, "draw")
        annotation = make_annotation(target, text, anchor=anchor, leader=leader,
                                     gap=gap, offset=offset, font_scale=font_scale,
                                     padding=padding, box=box, callout=True,
                                     max_width=max_width, line_spacing=line_spacing)
        self._callouts.append(annotation)
        if seconds is not None:
            self._reveals[annotation.id] = seconds
        if draw:
            self._draw.add(annotation.id)
        return annotation

    def highlight(self, target: Target, *, padding: float | None = None,
                  color: tuple[int, int, int] | None = None, width: float | None = None,
                  shape: str = "box", at: float | None = None, draw: bool = False) -> Step:
        """Outline this target in this step.

        `shape="box"` draws a rectangle around its bounds; `shape="outline"`
        follows the target's own outline, grown by `padding`, and needs a
        closed shape. `at` delays it; `draw=True` draws it on.
        """
        self._check_target(target)
        if shape not in HIGHLIGHT_SHAPES:
            raise ValidationError(f"shape must be one of {HIGHLIGHT_SHAPES}, not {shape!r}")
        _check_bool(draw, "draw")
        seconds = 0.0 if at is None else finite_number(at, "at", minimum=0)
        theme = self._tutorial.theme
        pad = finite_number(theme.highlight_padding if padding is None else padding, "padding", minimum=0)
        stroke = finite_number(theme.highlight_width if width is None else width, "width", minimum=0)
        if stroke == 0:
            raise ValidationError("width must be positive")
        tint = rgb(theme.highlight_color if color is None else color, "color")
        if shape == "outline":
            from .adapters.drawcv import outline_path
            outline_path(target.drawable, pad)  # Refuse now, not at render time.
        self._highlights[target.id] = Highlight(target, pad, tint, stroke, shape, seconds, draw)
        return self

    @property
    def marks(self) -> tuple[Mark, ...]:
        return tuple(self._marks)

    def _ref(self, value, name: str):
        if isinstance(value, Target):
            self._check_target(value)
            return value
        if isinstance(value, (tuple, list)) and len(value) == 2:
            return tuple(finite_number(v, name) for v in value)
        if hasattr(value, "x") and hasattr(value, "y"):  # a DrawCV Point, e.g. from a kit's to_scene
            return (finite_number(value.x, name), finite_number(value.y, name))
        raise ValidationError(f"{name} must be a target of this tutorial or an (x, y) point")

    def _mark(self, kind: str, refs: tuple, text: str | None, options: dict,
              at: float | None, draw: bool) -> Mark:
        seconds = None if at is None else finite_number(at, "at", minimum=0)
        _check_bool(draw, "draw")
        if text is not None:
            text = validate_annotation_text(text, allow_newlines=False,
                                            font=self._tutorial.font is not None)
        mark = Mark(kind, refs, text, options)
        self._marks.append(mark)
        if seconds is not None:
            self._reveals[mark.id] = seconds
        if draw:
            self._draw.add(mark.id)
        return mark

    def connect(self, source, destination, text: str | None = None, *,
                bend: float = 0.0, both: bool = False, at: float | None = None,
                draw: bool = False) -> Mark:
        """Draw an arrow between two targets, or from/to a fixed (x, y) point.

        A target end stops just outside its bounds; a point end lands exactly
        there, so `connect((x, y), ball)` is a force arrow pushing on the ball.
        `bend` curves it sideways by that fraction of its length (-1 to 1);
        `both=True` puts a head on each end.
        """
        source, destination = self._ref(source, "source"), self._ref(destination, "destination")
        same = source is destination if isinstance(source, Target) else source == destination
        if same:
            raise ValidationError("connect needs two different ends")
        if not isinstance(source, Target) and not isinstance(destination, Target):
            raise ValidationError("connect needs at least one target")
        bend = finite_number(bend, "bend")
        if not -1 <= bend <= 1:
            raise ValidationError("bend must be between -1 and 1")
        _check_bool(both, "both")
        return self._mark("arrow", (source, destination), text, {"bend": bend, "both": both}, at, draw)

    def brace(self, *targets: Target, text: str | None = None, side: Side = "bottom",
              at: float | None = None, draw: bool = False) -> Mark:
        """Group targets with a curly brace along one side, optionally captioned."""
        if not targets:
            raise ValidationError("brace needs at least one target")
        for value in targets:
            if not isinstance(value, Target):
                raise ValidationError("brace takes targets")
            self._check_target(value)
        if side not in ("left", "right", "top", "bottom"):
            raise ValidationError(f"Unsupported side: {side!r}")
        return self._mark("brace", tuple(dict.fromkeys(targets)), text, {"side": side}, at, draw)

    def measure(self, start, end=None, text: str | None = None, *, axis: str = "x",
                offset: float = 24, at: float | None = None, draw: bool = False) -> Mark:
        """Draw a dimension line with a caption such as "12 cm".

        With one target, spans its width (`axis="x"`) or height (`"y"`). With
        two refs (targets or (x, y) points), spans between their centres along
        x, y, or directly (`"free"`). `offset` pushes the line clear of the art.
        """
        if axis not in ("x", "y", "free"):
            raise ValidationError(f"axis must be 'x', 'y' or 'free', not {axis!r}")
        first = self._ref(start, "start")
        if end is None:
            if not isinstance(first, Target) or axis == "free":
                raise ValidationError("measuring one thing needs a target and axis 'x' or 'y'")
            refs = (first,)
        else:
            refs = (first, self._ref(end, "end"))
        offset = finite_number(offset, "offset", minimum=0)
        return self._mark("measure", refs, text, {"axis": axis, "offset": offset}, at, draw)

    def angle(self, vertex, start, end, text: str | None = None, *, radius: float = 32,
              at: float | None = None, draw: bool = False) -> Mark:
        """Mark the angle at `vertex` between the directions to `start` and `end`."""
        refs = (self._ref(vertex, "vertex"), self._ref(start, "start"), self._ref(end, "end"))
        radius = finite_number(radius, "radius", minimum=0)
        if radius == 0:
            raise ValidationError("radius must be positive")
        return self._mark("angle", refs, text, {"radius": radius}, at, draw)

    def number(self, target: Target, n: int | None = None, *, corner: Corner = "top_left",
               at: float | None = None) -> Mark:
        """Put a numbered badge on a target's corner; n defaults to the next number."""
        if not isinstance(target, Target):
            raise ValidationError("number needs a target")
        self._check_target(target)
        if corner not in ("top_left", "top_right", "bottom_left", "bottom_right"):
            raise ValidationError(f"Unsupported corner: {corner!r}")
        if n is None:
            n = 1 + sum(mark.kind == "number" for mark in self._marks)
        if isinstance(n, bool) or not isinstance(n, int) or not 0 < n < 1000:
            raise ValidationError("n must be an integer from 1 to 999")
        return self._mark("number", (target,), None, {"n": n, "corner": corner}, at, False)

    @property
    def narration(self) -> tuple:
        """The narration's word timings (Word objects), or () if not narrated."""
        return self._narration

    def narrate(self, words, cues: dict | None = None, *, lead: float = 0.15,
                tail: float = 0.5, fit: bool = True, rate: float | None = None) -> Step:
        """Time reveals to a voice: each cue appears as its phrase is spoken.

        `words` are the TTS word timings, (word, start, end) in seconds from the
        start of the step, or dicts; a plain string is timed at `rate` words per
        second for previews. `cues` maps a label or callout shown in this step,
        a mark of this step, or a highlighted target, to the phrase that
        introduces it; it appears `lead` seconds before the phrase starts.
        With `fit`, the step lasts at least until the narration ends plus
        `tail`. Draw-on still applies from the new reveal time. See
        docs/NARRATION.md.
        """
        from .narration import DEFAULT_RATE, find_phrase, parse_words

        spoken = parse_words(words, DEFAULT_RATE if rate is None else rate)
        lead = finite_number(lead, "lead", minimum=0)
        tail = finite_number(tail, "tail", minimum=0)
        _check_bool(fit, "fit")
        cues = {} if cues is None else cues
        if not isinstance(cues, dict):
            raise ValidationError("cues must map annotations, marks or targets to phrases")
        shown = {item.id for item in (*self._labels, *self._callouts, *self._marks)}
        # Resolve everything before changing anything, so a bad cue leaves the step as it was.
        times = []
        for item, phrase in cues.items():
            at = max(0.0, spoken[find_phrase(spoken, phrase)].start - lead)
            if isinstance(item, Target):
                if item.id not in self._highlights:
                    raise ValidationError(
                        f"Target {item.name or item.id!r} has no highlight in this step; "
                        "call highlight() before narrate()")
            elif not isinstance(item, (Label, Mark)) or item.id not in shown:
                raise ValidationError("Each cue must be a label or callout shown in this step, "
                                      "a mark of this step, or a highlighted target")
            times.append((item, at))
        for item, at in times:
            if isinstance(item, Target):
                from dataclasses import replace
                self._highlights[item.id] = replace(self._highlights[item.id], at=at)
            else:
                self._reveals[item.id] = at
        self._narration = spoken
        if fit and spoken[-1].end + tail > self._duration:
            self.set_timing(duration=spoken[-1].end + tail, pause=self._pause)
        return self

    @property
    def camera(self) -> Camera | None:
        return self._camera

    def zoom_to(self, *targets: Target, padding: float = 40, max_scale: float = 4) -> Step:
        """Frame these targets for this step, zooming the artwork (not the text).

        Framing uses the targets' state at the end of the step. On an animated
        step the camera moves from the previous step's framing.
        """
        if not targets:
            raise ValidationError("zoom_to needs at least one target")
        for value in targets:
            if not isinstance(value, Target):
                raise ValidationError("zoom_to takes targets")
            self._check_target(value)
        padding = finite_number(padding, "padding", minimum=0)
        max_scale = finite_number(max_scale, "max_scale", minimum=0)
        if not 0 < max_scale <= 20:
            raise ValidationError("max_scale must be > 0 and <= 20")
        self._camera = Camera(tuple(dict.fromkeys(targets)), padding, max_scale)
        return self

    def reset_camera(self) -> Step:
        """Show the whole canvas in this step (the default)."""
        self._camera = None
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

    @property
    def prompt(self):
        """The step's Prompt, or None. See docs/PROMPTS.md."""
        return self._prompt

    def ask(self, text: str, answer, *, correct: str | None = None, wrong: str | None = None,
            hint: str | None = None, attempts: int = 3) -> Step:
        """End the step with a question answered by tapping the picture.

        `answer` is the target to tap, or a tuple of targets that are all
        right. The player holds the step at its end until the learner taps an
        answer. Feedback defaults to "Yes, that's the nucleus.", "That's the
        cell wall. Try again." and, after `attempts` wrong taps, "Here it is:
        the nucleus.", naming targets by their names. One prompt per step;
        asking again replaces it. `Tutorial.check_answer` checks a tap in Python.
        """
        from .prompts import make_prompt

        self._prompt = make_prompt(self, text, answer, correct=correct, wrong=wrong,
                                   hint=hint, attempts=attempts)
        return self

    def clear_prompt(self) -> Step:
        """Remove the step's prompt, if it has one."""
        self._prompt = None
        return self


def _check_bool(value, name: str) -> None:
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be a boolean")
